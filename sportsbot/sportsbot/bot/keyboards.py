"""Reply and inline keyboards used across the bot."""

from __future__ import annotations

from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from ..db.base import Pick, RiskProfile
from . import texts


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [texts.BTN_PRONOS, texts.BTN_PROFILE],
            [texts.BTN_COMBO, texts.BTN_AI],
            [texts.BTN_STATS, texts.BTN_SUB],
            [texts.BTN_SETTINGS],
        ],
        resize_keyboard=True,
    )


def profile_keyboard(prefix: str = "profile") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🟢 Sécurisé", callback_data=f"{prefix}:{RiskProfile.SECURE}")],
            [InlineKeyboardButton("🟡 Équilibré", callback_data=f"{prefix}:{RiskProfile.BALANCED}")],
            [InlineKeyboardButton("🔴 Risqué", callback_data=f"{prefix}:{RiskProfile.RISKY}")],
        ]
    )


def day_nav_keyboard(day_offset: int, horizon: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if day_offset > 0:
        nav_row.append(InlineKeyboardButton("◀️ Jour préc.", callback_data=f"pronos:day:{day_offset-1}"))
    if day_offset < horizon - 1:
        nav_row.append(InlineKeyboardButton("Jour suiv. ▶️", callback_data=f"pronos:day:{day_offset+1}"))
    if nav_row:
        buttons.append(nav_row)
    buttons.append(
        [InlineKeyboardButton("🤖 Analyses détaillées", callback_data=f"ia:list:{day_offset}")]
    )
    return InlineKeyboardMarkup(buttons)


def ai_match_list_keyboard(matches, day_offset: int) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for match in matches[:12]:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{match.home_name} - {match.away_name}",
                    callback_data=f"ia:match:{match.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("📊 Retour pronostics", callback_data=f"pronos:day:{day_offset}")])
    return InlineKeyboardMarkup(rows)


def combo_match_keyboard(matches, day_offset: int = 0) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for match in matches[:10]:
        rows.append(
            [InlineKeyboardButton(
                f"➕ {match.home_name} - {match.away_name}",
                callback_data=f"combo:pickmatch:{match.id}",
            )]
        )
    rows.append(
        [
            InlineKeyboardButton("🧾 Voir mon combiné", callback_data="combo:view"),
            InlineKeyboardButton("🤖 Combiné IA", callback_data="combo:ai"),
        ]
    )
    rows.append([InlineKeyboardButton("🗑️ Vider", callback_data="combo:clear")])
    return InlineKeyboardMarkup(rows)


def combo_pick_keyboard(match) -> InlineKeyboardMarkup:
    a = match.analysis
    home = f"{match.home_name} @ {a.odds_home:.2f}" if a else match.home_name
    draw = f"Nul @ {a.odds_draw:.2f}" if a else "Nul"
    away = f"{match.away_name} @ {a.odds_away:.2f}" if a else match.away_name
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"1 — {home}", callback_data=f"combo:add:{match.id}:{Pick.HOME}")],
            [InlineKeyboardButton(f"X — {draw}", callback_data=f"combo:add:{match.id}:{Pick.DRAW}")],
            [InlineKeyboardButton(f"2 — {away}", callback_data=f"combo:add:{match.id}:{Pick.AWAY}")],
            [InlineKeyboardButton("◀️ Retour", callback_data="combo:back")],
        ]
    )


def combo_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Ajouter un match", callback_data="combo:back")],
            [InlineKeyboardButton("🤖 Optimiser avec l'IA", callback_data="combo:ai")],
            [InlineKeyboardButton("🗑️ Vider le combiné", callback_data="combo:clear")],
        ]
    )


def subscription_keyboard(payments_enabled: bool) -> InlineKeyboardMarkup:
    label = "💳 S'abonner maintenant" if payments_enabled else "💳 S'abonner (démo)"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data="sub:buy")],
            [InlineKeyboardButton("🎁 J'ai un code promo", callback_data="sub:promo")],
            [InlineKeyboardButton("📜 Historique paiements", callback_data="sub:history")],
        ]
    )


def settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    notif_label = "🔕 Désactiver notifications" if notifications_enabled else "🔔 Activer notifications"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎯 Changer mon profil", callback_data="set:profile")],
            [InlineKeyboardButton(notif_label, callback_data="set:notif")],
        ]
    )
