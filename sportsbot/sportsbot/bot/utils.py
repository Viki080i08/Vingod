"""Shared helpers for Telegram handlers."""

from __future__ import annotations

import html
import re
from datetime import datetime
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from ..config import get_settings
from ..db import session_scope
from ..db.base import Pick
from ..db import repo

_BOLD_RE = re.compile(r"\*(.+?)\*")


def md_to_html(text: str) -> str:
    """Escape HTML then convert *bold* markdown markers to <b> tags."""
    escaped = html.escape(text)
    return _BOLD_RE.sub(r"<b>\1</b>", escaped)


def esc(text) -> str:
    return html.escape(str(text))


def pick_label(pick: str, home_name: str, away_name: str) -> str:
    return {
        Pick.HOME: f"Victoire {home_name}",
        Pick.DRAW: "Match nul",
        Pick.AWAY: f"Victoire {away_name}",
    }.get(pick, pick)


def format_kickoff(dt: datetime) -> str:
    return dt.strftime("%d/%m %H:%M")


def sync_user_from_update(update: Update):
    """Ensure the Telegram user exists in DB and return a detached snapshot dict."""
    tg_user = update.effective_user
    with session_scope() as session:
        user, created = repo.get_or_create_user(
            session,
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            language_code=tg_user.language_code,
        )
        snapshot = {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "risk_profile": user.risk_profile,
            "onboarded": user.onboarded,
            "notifications_enabled": user.notifications_enabled,
            "subscription_status": user.subscription_status,
            "subscription_expiry": user.subscription_expiry,
            "is_blocked": user.is_blocked,
            "has_active_subscription": user.has_active_subscription,
            "created": created,
        }
    return snapshot


def is_admin(update: Update) -> bool:
    settings = get_settings()
    return update.effective_user is not None and settings.is_admin(update.effective_user.id)


def has_access(snapshot: dict, update: Update) -> bool:
    """Premium access: active subscription OR admin."""
    return snapshot.get("has_active_subscription") or is_admin(update)


def admin_only(func: Callable):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not is_admin(update):
            await update.effective_message.reply_text(
                "⛔️ Commande réservée aux administrateurs."
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
