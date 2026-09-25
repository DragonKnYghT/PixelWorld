# 🌍 PixelWorld

PixelWorld est un jeu web communautaire de pixels, avec connexion Discord et progression par compétences.

## Fonctionnalités de cette version

- 🗺️ Carte **2500 × 2500**
- 💾 Sauvegarde persistante via **PostgreSQL** quand `DATABASE_URL` est configuré
- 🧱 SQLite conservé comme fallback local
- 🎨 24 couleurs + **couleurs personnalisées HEX**
- 🚫 Impossible de recouvrir le pixel d'un autre joueur
- ♻️ Tu peux modifier tes propres pixels
- ⚡ 20 pixels de départ, stockage améliorable jusqu'à **200**
- ⏱️ Recharge de **60 s → 20 s** avec 36 niveaux
- ✨ Pixel critique jusqu'à **10 %** avec 36 niveaux
- 🧠 36 niveaux pour chaque compétence
- 🎁 **30 codes** de récupération, 10 pixels par code
- 🔐 Un code ne peut être utilisé qu'une fois par compte Discord
- 👤 Informations du créateur et de la dernière modification d'un pixel
- 🔵 Connexion Discord OAuth2

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
PIXEL_CODES.txt
```

## Render

### Backend

- Root Directory : `backend`
- Build Command :

```bash
pip install -r requirements.txt
```

- Start Command :

```bash
gunicorn server:app
```

### Variables d'environnement

```text
FLASK_SECRET_KEY=une-longue-valeur-aleatoire
FRONTEND_URL=https://dragonknyght.github.io/PixelWorld
DISCORD_CLIENT_ID=ID_DE_TON_APPLICATION_DISCORD
DISCORD_CLIENT_SECRET=SECRET_DE_TON_APPLICATION_DISCORD
DISCORD_REDIRECT_URI=https://pixelworld-0wr6.onrender.com/auth/discord/callback
DATABASE_URL=URL_POSTGRESQL_RENDER
PIXEL_CODES=CODE1, CODE2, CODE3, ...
```

`PIXEL_CODES` est facultatif pour tester : le backend possède 30 codes de démonstration. Pour un vrai déploiement, mets tes propres codes dans la variable Render plutôt que de laisser les codes de démonstration dans le dépôt public.

### Sauvegarde de la map

Le code utilise automatiquement PostgreSQL si `DATABASE_URL` existe. C'est le mode recommandé pour Render : les pixels, comptes, sessions et codes utilisés sont alors stockés dans la base au lieu du fichier SQLite local.

Dans Render, crée un **Postgres**, puis ajoute son URL de connexion dans `DATABASE_URL`. Utilise de préférence l'URL interne si la base et le backend sont dans la même région.

⚠️ Le Postgres gratuit de Render expire actuellement après 30 jours. Pour garder la map sur le long terme, il faut passer la base sur une offre payante avant son expiration. Les bases Postgres payantes bénéficient des fonctions de sauvegarde de Render.

## Discord OAuth2

Dans le Discord Developer Portal, ajoute exactement :

```text
https://pixelworld-0wr6.onrender.com/auth/discord/callback
```

comme Redirect URI.

Le flux utilise `state` pour limiter les attaques CSRF et garde le secret Discord uniquement côté serveur.

## Codes

`PIXEL_CODES.txt` contient les 30 codes actuellement prévus. Il est volontairement ignoré par Git via `.gitignore`.

Chaque code donne **10 pixels** et peut être utilisé une fois par compte Discord.

## GitHub Pages

Le dossier `frontend/` est déployable comme site statique. Le workflow `.github/workflows/pages.yml` permet également de publier automatiquement le frontend sur GitHub Pages.
