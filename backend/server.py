import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, request, redirect, session
from flask_cors import CORS

from database import (
    init_db, get_all_pixels, get_pixel, get_player, get_player_by_id,
    update_player, save_pixel, create_auth_session, get_auth_session,
    delete_auth_session,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500").rstrip("/")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://pixelworld-0wr6.onrender.com/auth/discord/callback")

CORS(app, origins=[FRONTEND_ORIGIN], allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "OPTIONS"])

WORLD_SIZE = 2500
BASE_RECHARGE_SECONDS = 60

COLORS = {
    "#000000", "#ffffff", "#ff3b30", "#ff9500", "#ffcc00", "#34c759",
    "#00c7be", "#007aff", "#5856d6", "#af52de", "#ff2d55", "#8e8e93",
    "#5ac8fa", "#30d158", "#64d2ff", "#ffd60a", "#ff9f0a", "#ff375f",
    "#bf5af2", "#ac8e68", "#a2845e", "#636366", "#2c2c2e", "#d1d1d6"
}

init_db()


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_player():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    record = get_auth_session(token_hash(token))
    if not record:
        return None
    if datetime.fromisoformat(record["expires_at"]) <= datetime.now(timezone.utc):
        delete_auth_session(token_hash(token))
        return None
    return get_player_by_id(record["discord_id"])


