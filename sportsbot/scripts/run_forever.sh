#!/usr/bin/env bash
# Lance PronoIA et le relance automatiquement en cas d'arrêt/crash.
# Le bot tourne ainsi "tout le temps" tant que ce script n'est pas stoppé.
set -uo pipefail

cd "$(dirname "$0")/.."

# Active l'environnement virtuel s'il existe.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[PronoIA] Vérification de la configuration..."
if ! python -m sportsbot check; then
  echo "[PronoIA] Configuration invalide (token ?). Corrigez .env puis relancez." >&2
  exit 1
fi

while true; do
  echo "[PronoIA] Démarrage du bot + dashboard à $(date)"
  python -m sportsbot all
  code=$?
  echo "[PronoIA] Processus arrêté (code ${code}). Redémarrage dans 5s..." >&2
  sleep 5
done
