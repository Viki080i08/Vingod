"""Application entry point.

Run with:  python -m trading_bot.main   (from the repository root)
       or: python main.py               (from inside the trading_bot folder)
"""
from __future__ import annotations

import logging

from .bot.telegram_bot import build_application
from .config import settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings.configure_logging()
    try:
        settings.validate()
    except RuntimeError as exc:
        logger.error(str(exc))
        raise SystemExit(1)

    app = build_application()
    logger.info("Starting Trading AI Telegram bot (polling)…")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
