# 🌍 PixelWorld

PixelWorld est un jeu web communautaire open source inspiré du principe des grandes toiles de pixels collaboratives.

## Fonctionnalités

- Carte de **2500 × 2500 pixels**
- 24 couleurs
- **20 charges de pixels** au départ
- Recharge automatique d'une charge
- Arbre de compétences
  - 📦 stockage maximum +5 par niveau
  - ⏱️ recharge -5 secondes par niveau
  - ✨ pixel critique jusqu'à 5 %
- Informations sur le créateur et la date du dernier pixel posé
- Sons lors de la pose et quand le stockage redevient plein
- Connexion sécurisée par **Discord OAuth2**
- Flask + SQLite pour le backend
- Frontend statique compatible GitHub Pages

## Architecture

```text
frontend/
  index.html
  skills.html
  style.css
  script.js
  skills.js
backend/
  server.py
  database.py
  requirements.txt
```

## Configuration Render

Root Directory : `backend`

Build Command :

```bash
pip install -r requirements.txt
```

Start Command :

```bash
gunicorn server:app
```

Variables d'environnement à créer sur Render :

```text
FLASK_SECRET_KEY=une-longue-valeur-aleatoire
FRONTEND_URL=https://TON-PSEUDO.github.io/PixelWorld
DISCORD_CLIENT_ID=ID_DE_TON_APPLICATION_DISCORD
DISCORD_CLIENT_SECRET=SECRET_DE_TON_APPLICATION_DISCORD
DISCORD_REDIRECT_URI=https://pixelworld-0wr6.onrender.com/auth/discord/callback
```

Dans Discord Developer Portal, ajoute exactement l'URL `DISCORD_REDIRECT_URI` dans les Redirects OAuth2. Le flux OAuth2 utilise un code retourné par Discord, échangé côté serveur, avec un paramètre `state` pour limiter les attaques CSRF.

## Important pour une vraie mise en production

SQLite est pratique pour cette V1. Pour une très grosse fréquentation, une base PostgreSQL et une stratégie de chargement par zones/chunks seront préférables afin d'éviter de charger toute la carte à chaque actualisation.
