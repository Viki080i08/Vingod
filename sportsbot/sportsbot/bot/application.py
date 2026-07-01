"""Builds and configures the Telegram Application."""

from __future__ import annotations

import httpx
from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from ..config import get_settings
from ..db import init_db
from ..logging_conf import get_logger
from ..scheduler.jobs import register_jobs
from .handlers import register_handlers

logger = get_logger(__name__)


def verify_token(token: str) -> dict:
    """Validate the bot token against Telegram's getMe endpoint.

    Returns the bot info dict on success, raises RuntimeError with a clear,
    actionable message on failure.
    """
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN manquant. Créez un bot avec @BotFather puis "
            "renseignez le token dans le fichier .env."
        )
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
    except httpx.HTTPError as exc:  # network problem
        raise RuntimeError(f"Impossible de joindre Telegram : {exc}") from exc

    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(
            "Token Telegram invalide (réponse "
            f"{data.get('error_code')}: {data.get('description')}).\n"
            "👉 Le token a probablement été révoqué (il avait été partagé "
            "publiquement). Générez-en un NOUVEAU via @BotFather "
            "(/revoke puis /token) et mettez-le dans .env."
        )
    return data["result"]

PUBLIC_COMMANDS = [
    BotCommand("start", "Démarrer / message de bienvenue"),
    BotCommand("menu", "Afficher le menu principal"),
    BotCommand("pronos", "Pronostics du jour"),
    BotCommand("profil", "Mon profil de risque"),
    BotCommand("combine", "Créer un combiné"),
    BotCommand("ia", "Analyse IA des matchs"),
    BotCommand("stats", "Statistiques de performance"),
    BotCommand("abonnement", "Gérer mon abonnement"),
    BotCommand("code", "Utiliser un code promo (ex. pronokiff)"),
    BotCommand("parametres", "Réglages"),
    BotCommand("aide", "Aide"),
    BotCommand("whoami", "Afficher mon identifiant Telegram"),
]


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(PUBLIC_COMMANDS)
    me = await application.bot.get_me()
    logger.info("Bot @%s (id=%s) ready.", me.username, me.id)


def build_application() -> Application:
    settings = get_settings()
    bot_info = verify_token(settings.bot_token)
    logger.info("Token validé pour @%s (id=%s).", bot_info.get("username"), bot_info.get("id"))

    init_db()

    application = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .build()
    )

    register_handlers(application)
    register_jobs(application)
    return application


def run_bot() -> None:
    import asyncio

    try:
        application = build_application()
    except RuntimeError as exc:
        logger.error("Démarrage impossible :\n%s", exc)
        raise SystemExit(2) from exc

    # Ensure the main thread has a usable event loop even if another component
    # (e.g. the admin web server) altered the global event-loop policy.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    logger.info("Starting bot (long polling)... Ctrl+C pour arrêter.")
    application.run_polling(drop_pending_updates=True)
