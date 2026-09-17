from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timezone
from database import init_db, get_all_pixels, get_last_pixel, save_pixel

app=Flask(__name__)
CORS(app)

WORLD_SIZE=100
COOLDOWN_SECONDS=60
ALLOWED_COLORS={
    "#000000","#ffffff","#ff3b30","#ff9500","#ffcc00","#34c759",
    "#00c7be","#007aff","#5856d6","#af52de","#ff2d55","#8e8e93"
}

init_db()

@app.get("/")
def home():
    return jsonify({"name":"PixelWorld API","status":"online"})

@app.get("/api/pixels")
def pixels():
    return jsonify({"size":WORLD_SIZE,"pixels":get_all_pixels()})

@app.post("/api/pixels")
def place_pixel():
    data=request.get_json(silent=True) or {}
    username=str(data.get("username","Anonyme")).strip()[:20] or "Anonyme"
    color=str(data.get("color","")).lower()
    try:
        x=int(data.get("x")); y=int(data.get("y"))
    except (TypeError,ValueError):
        return jsonify({"error":"Coordonnées invalides."}),400

    if not (0<=x<WORLD_SIZE and 0<=y<WORLD_SIZE):
        return jsonify({"error":"Ce pixel est hors de la carte."}),400
    if color not in ALLOWED_COLORS:
        return jsonify({"error":"Cette couleur n'est pas autorisée."}),400

    last=get_last_pixel(username)
    if last:
        elapsed=(datetime.now(timezone.utc)-last).total_seconds()
        remaining=COOLDOWN_SECONDS-elapsed
        if remaining>0:
            seconds=int(remaining)+1
            return jsonify({"error":f"Encore {seconds}s avant ton prochain pixel.","cooldown":seconds}),429

    save_pixel(x,y,color,username)
    return jsonify({"success":True,"x":x,"y":y,"color":color})

@app.get("/health")
def health():
    return jsonify({"status":"healthy"})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,debug=True)
