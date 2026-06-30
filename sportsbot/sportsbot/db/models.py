"""SQLAlchemy ORM models for PronoIA.

The schema covers users, subscriptions & payment history, sports data
(teams / matches), AI analyses, individual prediction tips and combo tickets.
Designed to run on PostgreSQL in production and SQLite for local development.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MatchStatus, RiskProfile, SubscriptionStatus, TipStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    # Personalisation
    risk_profile: Mapped[str] = mapped_column(String(16), default=RiskProfile.BALANCED)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    favourite_leagues: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Subscription snapshot (history kept in `payments`)
    subscription_status: Mapped[str] = mapped_column(
        String(16), default=SubscriptionStatus.NONE
    )
    subscription_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    payments: Mapped[List["Payment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tips: Mapped[List["Tip"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    combos: Mapped[List["Combo"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_active_subscription(self) -> bool:
        if self.subscription_status != SubscriptionStatus.ACTIVE:
            return False
        if self.subscription_expiry is None:
            return False
        return self.subscription_expiry > datetime.utcnow()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    provider: Mapped[str] = mapped_column(String(32), default="telegram")
    telegram_charge_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_charge_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    period_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(16), default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="payments")


class Team(Base):
    """A team with its rolling statistics used by the analysis engine."""

    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("name", "league", name="uq_team_league"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    league: Mapped[str] = mapped_column(String(128), default="")
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Rolling form indicators (kept up to date during sync / result updates)
    recent_form: Mapped[str] = mapped_column(String(16), default="")  # e.g. "WWDLW"
    goals_for_avg: Mapped[float] = mapped_column(Float, default=1.3)
    goals_against_avg: Mapped[float] = mapped_column(Float, default=1.3)
    home_strength: Mapped[float] = mapped_column(Float, default=1.0)
    away_strength: Mapped[float] = mapped_column(Float, default=1.0)
    attack_rating: Mapped[float] = mapped_column(Float, default=1.0)
    defense_rating: Mapped[float] = mapped_column(Float, default=1.0)
    key_absences: Mapped[int] = mapped_column(Integer, default=0)
    momentum: Mapped[float] = mapped_column(Float, default=0.0)  # -1..+1 trend
    elo: Mapped[float] = mapped_column(Float, default=1500.0)  # learned strength rating
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("external_id", "provider", name="uq_match_external"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    sport: Mapped[str] = mapped_column(String(32), default="football")
    league: Mapped[str] = mapped_column(String(128), default="")

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])

    # Denormalised names for cheap display
    home_name: Mapped[str] = mapped_column(String(128), default="")
    away_name: Mapped[str] = mapped_column(String(128), default="")

    kickoff: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), default=MatchStatus.SCHEDULED)
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    head_to_head: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    analysis: Mapped[Optional["Analysis"]] = relationship(
        back_populates="match", uselist=False, cascade="all, delete-orphan"
    )


class Analysis(Base):
    """AI analysis output for a single match."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"), unique=True, index=True
    )

    prob_home: Mapped[float] = mapped_column(Float, default=0.0)
    prob_draw: Mapped[float] = mapped_column(Float, default=0.0)
    prob_away: Mapped[float] = mapped_column(Float, default=0.0)

    expected_home_goals: Mapped[float] = mapped_column(Float, default=0.0)
    expected_away_goals: Mapped[float] = mapped_column(Float, default=0.0)

    recommended_pick: Mapped[str] = mapped_column(String(4), default="1")
    recommended_odds: Mapped[float] = mapped_column(Float, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    risk_level: Mapped[str] = mapped_column(String(16), default="medium")
    value_score: Mapped[float] = mapped_column(Float, default=0.0)

    odds_home: Mapped[float] = mapped_column(Float, default=2.0)
    odds_draw: Mapped[float] = mapped_column(Float, default=3.0)
    odds_away: Mapped[float] = mapped_column(Float, default=3.0)

    explanation: Mapped[str] = mapped_column(Text, default="")
    key_factors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    match: Mapped["Match"] = relationship(back_populates="analysis")


class Tip(Base):
    """A single prediction sent to (or selected by) a user, tracked for stats."""

    __tablename__ = "tips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    analysis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("analyses.id"), nullable=True
    )
    pick: Mapped[str] = mapped_column(String(4), default="1")
    odds: Mapped[float] = mapped_column(Float, default=1.0)
    profile: Mapped[str] = mapped_column(String(16), default=RiskProfile.BALANCED)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default=TipStatus.PENDING)
    is_broadcast: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="tips")
    match: Mapped["Match"] = relationship()


class Combo(Base):
    """A combo ticket (accumulator) built by a user or suggested by the AI."""

    __tablename__ = "combos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    profile: Mapped[str] = mapped_column(String(16), default=RiskProfile.BALANCED)
    total_odds: Mapped[float] = mapped_column(Float, default=1.0)
    combined_probability: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default=TipStatus.PENDING)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="combos")
    selections: Mapped[List["ComboSelection"]] = relationship(
        back_populates="combo", cascade="all, delete-orphan"
    )


class ComboSelection(Base):
    __tablename__ = "combo_selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    combo_id: Mapped[int] = mapped_column(ForeignKey("combos.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    pick: Mapped[str] = mapped_column(String(4), default="1")
    odds: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(16), default=TipStatus.PENDING)

    combo: Mapped["Combo"] = relationship(back_populates="selections")
    match: Mapped["Match"] = relationship()


class UserComboDraft(Base):
    """Transient storage of a user's in-progress combo selections."""

    __tablename__ = "user_combo_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    pick: Mapped[str] = mapped_column(String(4), default="1")
    odds: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    match: Mapped["Match"] = relationship()
