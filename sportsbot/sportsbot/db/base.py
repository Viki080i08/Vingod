"""Declarative base and shared enum-like constants for the data model."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class RiskProfile:
    SECURE = "secure"
    BALANCED = "balanced"
    RISKY = "risky"

    ALL = (SECURE, BALANCED, RISKY)

    LABELS = {
        SECURE: "🟢 Sécurisé",
        BALANCED: "🟡 Équilibré",
        RISKY: "🔴 Risqué",
    }

    @classmethod
    def label(cls, value: str) -> str:
        return cls.LABELS.get(value, "🟡 Équilibré")


class SubscriptionStatus:
    NONE = "none"
    ACTIVE = "active"
    EXPIRED = "expired"


class MatchStatus:
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


class TipStatus:
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class Pick:
    """Possible 1X2 outcomes used by the analysis engine and tips."""

    HOME = "1"
    DRAW = "X"
    AWAY = "2"

    LABELS = {
        HOME: "Victoire domicile",
        DRAW: "Match nul",
        AWAY: "Victoire extérieur",
    }
