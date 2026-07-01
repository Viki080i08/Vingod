"""Repository helpers: high level queries used by the bot and dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .base import MatchStatus, SubscriptionStatus, TipStatus
from .models import (
    Analysis,
    Combo,
    ComboSelection,
    Match,
    Payment,
    Team,
    Tip,
    User,
    UserComboDraft,
)


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
def get_or_create_user(session: Session, telegram_id: int, **kwargs) -> tuple[User, bool]:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        # Refresh light profile fields if provided.
        for field in ("username", "first_name", "language_code"):
            value = kwargs.get(field)
            if value:
                setattr(user, field, value)
        return user, False

    user = User(
        telegram_id=telegram_id,
        username=kwargs.get("username"),
        first_name=kwargs.get("first_name"),
        language_code=kwargs.get("language_code"),
    )
    session.add(user)
    session.flush()
    return user, True


def get_user(session: Session, telegram_id: int) -> Optional[User]:
    return session.scalar(select(User).where(User.telegram_id == telegram_id))


def all_users(session: Session) -> Sequence[User]:
    return session.scalars(select(User).order_by(User.created_at.desc())).all()


def active_subscribers(session: Session) -> Sequence[User]:
    now = datetime.utcnow()
    stmt = select(User).where(
        and_(
            User.subscription_status == SubscriptionStatus.ACTIVE,
            User.subscription_expiry > now,
            User.notifications_enabled.is_(True),
            User.is_blocked.is_(False),
        )
    )
    return session.scalars(stmt).all()


def count_users(session: Session) -> int:
    return session.scalar(select(func.count(User.id))) or 0


def count_active_subscribers(session: Session) -> int:
    now = datetime.utcnow()
    return session.scalar(
        select(func.count(User.id)).where(
            and_(
                User.subscription_status == SubscriptionStatus.ACTIVE,
                User.subscription_expiry > now,
            )
        )
    ) or 0


# --------------------------------------------------------------------------- #
# Subscriptions / payments
# --------------------------------------------------------------------------- #
def activate_subscription(
    session: Session,
    user: User,
    days: int,
    amount: float,
    currency: str,
    telegram_charge_id: Optional[str] = None,
    provider_charge_id: Optional[str] = None,
    provider: str = "telegram",
) -> Payment:
    now = datetime.utcnow()
    base = user.subscription_expiry if user.has_active_subscription else now
    user.subscription_status = SubscriptionStatus.ACTIVE
    user.subscription_expiry = base + timedelta(days=days)
    user.is_blocked = False

    payment = Payment(
        user_id=user.id,
        amount=amount,
        currency=currency,
        provider=provider,
        telegram_charge_id=telegram_charge_id,
        provider_charge_id=provider_charge_id,
        period_days=days,
        status="paid",
    )
    session.add(payment)
    session.flush()
    return payment


def expire_due_subscriptions(session: Session) -> int:
    """Mark expired subscriptions and block users whose access has ended."""
    now = datetime.utcnow()
    stmt = select(User).where(
        and_(
            User.subscription_status == SubscriptionStatus.ACTIVE,
            User.subscription_expiry <= now,
        )
    )
    count = 0
    for user in session.scalars(stmt).all():
        user.subscription_status = SubscriptionStatus.EXPIRED
        count += 1
    return count


def payment_history(session: Session, user_id: int) -> Sequence[Payment]:
    return session.scalars(
        select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
    ).all()


# --------------------------------------------------------------------------- #
# Teams
# --------------------------------------------------------------------------- #
def get_or_create_team(session: Session, name: str, league: str) -> Team:
    team = session.scalar(
        select(Team).where(and_(Team.name == name, Team.league == league))
    )
    if team is None:
        team = Team(name=name, league=league)
        session.add(team)
        session.flush()
    return team


# --------------------------------------------------------------------------- #
# Matches & analyses
# --------------------------------------------------------------------------- #
def matches_for_day(session: Session, day: datetime) -> Sequence[Match]:
    start = datetime(day.year, day.month, day.day)
    end = start + timedelta(days=1)
    stmt = (
        select(Match)
        .where(and_(Match.kickoff >= start, Match.kickoff < end))
        .order_by(Match.kickoff.asc())
    )
    return session.scalars(stmt).all()


def matches_between(
    session: Session, start: datetime, end: datetime, only_scheduled: bool = True
) -> Sequence[Match]:
    conditions = [Match.kickoff >= start, Match.kickoff < end]
    if only_scheduled:
        conditions.append(Match.status == MatchStatus.SCHEDULED)
    stmt = select(Match).where(and_(*conditions)).order_by(Match.kickoff.asc())
    return session.scalars(stmt).all()


def upcoming_matches(session: Session, horizon_days: int = 5) -> Sequence[Match]:
    now = datetime.utcnow()
    end = now + timedelta(days=horizon_days)
    return matches_between(session, now, end, only_scheduled=True)


def get_match(session: Session, match_id: int) -> Optional[Match]:
    return session.get(Match, match_id)


def find_match_by_external(
    session: Session, external_id: str, provider: str
) -> Optional[Match]:
    return session.scalar(
        select(Match).where(
            and_(Match.external_id == external_id, Match.provider == provider)
        )
    )


def upsert_analysis(session: Session, match_id: int, **fields) -> Analysis:
    analysis = session.scalar(select(Analysis).where(Analysis.match_id == match_id))
    if analysis is None:
        analysis = Analysis(match_id=match_id, **fields)
        session.add(analysis)
    else:
        for key, value in fields.items():
            setattr(analysis, key, value)
    session.flush()
    return analysis


# --------------------------------------------------------------------------- #
# Tips & combos (statistics)
# --------------------------------------------------------------------------- #
def record_tip(
    session: Session,
    match: Match,
    analysis: Analysis,
    pick: str,
    odds: float,
    profile: str,
    confidence: float,
    user_id: Optional[int] = None,
    is_broadcast: bool = False,
) -> Tip:
    tip = Tip(
        user_id=user_id,
        match_id=match.id,
        analysis_id=analysis.id if analysis else None,
        pick=pick,
        odds=odds,
        profile=profile,
        confidence=confidence,
        is_broadcast=is_broadcast,
    )
    session.add(tip)
    session.flush()
    return tip


def settle_tips_for_match(session: Session, match: Match) -> int:
    """Settle all pending tips/selections that reference a finished match."""
    if match.status != MatchStatus.FINISHED or match.home_score is None:
        return 0

    if match.home_score > match.away_score:
        winning_pick = "1"
    elif match.home_score < match.away_score:
        winning_pick = "2"
    else:
        winning_pick = "X"

    settled = 0
    now = datetime.utcnow()

    tips = session.scalars(
        select(Tip).where(and_(Tip.match_id == match.id, Tip.status == TipStatus.PENDING))
    ).all()
    for tip in tips:
        tip.status = TipStatus.WON if tip.pick == winning_pick else TipStatus.LOST
        tip.settled_at = now
        settled += 1

    selections = session.scalars(
        select(ComboSelection).where(
            and_(
                ComboSelection.match_id == match.id,
                ComboSelection.status == TipStatus.PENDING,
            )
        )
    ).all()
    for sel in selections:
        sel.status = TipStatus.WON if sel.pick == winning_pick else TipStatus.LOST

    return settled


def settle_combos(session: Session) -> int:
    """Resolve combos whose selections are all settled."""
    pending = session.scalars(
        select(Combo).where(Combo.status == TipStatus.PENDING)
    ).all()
    settled = 0
    now = datetime.utcnow()
    for combo in pending:
        statuses = [s.status for s in combo.selections]
        if not statuses or TipStatus.PENDING in statuses:
            continue
        if all(s == TipStatus.WON for s in statuses):
            combo.status = TipStatus.WON
        else:
            combo.status = TipStatus.LOST
        combo.settled_at = now
        settled += 1
    return settled


def tip_stats(session: Session, profile: Optional[str] = None) -> dict:
    """Aggregate win/loss statistics for broadcast tips."""
    conditions = [Tip.is_broadcast.is_(True)]
    if profile:
        conditions.append(Tip.profile == profile)

    base = select(func.count(Tip.id)).where(and_(*conditions))
    total = session.scalar(base) or 0
    won = session.scalar(base.where(Tip.status == TipStatus.WON)) or 0
    lost = session.scalar(base.where(Tip.status == TipStatus.LOST)) or 0
    pending = session.scalar(base.where(Tip.status == TipStatus.PENDING)) or 0
    settled = won + lost
    win_rate = (won / settled * 100) if settled else 0.0

    # Simple ROI assuming 1 unit stake per tip.
    won_tips = session.scalars(
        select(Tip).where(and_(*conditions, Tip.status == TipStatus.WON))
    ).all()
    returns = sum(t.odds for t in won_tips)
    roi = ((returns - settled) / settled * 100) if settled else 0.0

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "settled": settled,
        "win_rate": round(win_rate, 1),
        "roi": round(roi, 1),
    }


# --------------------------------------------------------------------------- #
# Combo drafts (user in-progress selections)
# --------------------------------------------------------------------------- #
def get_draft(session: Session, user_id: int) -> List[UserComboDraft]:
    return list(
        session.scalars(
            select(UserComboDraft)
            .where(UserComboDraft.user_id == user_id)
            .order_by(UserComboDraft.created_at.asc())
        ).all()
    )


def add_draft_selection(
    session: Session, user_id: int, match_id: int, pick: str, odds: float
) -> bool:
    existing = session.scalar(
        select(UserComboDraft).where(
            and_(
                UserComboDraft.user_id == user_id,
                UserComboDraft.match_id == match_id,
            )
        )
    )
    if existing:
        existing.pick = pick
        existing.odds = odds
        return False
    session.add(
        UserComboDraft(user_id=user_id, match_id=match_id, pick=pick, odds=odds)
    )
    return True


def clear_draft(session: Session, user_id: int) -> None:
    for row in get_draft(session, user_id):
        session.delete(row)
