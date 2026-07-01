"""Risk profile management (🎯 Mon profil risque)."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...ai.profiles import describe_profile
from ...db import repo, session_scope
from ...db.base import RiskProfile
from .. import keyboards
from ..utils import md_to_html, sync_user_from_update


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot = sync_user_from_update(update)
    current = snapshot["risk_profile"]
    text = (
        "🎯 <b>Mon profil de risque</b>\n\n"
        f"Profil actuel : <b>{RiskProfile.label(current)}</b>\n\n"
        f"{md_to_html(describe_profile(current))}\n\n"
        "Choisis un nouveau profil ci-dessous :"
    )
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=keyboards.profile_keyboard("profile")
    )


async def profile_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    profile = query.data.split(":", 1)[1]
    if profile not in RiskProfile.ALL:
        profile = RiskProfile.BALANCED

    with session_scope() as session:
        user = repo.get_user(session, update.effective_user.id)
        if user:
            user.risk_profile = profile
            user.onboarded = True

    await query.edit_message_text(
        f"✅ Profil mis à jour : <b>{RiskProfile.label(profile)}</b>\n\n"
        f"{md_to_html(describe_profile(profile))}\n\n"
        "L'IA adaptera désormais ses recommandations à ce profil.",
        parse_mode=ParseMode.HTML,
    )