def skill_points(player):
    return max(0, player["total_placed"] // 50 - player["skill_points_spent"])


def recharge_player(player):
    current = datetime.now(timezone.utc)
    last = datetime.fromisoformat(player["last_recharge_at"])
    cooldown = max(35, BASE_RECHARGE_SECONDS - player["cooldown_level"] * 5)
    elapsed = (current - last).total_seconds()
    periods = int(elapsed // cooldown)
    if periods <= 0:
        return player
    new_balance = min(player["max_storage"], player["pixel_balance"] + periods)
    if new_balance >= player["max_storage"]:
        new_last = current
    else:
        new_last = last + timedelta(seconds=periods * cooldown)
    update_player(player["discord_id"], pixel_balance=new_balance, last_recharge_at=new_last.isoformat())
    player["pixel_balance"] = new_balance
    player["last_recharge_at"] = new_last.isoformat()
    return player


def player_payload(player):
    player = recharge_player(player)
    cooldown = max(35, BASE_RECHARGE_SECONDS - player["cooldown_level"] * 5)
    return {
        "discord_id": player["discord_id"], "username": player["username"],
        "pixel_balance": player["pixel_balance"], "max_storage": player["max_storage"],
        "recharge_seconds": cooldown, "storage_level": player["storage_level"],
        "cooldown_level": player["cooldown_level"], "crit_level": player["crit_level"],
        "crit_chance": player["crit_level"], "total_placed": player["total_placed"],
        "skill_points": skill_points(player),
    }


def require_login():
    user = current_player()
    if not user:
        return None, (jsonify({"error": "Connecte-toi avec Discord pour faire ça.", "login_required": True}), 401)
    return user, None


@app.get("/")
def home():
    return jsonify({"name": "PixelWorld API", "status": "online", "world_size": WORLD_SIZE})


@app.get("/api/pixels")
def pixels():
    return jsonify({"size": WORLD_SIZE, "pixels": get_all_pixels()})


@app.get("/api/pixels/<int:x>/<int:y>")
def pixel_info(x, y):
    if not (0 <= x < WORLD_SIZE and 0 <= y < WORLD_SIZE):
        return jsonify({"error": "Coordonnées invalides."}), 400
    return jsonify({"pixel": get_pixel(x, y)})


@app.get("/api/me")
def me():
    user = current_player()
    return jsonify({"logged_in": bool(user), "player": player_payload(user) if user else None})


@app.post("/api/pixels")
def place_pixel():
    player, error = require_login()
    if error:
        return error
    player = recharge_player(player)
    data = request.get_json(silent=True) or {}
    color = str(data.get("color", "")).lower()
    try:
        x = int(data.get("x")); y = int(data.get("y"))
    except (TypeError, ValueError):
        return jsonify({"error": "Coordonnées invalides."}), 400
    if not (0 <= x < WORLD_SIZE and 0 <= y < WORLD_SIZE):
        return jsonify({"error": "Ce pixel est hors de la carte."}), 400
    if color not in COLORS:
        return jsonify({"error": "Cette couleur n'est pas autorisée."}), 400
    if player["pixel_balance"] <= 0:
        cooldown = max(35, BASE_RECHARGE_SECONDS - player["cooldown_level"] * 5)
        return jsonify({"error": "Tu n'as plus de pixels disponibles.", "cooldown": cooldown}), 429

    critical = secrets.randbelow(100) < player["crit_level"]
    new_balance = player["pixel_balance"] if critical else player["pixel_balance"] - 1
    total = player["total_placed"] + 1
    update_player(player["discord_id"], pixel_balance=new_balance, total_placed=total)
    save_pixel(x, y, color, player["username"], player["discord_id"])
    return jsonify({"success": True, "x": x, "y": y, "color": color, "critical": critical, "player": player_payload(get_player_by_id(player["discord_id"]))})


@app.post("/api/skills/<skill>")
def buy_skill(skill):
    player, error = require_login()
    if error:
        return error
    player = recharge_player(player)
    levels = {"storage": player["storage_level"], "cooldown": player["cooldown_level"], "crit": player["crit_level"]}
    if skill not in levels:
        return jsonify({"error": "Compétence inconnue."}), 404
    level = levels[skill]
    if level >= 5:
        return jsonify({"error": "Cette compétence est déjà au niveau maximum."}), 400
    if skill_points(player) < 1:
        return jsonify({"error": "Pas assez de points de compétence."}), 400
    field = {"storage": "storage_level", "cooldown": "cooldown_level", "crit": "crit_level"}[skill]
    values = {field: level + 1, "skill_points_spent": player["skill_points_spent"] + 1}
    if skill == "storage":
        values["max_storage"] = player["max_storage"] + 5
        values["pixel_balance"] = min(player["max_storage"] + 5, player["pixel_balance"] + 5)
    update_player(player["discord_id"], **values)
    return jsonify({"success": True, "player": player_payload(get_player_by_id(player["discord_id"]))})


@app.get("/auth/discord")
def discord_login():
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return jsonify({"error": "Discord OAuth n'est pas encore configuré sur le serveur."}), 503
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {"client_id": DISCORD_CLIENT_ID, "redirect_uri": DISCORD_REDIRECT_URI, "response_type": "code", "scope": "identify", "state": state}
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))


@app.get("/auth/discord/callback")
def discord_callback():
    if request.args.get("error"):
        return redirect(FRONTEND_URL + "?login=cancelled")
    state = request.args.get("state")
    if not state or state != session.pop("oauth_state", None):
        return jsonify({"error": "État OAuth invalide."}), 400
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Code Discord manquant."}), 400
    token = requests.post("https://discord.com/api/v10/oauth2/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": DISCORD_REDIRECT_URI}, auth=(DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET), timeout=10)
    if not token.ok:
        return jsonify({"error": "Discord n'a pas accepté la connexion."}), 502
    access_token = token.json()["access_token"]
    profile = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if not profile.ok:
        return jsonify({"error": "Impossible de récupérer ton profil Discord."}), 502
    data = profile.json()
    discord_id = str(data["id"])
    username = data.get("global_name") or data.get("username") or "Joueur Discord"
    get_player(discord_id, username)

    raw_token = secrets.token_urlsafe(48)
    create_auth_session(token_hash(raw_token), discord_id, (datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
    return redirect(FRONTEND_URL + "#token=" + raw_token)


@app.post("/auth/logout")
def logout():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        delete_auth_session(token_hash(auth[7:].strip()))
    return jsonify({"success": True})


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
