"""Telegram bot wiring: command handlers, security, alert job."""
from __future__ import annotations

import functools
import logging
from typing import Callable, List

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..ai.engine import ai_engine
from ..config import settings
from ..data.economic_calendar import economic_calendar_provider
from ..data.market_data import MarketDataError, market_data_provider
from ..data.news import news_provider
from ..risk import position_size
from ..services.learning import get_performance, resolve_open_predictions
from ..services.signal_scanner import signal_scanner
from ..storage.database import get_db
from . import formatting
from .security import is_admin, rate_limiter

logger = logging.getLogger(__name__)

START_TEXT = (
    "👋 <b>Bienvenue sur l'Assistant IA de Trading</b>\n\n"
    "Je combine analyse technique, fondamentale, quantitative et machine learning "
    "pour repérer les meilleures configurations de marché en temps réel "
    "(crypto, forex, actions, indices).\n\n"
    "<b>Commandes principales :</b>\n"
    "• /analyse <code>BTCUSDT</code> — analyse complète d'un actif\n"
    "• /signaux — meilleures opportunités détectées\n"
    "• /top — classement des trades par score IA\n"
    "• /news <code>[sujet]</code> — actualités + sentiment\n"
    "• /calendrier — événements économiques importants\n"
    "• /risque — taille de position & gestion du risque\n"
    "• /portfolio — suivi de votre portefeuille\n"
    "• /alertes <code>on|off</code> — recevoir les signaux automatiques\n"
    "• /perf — performance historique de l'IA\n"
    "• /aide — aide détaillée\n\n"
    "<i>⚠️ Outil d'aide à la décision. Pas un conseil financier. "
    "Aucun gain n'est garanti — le trading comporte des risques.</i>"
)

HELP_TEXT = (
    "🆘 <b>Aide détaillée</b>\n\n"
    "<b>/analyse SYMBOLE [TF]</b>\n"
    "Analyse complète. TF = 15m, 1h, 4h, 1d (défaut 1h).\n"
    "Ex : <code>/analyse ETHUSDT 4h</code>\n\n"
    "<b>/signaux</b> — meilleures opportunités (score ≥ seuil).\n"
    "<b>/top</b> — top des trades classés par score IA.\n\n"
    "<b>/news [sujet]</b> — actualités + analyse de sentiment.\n"
    "Ex : <code>/news bitcoin</code>\n\n"
    "<b>/calendrier</b> — événements macro à venir.\n\n"
    "<b>/risque CAPITAL RISQUE% ENTREE STOP [OBJECTIF]</b>\n"
    "Ex : <code>/risque 1000 1 30000 29000 33000</code>\n\n"
    "<b>/portfolio</b>\n"
    "• <code>/portfolio</code> — voir le portefeuille\n"
    "• <code>/portfolio add BTCUSDT 0.5 30000</code>\n"
    "• <code>/portfolio clear</code>\n\n"
    "<b>/alertes on|off</b> — activer/désactiver les alertes automatiques.\n"
    "<b>/perf</b> — performance et taux de réussite de l'IA."
)


