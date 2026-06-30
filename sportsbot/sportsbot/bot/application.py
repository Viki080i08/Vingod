"""Builds and configures the Telegram Application."""

from __future__ import annotations

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from ..config import get_settings
from ..db import init_db
from ..logging_conf import get_logger
from ..scheduler.jobs import register_jobs
from .handlers import register_handlers

logger = get_logger(__name__)

PUBLIC_COMMANDS = [
    BotCommand("start", "Démarrer / message de bienvenue"),
    BotCommand("menu", "Afficher le menu principal"),
    BotCommand("pronos", "Pronostics du jour"),
    BotCommand("profil", "Mon profil de risque"),
    BotCommand("combine", "Créer un combiné"),
    BotCommand("ia", "Analyse IA des matchs"),
    BotCommand("stats", "Statistiques de performance"),
    BotCommand("abonnement", "Gérer mon abonnement"),
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
    if not settings.bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN manquant. Renseignez-le dans le fichier .env."
        )

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
    application = build_application()
    logger.info("Starting bot (long polling)...")
    application.run_polling(drop_pending_updates=True)
