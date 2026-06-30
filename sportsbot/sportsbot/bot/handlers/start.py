"""Onboarding: /start welcome, risk-profile selection, /menu, /aide, /whoami."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...db import session_scope
from ...db import repo
from ...db.base import RiskProfile
from .. import keyboards, texts
from ..utils import sync_user_from_update


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot = sync_user_from_update(update)

    await update.effective_message.reply_text(
        texts.welcome_message(snapshot["first_name"]),
        parse_mode=ParseMode.HTML,
    )

    if not snapshot["onboarded"]:
        await update.effective_message.reply_text(
            texts.profile_question(),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.profile_keyboard(prefix="onboard"),
        )
    else:
        await send_menu(update, snapshot)


async def send_menu(update: Update, snapshot: dict) -> None:
    await update.effective_message.reply_text(
        texts.menu_message(snapshot),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_keyboard(),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snapshot = sync_user_from_update(update)
    await send_menu(update, snapshot)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        texts.help_message(), parse_mode=ParseMode.HTML
    )


async def whoami_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.effective_message.reply_text(
        f"🆔 Ton identifiant Telegram est : <code>{user.id}</code>\n"
        f"Nom : {user.full_name}",
        parse_mode=ParseMode.HTML,
    )


async def onboarding_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, profile = query.data.split(":", 1)
    if profile not in RiskProfile.ALL:
        profile = RiskProfile.BALANCED

    with session_scope() as session:
        user = repo.get_user(session, update.effective_user.id)
        if user:
            user.risk_profile = profile
            user.onboarded = True

    await query.edit_message_text(
        f"✅ Profil enregistré : <b>{RiskProfile.label(profile)}</b>\n\n"
        "Tu peux maintenant explorer le menu ci-dessous 👇",
        parse_mode=ParseMode.HTML,
    )

    snapshot = sync_user_from_update(update)
    await send_menu(update, snapshot)
