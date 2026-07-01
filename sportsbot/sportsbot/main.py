"""Command-line entry point for PronoIA.

Usage:
    python -m sportsbot bot      # run only the Telegram bot (long polling)
    python -m sportsbot admin    # run only the web admin dashboard
    python -m sportsbot all      # run both (admin in a background thread)
    python -m sportsbot sync     # run a one-off fixtures sync + analysis
    python -m sportsbot initdb   # create database tables and exit
    python -m sportsbot check    # validate config & Telegram token (diagnosis)
"""

from __future__ import annotations

import argparse
import threading

from .logging_conf import get_logger, setup_logging

logger = get_logger(__name__)


def _run_check() -> None:
    """Validate configuration and the Telegram token, print a clear report."""
    from .bot.application import verify_token
    from .config import get_settings

    settings = get_settings()
    print("🔎 Vérification de la configuration PronoIA\n")
    print(f"  Base de données : {settings.database_url}")
    if settings.apifootball_api_key:
        src = "API-Football (TOUS les vrais matchs ✅)"
    elif settings.football_data_api_key:
        src = "football-data.org (vrais matchs majeurs + Coupe du monde)"
    else:
        src = ("TheSportsDB clé de test — COUVERTURE LIMITÉE ⚠️  "
               "(ajoutez APIFOOTBALL_API_KEY gratuit pour tous les matchs)")
    print(f"  Source de données : {src}")
    print(f"  Horizon d'analyse : {settings.forecast_horizon_days} jours")
    print(f"  Paiements : {'réels (Telegram Payments)' if settings.payments_enabled else 'mode démo'}")
    print(f"  Admins : {settings.admin_ids or 'aucun défini'}")
    print(f"  Dashboard web : http://{settings.admin_web_host}:{settings.admin_web_port}\n")

    try:
        info = verify_token(settings.bot_token)
        print(f"  ✅ Token Telegram VALIDE — bot @{info.get('username')} (id={info.get('id')})")
        print("\n➡️  Tout est prêt. Lancez :  python -m sportsbot all")
    except RuntimeError as exc:
        print(f"  ❌ {exc}")
        raise SystemExit(1)


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
        choices=["bot", "admin", "all", "sync", "initdb", "check"],
        help="Composant à lancer (défaut: all)",
    )
    args = parser.parse_args(argv)

    if args.command == "check":
        _run_check()
        return

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
