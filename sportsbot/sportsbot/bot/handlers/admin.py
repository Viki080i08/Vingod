"""Administrator commands (in-chat)."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ...config import get_settings
from ...db import repo, session_scope
from ...db.base import RiskProfile
from ...scheduler.jobs import run_daily_push, run_sync
from ..utils import admin_only, esc


@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    with session_scope() as session:
        users = repo.count_users(session)
        subs = repo.count_active_subscribers(session)
        stats = repo.tip_stats(session)
    text = (
        "🛠️ <b>Panneau administrateur</b>\n\n"
        f"👥 Utilisateurs : <b>{users}</b>\n"
        f"💳 Abonnés actifs : <b>{subs}</b>\n"
        f"🎯 Pronostics : {stats['total']} (réussite {stats['win_rate']}%)\n\n"
        "<b>Commandes :</b>\n"
        "/sync — synchroniser et analyser les matchs\n"
        "/push — envoyer les pronostics du jour aux abonnés\n"
        "/broadcast &lt;message&gt; — message à tous les utilisateurs\n"
        "/grant &lt;telegram_id&gt; [jours] — offrir un abonnement\n"
        "/revoke &lt;telegram_id&gt; — révoquer un abonnement\n\n"
        f"🖥️ Dashboard web : port {settings.admin_web_port}"
    )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@admin_only
async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_message.reply_text("⏳ Synchronisation en cours...")
    result = await asyncio.to_thread(run_sync)
    fx = result["fixtures"]
    await msg.edit_text(
        "✅ Synchronisation terminée.\n"
        f"Matchs récupérés : {fx.get('fixtures', 0)}\n"
        f"Analysés : {fx.get('analysed', 0)}\n"
        f"Résultats réglés : {result['results'].get('settled', 0)}"
    )


@admin_only
async def push_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.effective_message.reply_text("📤 Envoi des pronostics du jour...")
    result = await run_daily_push(context.bot)
    await msg.edit_text(
        f"✅ Pronostics envoyés.\nEnvoyés : {result['sent']} • "
        f"Échecs : {result['failed']} • Bloqués : {result['blocked']}"
    )


@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text(
            "Usage : /broadcast votre message ici"
        )
        return
    message = " ".join(context.args)
    with session_scope() as session:
        targets = [u.telegram_id for u in repo.all_users(session) if not u.is_blocked]

    sent, failed = 0, 0
    for tid in targets:
        try:
            await context.bot.send_message(
                chat_id=tid, text=f"📢 <b>Annonce</b>\n\n{esc(message)}", parse_mode=ParseMode.HTML
            )
            sent += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)
    await update.effective_message.reply_text(
        f"✅ Annonce envoyée à {sent} utilisateur(s) ({failed} échec(s))."
    )


@admin_only
async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Usage : /grant <telegram_id> [jours]")
        return
    target_id = int(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else settings.subscription_duration_days

    with session_scope() as session:
        user, _ = repo.get_or_create_user(session, target_id)
        repo.activate_subscription(
            session, user, days=days, amount=0.0,
            currency=settings.subscription_currency, provider="admin",
        )
        expiry = user.subscription_expiry
    await update.effective_message.reply_text(
        f"✅ Abonnement offert à {target_id} jusqu'au {expiry:%d/%m/%Y}."
    )


@admin_only
async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Usage : /revoke <telegram_id>")
        return
    target_id = int(context.args[0])
    from ...db.base import SubscriptionStatus

    with session_scope() as session:
        user = repo.get_user(session, target_id)
        if not user:
            await update.effective_message.reply_text("Utilisateur introuvable.")
            return
        user.subscription_status = SubscriptionStatus.EXPIRED
        user.subscription_expiry = None
    await update.effective_message.reply_text(f"✅ Abonnement révoqué pour {target_id}.")
