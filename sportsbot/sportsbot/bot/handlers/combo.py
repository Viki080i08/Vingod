"""Combo (accumulator) builder — 🎟️ Créer un combiné."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...db import repo, session_scope
from ...services.tips import build_ai_combo
from .. import keyboards, texts
from ..utils import esc, has_access, pick_label, sync_user_from_update


def _draft_summary(session, user_id: int) -> str:
    rows = repo.get_draft(session, user_id)
    if not rows:
        return "🧾 Ton combiné est vide. Ajoute des matchs ci-dessous."
    total = 1.0
    lines = ["🧾 <b>Ton combiné en cours :</b>"]
    for i, row in enumerate(rows, 1):
        match = row.match
        total *= row.odds
        label = pick_label(row.pick, match.home_name, match.away_name)
        lines.append(
            f"<b>{i}.</b> {esc(match.home_name)} 🆚 {esc(match.away_name)} — "
            f"{esc(label)} @ <b>{row.odds:.2f}</b>"
        )
    lines.append(f"\n💰 <b>Cote totale : {total:.2f}</b>")
    return "\n".join(lines)


async def combo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_match_list(update, edit=False)


async def _show_match_list(update: Update, edit: bool) -> None:
    snapshot = sync_user_from_update(update)
    if not has_access(snapshot, update):
        await _reply(update, texts.subscription_required(), edit)
        return

    with session_scope() as session:
        matches = [m for m in repo.upcoming_matches(session, 5) if m.analysis]
        summary = _draft_summary(session, snapshot["id"])
        if not matches:
            await _reply(update, "Aucun match analysé disponible pour le moment.", edit)
            return
        keyboard = keyboards.combo_match_keyboard(matches)

    text = (
        "🎟️ <b>Créer un combiné</b>\n\n"
        f"{summary}\n\n"
        "Sélectionne un match à ajouter, puis choisis ton pari :"
    )
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


async def combo_pickmatch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    match_id = int(query.data.split(":")[2])
    with session_scope() as session:
        match = repo.get_match(session, match_id)
        if not match or not match.analysis:
            await query.answer("Match indisponible.", show_alert=True)
            return
        text = (
            f"⚽ <b>{esc(match.home_name)}</b> 🆚 <b>{esc(match.away_name)}</b>\n"
            f"🏆 {esc(match.league)}\n\n"
            "Choisis ton pari pour ce match :"
        )
        keyboard = keyboards.combo_pick_keyboard(match)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def combo_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, match_id, pick = query.data.split(":")
    match_id = int(match_id)
    snapshot = sync_user_from_update(update)

    with session_scope() as session:
        match = repo.get_match(session, match_id)
        if not match or not match.analysis:
            await query.answer("Match indisponible.", show_alert=True)
            return
        odds = {
            "1": match.analysis.odds_home,
            "X": match.analysis.odds_draw,
            "2": match.analysis.odds_away,
        }[pick]
        added = repo.add_draft_selection(session, snapshot["id"], match_id, pick, odds)

    await query.answer("✅ Ajouté au combiné" if added else "🔁 Sélection mise à jour")
    await _show_match_list(update, edit=True)


async def combo_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    snapshot = sync_user_from_update(update)
    with session_scope() as session:
        summary = _draft_summary(session, snapshot["id"])
    await query.edit_message_text(
        summary, parse_mode=ParseMode.HTML, reply_markup=keyboards.combo_view_keyboard()
    )


async def combo_clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("🗑️ Combiné vidé")
    snapshot = sync_user_from_update(update)
    with session_scope() as session:
        repo.clear_draft(session, snapshot["id"])
    await _show_match_list(update, edit=True)


async def combo_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await _show_match_list(update, edit=True)


async def combo_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("🤖 L'IA construit ton combiné...")
    snapshot = sync_user_from_update(update)

    with session_scope() as session:
        combo = build_ai_combo(session, snapshot["risk_profile"], user_id=snapshot["id"])
        if combo is None:
            await query.edit_message_text(
                "🤖 Pas assez d'opportunités fiables pour construire un combiné "
                "selon ton profil actuel. Réessaie plus tard."
            )
            return
        match_ids = [s.match_id for s in combo.selections]
        matches_by_id = {
            mid: repo.get_match(session, mid) for mid in match_ids
        }
        text = texts.format_combo(
            combo, matches_by_id, title="🤖 <b>Combiné optimisé par l'IA</b>"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
