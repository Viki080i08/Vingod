#!/usr/bin/env bash
# ============================================================================
#  Installation automatique de PronoIA sur un serveur Linux (Ubuntu/Debian).
#  Le bot tournera ensuite 24h/24, 7j/7, même Cursor fermé et PC éteint.
#
#  Utilisation (sur le serveur, connecté en SSH) :
#     curl -fsSL https://raw.githubusercontent.com/Viki080i08/Vingod/cursor/telegram-sports-prediction-bot-d3d7/sportsbot/scripts/install_vps.sh -o install.sh
#     bash install.sh
#
#  Le script vous demandera votre token Telegram, votre clé API-Football et
#  votre ID admin, puis installera un service qui redémarre tout seul.
# ============================================================================
set -euo pipefail

REPO_URL="https://github.com/Viki080i08/Vingod.git"
BRANCH="${PRONOIA_BRANCH:-cursor/telegram-sports-prediction-bot-d3d7}"
DEST="/opt/pronoia"

echo "==================================================="
echo "  Installation de PronoIA (bot Telegram 24/7)"
echo "==================================================="

echo "[1/6] Installation des paquets système..."
sudo apt-get update -y
sudo apt-get install -y git python3-venv python3-pip

echo "[2/6] Récupération du code (${BRANCH})..."
sudo mkdir -p "$DEST"
sudo chown "$(whoami)" "$DEST"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch --all --quiet
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull origin "$BRANCH" --quiet
else
  git clone --quiet "$REPO_URL" "$DEST"
  git -C "$DEST" checkout "$BRANCH"
fi

cd "$DEST/sportsbot"

echo "[3/6] Environnement Python + dépendances..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

echo "[4/6] Configuration (.env)..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo
  read -rp "  ➜ Token Telegram (@BotFather) : " TOKEN
  read -rp "  ➜ Clé API-Football           : " APIKEY
  read -rp "  ➜ Votre ID Telegram admin    : " ADMINID
  sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${TOKEN}|" .env
  sed -i "s|^APIFOOTBALL_API_KEY=.*|APIFOOTBALL_API_KEY=${APIKEY}|" .env
  sed -i "s|^ADMIN_IDS=.*|ADMIN_IDS=${ADMINID}|" .env
  echo "  .env créé."
else
  echo "  .env déjà présent, on le garde."
fi

echo "[5/6] Vérification de la configuration..."
.venv/bin/python -m sportsbot check

echo "[6/6] Installation du service systemd (démarrage auto + redémarrage)..."
SERVICE=/etc/systemd/system/pronoia.service
sudo cp deploy/pronoia.service "$SERVICE"
sudo sed -i "s|/opt/pronoia/sportsbot|${DEST}/sportsbot|g" "$SERVICE"
sudo sed -i "s|^# User=pronoia|User=$(whoami)|" "$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable --now pronoia

echo
echo "==================================================="
echo "  ✅ PronoIA est installé et tourne 24/7 !"
echo "  Voir les logs   : journalctl -u pronoia -f"
echo "  Redémarrer      : sudo systemctl restart pronoia"
echo "  Arrêter         : sudo systemctl stop pronoia"
echo "==================================================="