def guarded(func: Callable) -> Callable:
    """Register the user, block spam and blocked users, then run the handler."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message = update.effective_message
        if user is None or message is None:
            logger.warning("Update without user/message ignored: %s", update)
            return

        logger.info(
            "Commande reçue: /%s de %s (id=%s)",
            func.__name__.removeprefix("cmd_"),
            user.username or user.first_name,
            user.id,
        )

        db = get_db()
        await db.upsert_user(
            user.id, user.username or "", user.first_name or "", is_admin(user.id)
        )
        record = await db.get_user(user.id)
        if record and record.get("is_blocked"):
            return  # silently ignore blocked users

        if not is_admin(user.id) and not rate_limiter.check(user.id):
            wait = rate_limiter.retry_after(user.id)
            await message.reply_text(
                f"⏳ Trop de requêtes. Réessayez dans {wait}s (anti-spam)."
            )
            return
        try:
            await func(update, context)
        except MarketDataError as exc:
            await message.reply_text(f"⚠️ {exc}")
        except Exception:  # pragma: no cover - defensive top-level guard
            logger.exception("Handler %s failed", func.__name__)
            await message.reply_text(
                "❌ Une erreur interne est survenue. Réessayez plus tard."
            )

    return wrapper


async def _reply(update: Update, text: str, disable_preview: bool = True) -> None:
    message = update.effective_message
    if message is None:
        return
    try:
        await message.reply_text(
            text, parse_mode=ParseMode.HTML, disable_web_page_preview=disable_preview
        )
    except Exception:
        # Fallback if Telegram rejects HTML formatting.
        logger.warning("HTML reply failed, sending plain text", exc_info=True)
        plain = text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
        plain = plain.replace("<code>", "").replace("</code>", "")
        await message.reply_text(plain, disable_web_page_preview=disable_preview)


# --------------------------------------------------------------------- handlers
@guarded
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, START_TEXT)


@guarded
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, HELP_TEXT)


@guarded
async def cmd_analyse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await _reply(update, "Usage : <code>/analyse SYMBOLE [TF]</code>\nEx : <code>/analyse BTCUSDT 1h</code>")
        return
    symbol = args[0]
    timeframe = args[1].lower() if len(args) > 1 else "1h"
    if timeframe not in {"15m", "1h", "4h", "1d"}:
        timeframe = "1h"

    msg = await update.effective_message.reply_text("🔎 Analyse en cours…")
    analysis = await ai_engine.analyze_symbol(symbol, timeframe=timeframe)
    try:
        await get_db().record_prediction(analysis.signal)
    except Exception:  # pragma: no cover
        logger.exception("Could not record prediction")
    await msg.edit_text(
        formatting.format_analysis(analysis),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@guarded
async def cmd_signaux(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_message.reply_text("📡 Recherche d'opportunités…")
    signals = await signal_scanner.best_opportunities(limit=5)
    await msg.edit_text(
        formatting.format_signal_list(signals, "📡 Meilleures opportunités IA"),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@guarded
async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_message.reply_text("🏆 Classement des trades…")
    signals = await signal_scanner.top(limit=10)
    await msg.edit_text(
        formatting.format_signal_list(signals, "🏆 Top trades (score IA)"),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@guarded
async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args) if context.args else None
    items = await news_provider.get_news(query=query, limit=8)
    title = f"📰 Actualités — {query}" if query else "📰 Actualités importantes"
    await _reply(update, formatting.format_news(items, title), disable_preview=True)


@guarded
async def cmd_calendrier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    events = await economic_calendar_provider.get_events(importance="high", limit=12)
    await _reply(update, formatting.format_economic_events(events))


@guarded
async def cmd_risque(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 4:
        await _reply(
            update,
            "Usage : <code>/risque CAPITAL RISQUE% ENTREE STOP [OBJECTIF]</code>\n"
            "Ex : <code>/risque 1000 1 30000 29000 33000</code>",
        )
        return
    try:
        capital = float(args[0])
        risk_pct = float(args[1])
        entry = float(args[2])
        stop = float(args[3])
        target = float(args[4]) if len(args) > 4 else None
    except ValueError:
        await _reply(update, "❌ Paramètres invalides. Utilisez des nombres.")
        return
    try:
        result = position_size(capital, risk_pct, entry, stop, target)
    except ValueError as exc:
        await _reply(update, f"❌ {exc}")
        return
    await _reply(update, formatting.format_risk(result, "position"))


@guarded
async def cmd_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    user_id = update.effective_user.id
    args = context.args

    if args and args[0].lower() == "add":
        if len(args) < 4:
            await _reply(update, "Usage : <code>/portfolio add SYMBOLE QUANTITE PRIX</code>")
            return
        try:
            symbol = args[1].upper()
            qty = float(args[2])
            price = float(args[3])
        except ValueError:
            await _reply(update, "❌ Quantité / prix invalides.")
            return
        await db.add_position(user_id, symbol, qty, price)
        await _reply(update, f"✅ Position ajoutée : {qty} {symbol} @ {formatting.fmt_price(price)}")
        return

    if args and args[0].lower() == "clear":
        removed = await db.clear_portfolio(user_id)
        await _reply(update, f"🗑️ Portefeuille vidé ({removed} position(s) supprimée(s)).")
        return

    positions = await db.get_portfolio(user_id)
    valuations = []
    for p in positions:
        price = None
        try:
            quote = await market_data_provider.get_quote(p["symbol"])
            price = quote.price
        except Exception:
            price = None
        value = (price or p["entry_price"]) * p["quantity"]
        cost = p["entry_price"] * p["quantity"]
        valuations.append(
            {
                "symbol": p["symbol"],
                "quantity": p["quantity"],
                "entry_price": p["entry_price"],
                "price": price,
                "value": value,
                "cost": cost,
            }
        )
    await _reply(update, formatting.format_portfolio(positions, valuations))


@guarded
async def cmd_alertes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    user_id = update.effective_user.id
    arg = context.args[0].lower() if context.args else ""
    if arg == "on":
        await db.set_alerts(user_id, True)
        await _reply(update, "🔔 Alertes automatiques <b>activées</b>. Vous recevrez les signaux à haute conviction.")
    elif arg == "off":
        await db.set_alerts(user_id, False)
        await _reply(update, "🔕 Alertes automatiques <b>désactivées</b>.")
    else:
        await _reply(update, "Usage : <code>/alertes on</code> ou <code>/alertes off</code>")


@guarded
async def cmd_perf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    perf = await get_performance()
    text = (
        "📈 <b>Performance de l'IA (auto-apprentissage)</b>\n\n"
        f"• Prédictions totales : {perf['total']}\n"
        f"• Résolues : {perf['resolved']} (ouvertes : {perf['open']})\n"
        f"• Gagnantes : {perf['wins']} · Perdantes : {perf['losses']}\n"
        f"• Taux de réussite : {perf['win_rate']}%\n"
        f"• Score IA moyen : {perf['avg_score']}/100\n\n"
        "<i>L'IA enregistre chaque signal, compare au résultat réel et affine ses modèles.</i>"
    )
    await _reply(update, text)


@guarded
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await _reply(update, "⛔ Commande réservée aux administrateurs.")
        return
    db = get_db()
    users = await db.count_users()
    subs = await db.alert_subscribers()
    perf = await get_performance()
    await _reply(
        update,
        "🛠️ <b>Statistiques admin</b>\n\n"
        f"• Utilisateurs : {users}\n"
        f"• Abonnés alertes : {len(subs)}\n"
        f"• Prédictions : {perf['total']} (réussite {perf['win_rate']}%)",
    )


# ------------------------------------------------------------------- jobs
async def alert_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: scan for high-conviction signals and push to subscribers."""
    logger.info("Running scheduled signal scan…")
    try:
        signals = await signal_scanner.best_opportunities(limit=3, min_score=settings.signal_min_score)
    except Exception:
        logger.exception("Scheduled scan failed")
        return

    if not signals:
        logger.info("No high-conviction signals this cycle.")
        return

    db = get_db()
    recipients: List[int] = list(await db.alert_subscribers())
    if settings.alerts_chat_id:
        try:
            recipients.append(int(settings.alerts_chat_id))
        except ValueError:
            recipients.append(settings.alerts_chat_id)  # type: ignore[arg-type]

    for signal in signals:
        try:
            await db.record_prediction(signal)
        except Exception:  # pragma: no cover
            logger.exception("Could not record scanned prediction")
        text = "🚨 <b>Nouvelle opportunité détectée</b>\n\n" + formatting.format_signal(signal)
        for chat_id in recipients:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception as exc:  # pragma: no cover - user may have blocked the bot
                logger.debug("Could not send alert to %s: %s", chat_id, exc)


