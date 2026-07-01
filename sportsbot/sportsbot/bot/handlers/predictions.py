"""Pronostics du jour and AI analysis handlers."""

from __future__ import annotations

from datetime import datetime, timedelta

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...config import get_settings
from ...db import session_scope
from ...db import repo
from ...services.tips import best_opportunities
from .. import keyboards, texts
from ..utils import has_access, sync_user_from_update


async def _render_day(update: Update, day_offset: int, edit: bool = False) -> None:
    settings = get_settings()
    snapshot = sync_user_from_update(update)

    if not has_access(snapshot, update):
        await _reply(update, texts.subscription_required(), edit)
        return

    day_offset = max(0, min(day_offset, settings.forecast_horizon_days - 1))
    day = datetime.utcnow() + timedelta(days=day_offset)
    profile = snapshot["risk_profile"]

    with session_scope() as session:
        opps = best_opportunities(session, profile, limit=6, day=day)
        text = texts.format_day_predictions(opps, day, profile)

    keyboard = keyboards.day_nav_keyboard(day_offset, settings.forecast_horizon_days)
    await _reply(update, text, edit, keyboard)


async def _reply(update: Update, text: str, edit: bool, keyboard=None) -> None:
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )


async def pronos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_day(update, 0, edit=False)


async def pronos_day_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    day_offset = int(query.data.split(":")[2])
    await _render_day(update, day_offset, edit=True)


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for 🤖 Analyse IA: list today's matches to analyse."""
    await _render_ai_list(update, 0, edit=False)


async def _render_ai_list(update: Update, day_offset: int, edit: bool) -> None:
    settings = get_settings()
    snapshot = sync_user_from_update(update)
    if not has_access(snapshot, update):
        await _reply(update, texts.subscription_required(), edit)
        return

    day_offset = max(0, min(day_offset, settings.forecast_horizon_days - 1))
    day = datetime.utcnow() + timedelta(days=day_offset)

    with session_scope() as session:
        matches = list(repo.matches_for_day(session, day))
        # keep only scheduled & analysed matches
        matches = [m for m in matches if m.status == "scheduled" and m.analysis]
        if not matches:
            await _reply(
                update,
                f"🤖 <b>Analyse IA</b>\n\nAucun match analysé pour le {day:%d/%m/%Y}.",
                edit,
            )
            return
        keyboard = keyboards.ai_match_list_keyboard(matches, day_offset)

    await _reply(
        update,
        f"🤖 <b>Analyse IA — {day:%d/%m/%Y}</b>\n\n"
        "Sélectionne un match pour voir l'analyse détaillée :",
        edit,
        keyboard,
    )


async def ai_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    day_offset = int(query.data.split(":")[2])
    await _render_ai_list(update, day_offset, edit=True)


async def ai_match_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    match_id = int(query.data.split(":")[2])

    snapshot = sync_user_from_update(update)
    if not has_access(snapshot, update):
        await query.edit_message_text(
            texts.subscription_required(), parse_mode=ParseMode.HTML
        )
        return

    with session_scope() as session:
        match = repo.get_match(session, match_id)
        if not match or not match.analysis:
            await query.edit_message_text("Match introuvable ou non analysé.")
            return
        text = texts.format_match_analysis(match, match.analysis)

    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
