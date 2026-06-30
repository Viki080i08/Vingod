"""Command-line entry point for PronoIA.

Usage:
    python -m sportsbot bot      # run only the Telegram bot (long polling)
    python -m sportsbot admin    # run only the web admin dashboard
    python -m sportsbot all      # run both (admin in a background thread)
    python -m sportsbot sync     # run a one-off fixtures sync + analysis
    python -m sportsbot initdb   # create database tables and exit
"""

from __future__ import annotations

import argparse
import threading

from .logging_conf import get_logger, setup_logging

logger = get_logger(__name__)


def _run_admin_thread() -> None:
    from .admin.web import run_admin

    thread = threading.Thread(target=run_admin, name="admin-web", daemon=True)
    thread.start()
    logger.info("Admin dashboard thread started.")


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    parser = argparse.ArgumentParser(prog="sportsbot", description="PronoIA")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["bot", "admin", "all", "sync", "initdb"],
        help="Composant à lancer (défaut: all)",
    )
    args = parser.parse_args(argv)

    if args.command == "initdb":
        from .db import init_db

        init_db()
        logger.info("Base de données initialisée.")
        return

    if args.command == "sync":
        from .scheduler.jobs import run_sync

        result = run_sync()
        logger.info("Synchronisation terminée: %s", result)
        return

    if args.command == "admin":
        from .admin.web import run_admin

        run_admin()
        return

    if args.command == "all":
        _run_admin_thread()

    # bot or all -> run the bot in the main thread.
    from .bot.application import run_bot

    run_bot()


if __name__ == "__main__":
    main()
