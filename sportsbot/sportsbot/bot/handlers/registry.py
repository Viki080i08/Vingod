"""Registers every handler onto the Telegram Application."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from ...logging_conf import get_logger
from .. import texts
from . import admin, combo, predictions, profile, settings, start, stats, subscription

logger = get_logger(__name__)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error while processing update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Une erreur est survenue. Réessaie ou utilise /menu."
            )
        except Exception:  # noqa: BLE001
            pass


# Map reply-keyboard button text to the corresponding command handler.
_TEXT_ROUTES = {
    texts.BTN_PRONOS: predictions.pronos_command,
    texts.BTN_PROFILE: profile.profile_command,
    texts.BTN_COMBO: combo.combo_command,
    texts.BTN_AI: predictions.ai_command,
    texts.BTN_STATS: stats.stats_command,
    texts.BTN_SUB: subscription.subscription_command,
    texts.BTN_SETTINGS: settings.settings_command,
}


async def _text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.effective_message.text or "").strip()
    handler = _TEXT_ROUTES.get(text)

    # If we are waiting for a promo code and the user did not tap a menu button,
    # treat the message as the promo code.
    if context.user_data.get(subscription.AWAITING_PROMO_KEY) and handler is None:
        await subscription.apply_promo_code(update, context, text)
        return

    if handler:
        context.user_data.pop(subscription.AWAITING_PROMO_KEY, None)
        await handler(update, context)
    else:
        await start.menu_command(update, context)


def register_handlers(application: Application) -> None:
    # --- Commands ---
    application.add_handler(CommandHandler("start", start.start_command))
    application.add_handler(CommandHandler("menu", start.menu_command))
    application.add_handler(CommandHandler(["aide", "help"], start.help_command))
    application.add_handler(CommandHandler("whoami", start.whoami_command))

    application.add_handler(CommandHandler("pronos", predictions.pronos_command))
    application.add_handler(CommandHandler("profil", profile.profile_command))
    application.add_handler(CommandHandler("combine", combo.combo_command))
    application.add_handler(CommandHandler("ia", predictions.ai_command))
    application.add_handler(CommandHandler("stats", stats.stats_command))
    application.add_handler(CommandHandler("abonnement", subscription.subscription_command))
    application.add_handler(CommandHandler("code", subscription.code_command))
    application.add_handler(CommandHandler("parametres", settings.settings_command))

    # --- Admin commands ---
    application.add_handler(CommandHandler("admin", admin.admin_command))
    application.add_handler(CommandHandler("sync", admin.sync_command))
    application.add_handler(CommandHandler("push", admin.push_command))
    application.add_handler(CommandHandler("broadcast", admin.broadcast_command))
    application.add_handler(CommandHandler("grant", admin.grant_command))
    application.add_handler(CommandHandler("revoke", admin.revoke_command))

    # --- Callback queries ---
    application.add_handler(CallbackQueryHandler(start.onboarding_profile_callback, pattern=r"^onboard:"))
    application.add_handler(CallbackQueryHandler(profile.profile_set_callback, pattern=r"^profile:"))
    application.add_handler(CallbackQueryHandler(predictions.pronos_day_callback, pattern=r"^pronos:day:"))
    application.add_handler(CallbackQueryHandler(predictions.ai_list_callback, pattern=r"^ia:list:"))
    application.add_handler(CallbackQueryHandler(predictions.ai_match_callback, pattern=r"^ia:match:"))

    application.add_handler(CallbackQueryHandler(combo.combo_pickmatch_callback, pattern=r"^combo:pickmatch:"))
    application.add_handler(CallbackQueryHandler(combo.combo_add_callback, pattern=r"^combo:add:"))
    application.add_handler(CallbackQueryHandler(combo.combo_view_callback, pattern=r"^combo:view$"))
    application.add_handler(CallbackQueryHandler(combo.combo_clear_callback, pattern=r"^combo:clear$"))
    application.add_handler(CallbackQueryHandler(combo.combo_back_callback, pattern=r"^combo:back$"))
    application.add_handler(CallbackQueryHandler(combo.combo_ai_callback, pattern=r"^combo:ai$"))

    application.add_handler(CallbackQueryHandler(subscription.subscription_buy_callback, pattern=r"^sub:buy$"))
    application.add_handler(CallbackQueryHandler(subscription.subscription_promo_callback, pattern=r"^sub:promo$"))
    application.add_handler(CallbackQueryHandler(subscription.subscription_history_callback, pattern=r"^sub:history$"))

    application.add_handler(CallbackQueryHandler(settings.settings_profile_callback, pattern=r"^set:profile$"))
    application.add_handler(CallbackQueryHandler(settings.settings_notif_callback, pattern=r"^set:notif$"))

    # --- Payments ---
    application.add_handler(PreCheckoutQueryHandler(subscription.precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, subscription.successful_payment_callback)
    )

    # --- Reply keyboard text router (must be last among message handlers) ---
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router)
    )

    application.add_error_handler(_error_handler)
    logger.info("Handlers registered.")
