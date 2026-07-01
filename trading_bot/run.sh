#!/usr/bin/env bash
# Lance le bot Telegram depuis n'importe quel répertoire.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f "trading_bot/.env" ]; then
  echo "❌ Fichier trading_bot/.env introuvable."
  echo ""
  echo "Créez-le ainsi :"
  echo "  cp trading_bot/.env.example trading_bot/.env"
  echo "  # puis éditez trading_bot/.env et mettez TELEGRAM_BOT_TOKEN=..."
  exit 1
fi

if ! grep -qE '^TELEGRAM_BOT_TOKEN=.+$' trading_bot/.env; then
  echo "❌ TELEGRAM_BOT_TOKEN est vide dans trading_bot/.env"
  exit 1
fi

echo "Installation des dépendances (si nécessaire)…"
pip3 install -q -r trading_bot/requirements.txt 2>/dev/null || pip install -q -r trading_bot/requirements.txt

echo "Démarrage du bot…"
echo "⚠️  Ne lancez qu'UNE seule instance (sinon Telegram renvoie Conflict)."
exec python3 -m trading_bot.main
