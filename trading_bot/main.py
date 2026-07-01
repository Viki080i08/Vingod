"""Application entry point.

Run with:  python -m trading_bot.main   (from the repository root)
       or: python main.py               (from inside the trading_bot folder)
"""
from __future__ import annotations

import logging
import sys

from .bot.telegram_bot import build_application
from .config import settings

logger = logging.getLogger(__name__)


def _banner() -> None:
    print("=" * 60, flush=True)
    print("  Trading AI Telegram Bot", flush=True)
    print("=" * 60, flush=True)


def main() -> None:
    _banner()
    settings.configure_logging()

    try:
        settings.validate()
    except RuntimeError as exc:
        print(f"\n❌ ERREUR : {exc}\n", flush=True)
        print("Étapes :", flush=True)
        print("  1. cd trading_bot", flush=True)
        print("  2. cp .env.example .env", flush=True)
        print("  3. Ouvrez .env et mettez votre TELEGRAM_BOT_TOKEN", flush=True)
        print("  4. python -m trading_bot.main   (depuis la racine du dépôt)\n", flush=True)
        raise SystemExit(1)

    print("✓ Token Telegram détecté", flush=True)
    print("✓ Démarrage du bot (Ctrl+C pour arrêter)…\n", flush=True)

    app = build_application()
    logger.info("Starting Trading AI Telegram bot (polling)…")

    # drop_pending_updates=False keeps messages sent while the bot was offline.
    app.run_polling(
        drop_pending_updates=False,
        allowed_updates=["message", "edited_message"],
    )


if __name__ == "__main__":
    main()
