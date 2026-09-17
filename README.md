# 🌍 PixelWorld

Jeu communautaire de pixels collaboratif, inspiré du concept des grandes toiles de pixels.

## Fonctionnalités
- Carte 100 × 100
- 12 couleurs
- Pseudo
- 1 pixel toutes les 60 secondes
- Zoom et déplacement
- Mise à jour automatique
- Flask + SQLite
- Code open source

## Lancer en local

Backend :
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Frontend :
```bash
cd frontend
python -m http.server 8080
```

Puis ouvre http://localhost:8080.

## GitHub Pages

Le dossier `frontend` peut être publié avec GitHub Pages.

Le backend doit être hébergé séparément sur un service compatible avec Flask. Après son déploiement, remplace `API_URL` dans `frontend/script.js`.

## Licence
MIT
