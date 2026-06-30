"""Performance statistics (📈 Statistiques)."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...db import repo, session_scope
from ...db.base import RiskProfile
from .. import texts
from ..utils import sync_user_from_update


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sync_user_from_update(update)
    with session_scope() as session:
        global_stats = repo.tip_stats(session)
        per_profile = {
            RiskProfile.SECURE: repo.tip_stats(session, RiskProfile.SECURE),
            RiskProfile.BALANCED: repo.tip_stats(session, RiskProfile.BALANCED),
            RiskProfile.RISKY: repo.tip_stats(session, RiskProfile.RISKY),
        }
    await update.effective_message.reply_text(
        texts.format_stats(global_stats, per_profile), parse_mode=ParseMode.HTML
    )
