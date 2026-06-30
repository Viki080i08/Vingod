"""Subscription & Telegram Payments (💳 Abonnement)."""

from __future__ import annotations

from telegram import LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...config import get_settings
from ...db import repo, session_scope
from .. import keyboards, texts
from ..utils import esc, sync_user_from_update

INVOICE_PAYLOAD_PREFIX = "pronoia-sub"


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    snapshot = sync_user_from_update(update)
    text = texts.subscription_info(
        snapshot,
        settings.subscription_price_eur,
        settings.subscription_currency,
        settings.subscription_duration_days,
        settings.payments_enabled,
    )
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.subscription_keyboard(settings.payments_enabled),
    )


async def subscription_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    settings = get_settings()
    snapshot = sync_user_from_update(update)

    if not settings.payments_enabled:
        # Demo mode: activate immediately, record a simulated payment.
        await query.answer("Mode démo : activation immédiate.")
        with session_scope() as session:
            user = repo.get_user(session, update.effective_user.id)
            repo.activate_subscription(
                session,
                user,
                days=settings.subscription_duration_days,
                amount=settings.subscription_price_eur,
                currency=settings.subscription_currency,
                provider="demo",
                telegram_charge_id=None,
            )
            expiry = user.subscription_expiry
        await query.edit_message_text(
            "✅ <b>Abonnement activé (mode démo)</b>\n\n"
            f"Ton accès Premium est actif jusqu'au <b>{expiry:%d/%m/%Y}</b>.\n"
            "Tu reçois désormais tous les pronostics et analyses IA.",
            parse_mode=ParseMode.HTML,
        )
        return

    await query.answer()
    days = settings.subscription_duration_days
    prices = [
        LabeledPrice(
            label=f"Abonnement Premium {days} jours",
            amount=settings.price_minor_units,
        )
    ]
    payload = f"{INVOICE_PAYLOAD_PREFIX}:{update.effective_user.id}:{days}"
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="PronoIA Premium",
        description=(
            f"Abonnement Premium de {days} jours : tous les pronostics, "
            "analyses IA et combinés optimisés."
        ),
        payload=payload,
        provider_token=settings.payment_provider_token,
        currency=settings.subscription_currency,
        prices=prices,
        start_parameter="pronoia-premium",
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith(INVOICE_PAYLOAD_PREFIX):
        await query.answer(ok=False, error_message="Commande invalide.")
        return
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    payment = update.message.successful_payment
    parts = payment.invoice_payload.split(":")
    days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else settings.subscription_duration_days

    with session_scope() as session:
        user = repo.get_user(session, update.effective_user.id)
        if user is None:
            user, _ = repo.get_or_create_user(session, update.effective_user.id)
        repo.activate_subscription(
            session,
            user,
            days=days,
            amount=payment.total_amount / 100.0,
            currency=payment.currency,
            telegram_charge_id=payment.telegram_payment_charge_id,
            provider_charge_id=payment.provider_payment_charge_id,
            provider="telegram",
        )
        expiry = user.subscription_expiry

    await update.message.reply_text(
        "✅ <b>Paiement confirmé — merci !</b>\n\n"
        f"Ton abonnement Premium est actif jusqu'au <b>{expiry:%d/%m/%Y}</b>.\n"
        "Profite de tous les pronostics et analyses IA. 🚀",
        parse_mode=ParseMode.HTML,
    )


async def subscription_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    snapshot = sync_user_from_update(update)
    with session_scope() as session:
        payments = repo.payment_history(session, snapshot["id"])
        if not payments:
            text = "📜 <b>Historique des paiements</b>\n\nAucun paiement enregistré."
        else:
            lines = ["📜 <b>Historique des paiements</b>\n"]
            for p in payments:
                lines.append(
                    f"• {p.created_at:%d/%m/%Y} — {p.amount:.2f} {esc(p.currency)} "
                    f"({esc(p.provider)}, {p.period_days}j)"
                )
            text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)
