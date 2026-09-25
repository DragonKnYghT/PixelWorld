import hashlib
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, urlparse

import requests
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS

from database import (
    init_db, get_all_pixels, get_pixel, get_player, get_player_by_id,
    update_player, save_pixel, create_auth_session, get_auth_session,
    delete_auth_session, redeem_code, create_oauth_state, consume_oauth_state,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None"
)

from urllib.parse import urlparse

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://dragonknyght.github.io/PixelWorld"
).rstrip("/")

FRONTEND_ORIGIN = f"{urlparse(FRONTEND_URL).scheme}://{urlparse(FRONTEND_URL).netloc}"
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://pixelworld-0wr6.onrender.com/auth/discord/callback")

CORS(
    app,
    origins=[FRONTEND_ORIGIN],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

WORLD_SIZE = 2500
BASE_RECHARGE_SECONDS = 60
MAX_SKILL_LEVEL = 36
MAX_STORAGE = 200
MIN_RECHARGE_SECONDS = 20
MAX_CRIT_PERCENT = 10.0

# 24 predefined colours. Custom 6-digit HEX colours are also accepted by the server.
COLORS = {
    "#000000", "#ffffff", "#ff3b30", "#ff9500", "#ffcc00", "#34c759",
    "#00c7be", "#007aff", "#5856d6", "#af52de", "#ff2d55", "#8e8e93",
    "#5ac8fa", "#30d158", "#64d2ff", "#ffd60a", "#ff9f0a", "#ff375f",
    "#bf5af2", "#ac8e68", "#a2845e", "#636366", "#2c2c2e", "#d1d1d6"
}

# Thirty reward codes. Keep these in Render's PIXEL_CODES variable instead of committing them publicly.
DEFAULT_PIXEL_CODES = [
    "PW-7K4M-2Q9X", "PW-H8TZ-5N3C", "PW-R6VL-9D2A", "PW-X3QP-8M7F", "PW-B5NW-4K8J",
    "PW-2Y6S-9H4P", "PW-C8FD-3R7V", "PW-M4QK-6T9Z", "PW-N7XA-2L5D", "PW-P9JW-4C6H",
    "PW-6V3B-8K2M", "PW-T5RD-7Q9N", "PW-Z4HF-2X8C", "PW-8LKM-5P3S", "PW-Q7NC-9V2T",
    "PW-3F8J-6W4R", "PW-K2DP-7M9X", "PW-V6QT-4H8B", "PW-9R3Z-5N7K", "PW-D8MC-2P6Y",
    "PW-4X7H-9Q2F", "PW-J5VN-3K8D", "PW-2C6R-7T9W", "PW-F8LP-4M3Q", "PW-6N2Z-8H5V",
    "PW-S7KD-9X4C", "PW-5Q3M-2R8J", "PW-Y9TF-6P4N", "PW-3V7B-5K2X", "PW-H6CQ-8D4M"
]
PIXEL_CODES = {c.strip().upper(): 10 for c in os.getenv("PIXEL_CODES", ",".join(DEFAULT_PIXEL_CODES)).split(",") if c.strip()}

init_db()
def init_db():
    c = get_connection()

    # tes autres tables
    c.execute(q("""CREATE TABLE IF NOT EXISTS players (
        ...
    )"""))

    c.execute(q("""CREATE TABLE IF NOT EXISTS redeemed_codes (
        code TEXT NOT NULL,
        discord_id TEXT NOT NULL,
        redeemed_at TEXT NOT NULL,
        PRIMARY KEY (code, discord_id)
    )"""))

    # AJOUTER ÇA
    c.execute(q("""CREATE TABLE IF NOT EXISTS oauth_states (
        state TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )"""))

    c.commit()
    c.close()


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


def cooldown_for_level(level):
    # 36 levels smoothly take the timer from 60 s to exactly 20 s.
    return int(round(BASE_RECHARGE_SECONDS - (BASE_RECHARGE_SECONDS - MIN_RECHARGE_SECONDS) * level / MAX_SKILL_LEVEL))


def crit_for_level(level):
    return round(MAX_CRIT_PERCENT * level / MAX_SKILL_LEVEL, 2)


def recharge_player(player):
    current = datetime.now(timezone.utc)
    last = datetime.fromisoformat(player["last_recharge_at"])
    cooldown = cooldown_for_level(player["cooldown_level"])
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
    cooldown = cooldown_for_level(player["cooldown_level"])
    return {
        "discord_id": player["discord_id"], "username": player["username"],
        "pixel_balance": player["pixel_balance"], "max_storage": player["max_storage"],
        "recharge_seconds": cooldown, "storage_level": player["storage_level"],
        "cooldown_level": player["cooldown_level"], "crit_level": player["crit_level"],
        "crit_chance": crit_for_level(player["crit_level"]), "total_placed": player["total_placed"],
        "skill_points": skill_points(player), "max_skill_level": MAX_SKILL_LEVEL,
    }


def require_login():
    user = current_player()
    if not user:
        return None, (jsonify({"error": "Connecte-toi avec Discord pour faire ça.", "login_required": True}), 401)
    return user, None


def valid_color(value):
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", value))


@app.get("/")
def home():
    return jsonify({"name": "PixelWorld API", "status": "online", "world_size": WORLD_SIZE, "storage": "postgresql" if os.getenv("DATABASE_URL") else "sqlite"})


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
    if not valid_color(color):
        return jsonify({"error": "Couleur invalide. Utilise un code HEX comme #ff00aa."}), 400

    existing = get_pixel(x, y)
    if existing and existing.get("discord_id") != player["discord_id"]:
        return jsonify({"error": "Ce pixel appartient déjà à un autre joueur. Tu ne peux pas le recouvrir."}), 403
    if player["pixel_balance"] <= 0:
        cooldown = cooldown_for_level(player["cooldown_level"])
        return jsonify({"error": "Tu n'as plus de pixels disponibles.", "cooldown": cooldown}), 429

    critical = secrets.randbelow(10000) < int(crit_for_level(player["crit_level"]) * 100)
    new_balance = player["pixel_balance"] if critical else player["pixel_balance"] - 1
    total = player["total_placed"] + 1

    if not save_pixel(x, y, color, player["username"], player["discord_id"]):
        return jsonify({"error": "Quelqu'un vient de poser ce pixel avant toi."}), 409
    update_player(player["discord_id"], pixel_balance=new_balance, total_placed=total)
    return jsonify({"success": True, "x": x, "y": y, "color": color, "critical": critical, "overwritten_own": bool(existing), "player": player_payload(get_player_by_id(player["discord_id"]))})


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
    if level >= MAX_SKILL_LEVEL:
        return jsonify({"error": "Cette compétence est déjà au niveau maximum."}), 400
    if skill_points(player) < 1:
        return jsonify({"error": "Pas assez de points de compétence."}), 400

    field = {"storage": "storage_level", "cooldown": "cooldown_level", "crit": "crit_level"}[skill]
    values = {field: level + 1, "skill_points_spent": player["skill_points_spent"] + 1}
    if skill == "storage":
        values["max_storage"] = min(MAX_STORAGE, player["max_storage"] + 5)
        values["pixel_balance"] = min(values["max_storage"], player["pixel_balance"] + 5)
    elif skill == "cooldown":
        values["last_recharge_at"] = datetime.now(timezone.utc).isoformat()
    update_player(player["discord_id"], **values)
    return jsonify({"success": True, "player": player_payload(get_player_by_id(player["discord_id"]))})


@app.post("/api/codes/redeem")
def redeem_pixel_code():
    player, error = require_login()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip().upper()
    if code not in PIXEL_CODES:
        return jsonify({"error": "Code invalide ou inconnu."}), 400
    amount = PIXEL_CODES[code]
    if not redeem_code(code, player["discord_id"], amount):
        return jsonify({"error": "Tu as déjà utilisé ce code."}), 409
    updated = get_player_by_id(player["discord_id"])
    return jsonify({"success": True, "pixels_received": amount, "player": player_payload(updated)})


@app.get("/api/codes/count")
def codes_count():
    return jsonify({"available_codes": len(PIXEL_CODES), "pixels_per_code": 10})


@app.get("/auth/discord")
def discord_login():
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return jsonify({"error": "Discord OAuth n'est pas encore configuré sur le serveur."}), 503
    state = secrets.token_urlsafe(32)

    create_oauth_state(
        state,
        (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    )
    params = {"client_id": DISCORD_CLIENT_ID, "redirect_uri": DISCORD_REDIRECT_URI, "response_type": "code", "scope": "identify", "state": state}
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))


@app.get("/auth/discord/callback")
def discord_callback():
    if request.args.get("error"):
        return redirect(FRONTEND_URL + "?login=cancelled")
    state = request.args.get("state")

    if not state or not consume_oauth_state(state):
        return jsonify({
            "error": "État OAuth invalide ou expiré. Relance la connexion Discord."
        }), 400
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