async def learning_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: resolve open predictions to measure real performance."""
    try:
        counts = await resolve_open_predictions()
        logger.info("Learning cycle: %s", counts)
    except Exception:
        logger.exception("Learning job failed")


async def cmd_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply when the user sends plain text instead of a command."""
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    logger.info("Message texte de %s (id=%s): %s", user.username or user.first_name, user.id, message.text)
    await message.reply_text(
        "👋 Bonjour ! Je suis l'assistant IA de trading.\n\n"
        "Tapez /start pour commencer ou /aide pour la liste des commandes.\n\n"
        "Exemples :\n"
        "• /analyse BTCUSDT\n"
        "• /signaux\n"
        "• /news bitcoin"
    )


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Erreur Telegram non gérée", exc_info=context.error)


BOT_COMMANDS = [
    BotCommand("start", "Démarrer le bot"),
    BotCommand("analyse", "Analyser un actif (ex: BTCUSDT)"),
    BotCommand("signaux", "Meilleures opportunités IA"),
    BotCommand("top", "Top trades par score"),
    BotCommand("news", "Actualités + sentiment"),
    BotCommand("calendrier", "Événements économiques"),
    BotCommand("risque", "Calcul taille de position"),
    BotCommand("portfolio", "Suivi portefeuille"),
    BotCommand("alertes", "Alertes auto on/off"),
    BotCommand("perf", "Performance de l'IA"),
    BotCommand("aide", "Aide détaillée"),
]


async def _post_init(app: Application) -> None:
    await get_db().init()
    logger.info("Database initialised at %s", settings.database_path)

    me = await app.bot.get_me()
    await app.bot.set_my_commands(BOT_COMMANDS)
    await app.bot.delete_webhook(drop_pending_updates=False)

    print(f"✓ Bot connecté : @{me.username} ({me.first_name})", flush=True)
    print("✓ En écoute — ouvrez Telegram et tapez /start\n", flush=True)
    logger.info("Bot ready: @%s (id=%s)", me.username, me.id)


def build_application() -> Application:
    settings.validate()
    app = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["aide", "help"], cmd_help))
    app.add_handler(CommandHandler(["analyse", "analyze"], cmd_analyse))
    app.add_handler(CommandHandler(["signaux", "signals"], cmd_signaux))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler(["calendrier", "calendar"], cmd_calendrier))
    app.add_handler(CommandHandler(["risque", "risk"], cmd_risque))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))
    app.add_handler(CommandHandler(["alertes", "alerts"], cmd_alertes))
    app.add_handler(CommandHandler("perf", cmd_perf))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_fallback),
    )
    app.add_error_handler(_on_error)

    if app.job_queue is not None:
        app.job_queue.run_repeating(
            alert_job, interval=settings.scan_interval_seconds, first=30
        )
        app.job_queue.run_repeating(
            learning_job, interval=max(settings.scan_interval_seconds, 600), first=60
        )
    else:  # pragma: no cover
        logger.warning("JobQueue unavailable; automatic alerts disabled.")

    return app
