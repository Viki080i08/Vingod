"""User settings (⚙️ Paramètres)."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...db import repo, session_scope
from .. import keyboards, texts
from ..utils import sync_user_from_update


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot = sync_user_from_update(update)
    await update.effective_message.reply_text(
        texts.settings_message(snapshot),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.settings_keyboard(snapshot["notifications_enabled"]),
    )


async def settings_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎯 Choisis ton profil de risque :",
        reply_markup=keyboards.profile_keyboard("profile"),
    )


async def settings_notif_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    with session_scope() as session:
        user = repo.get_user(session, update.effective_user.id)
        if user:
            user.notifications_enabled = not user.notifications_enabled
            enabled = user.notifications_enabled
        else:
            enabled = True
    await query.answer("🔔 Notifications activées" if enabled else "🔕 Notifications désactivées")
    snapshot = sync_user_from_update(update)
    await query.edit_message_text(
        texts.settings_message(snapshot),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.settings_keyboard(enabled),
    )
