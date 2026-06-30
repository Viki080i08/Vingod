"""Promo / trial code definitions and redemption logic."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.models import PromoRedemption, User
from ..db import repo

# Available promo codes. Add new ones here freely.
#   days  -> number of free subscription days granted
#   label -> human-readable description shown to the user
PROMO_CODES = {
    "pronokiff": {"days": 7, "label": "1 semaine d'essai gratuite"},
}


def normalize(code: str) -> str:
    return (code or "").strip().lower()


def get_promo(code: str) -> Optional[dict]:
    return PROMO_CODES.get(normalize(code))


def already_redeemed(session: Session, user_id: int, code: str) -> bool:
    return session.scalar(
        select(PromoRedemption).where(
            and_(PromoRedemption.user_id == user_id, PromoRedemption.code == normalize(code))
        )
    ) is not None


def redeem(session: Session, user: User, code: str) -> dict:
    """Attempt to redeem a promo code for a user.

    Returns a dict describing the outcome:
        {"ok": bool, "reason": str, "days": int, "label": str, "expiry": datetime|None}
    """
    promo = get_promo(code)
    if promo is None:
        return {"ok": False, "reason": "invalid"}

    if already_redeemed(session, user.id, code):
        return {"ok": False, "reason": "already_used"}

    settings = get_settings()
    days = promo["days"]
    repo.activate_subscription(
        session,
        user,
        days=days,
        amount=0.0,
        currency=settings.subscription_currency,
        provider=f"promo:{normalize(code)}",
    )
    session.add(
        PromoRedemption(user_id=user.id, code=normalize(code), days=days)
    )
    session.flush()
    return {
        "ok": True,
        "reason": "applied",
        "days": days,
        "label": promo["label"],
        "expiry": user.subscription_expiry,
    }
