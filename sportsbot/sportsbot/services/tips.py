"""Selection of daily opportunities, broadcast tips and AI combos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..ai.engine import AnalysisResult, pick_for_profile
from ..ai.profiles import tuning_for
from ..config import get_settings
from ..db.base import MatchStatus, RiskProfile, TipStatus
from ..db.models import Analysis, Combo, ComboSelection, Match
from ..db import repo
from ..logging_conf import get_logger

logger = get_logger(__name__)


@dataclass
class Opportunity:
    match: Match
    analysis: Analysis
    pick: str
    odds: float
    probability: float
    value: float
    confidence: float
    rationale: str
    fallback: bool = False


def _analysis_to_result(a: Analysis) -> AnalysisResult:
    return AnalysisResult(
        prob_home=a.prob_home,
        prob_draw=a.prob_draw,
        prob_away=a.prob_away,
        expected_home_goals=a.expected_home_goals,
        expected_away_goals=a.expected_away_goals,
        odds_home=a.odds_home,
        odds_draw=a.odds_draw,
        odds_away=a.odds_away,
        recommended_pick=a.recommended_pick,
        recommended_odds=a.recommended_odds,
        confidence=a.confidence,
        risk_level=a.risk_level,
        value_score=a.value_score,
        explanation=a.explanation,
        key_factors=a.key_factors or {},
    )


def _scheduled_analysed_matches(
    session: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> List[Match]:
    settings = get_settings()
    now = datetime.utcnow()
    start = start or now
    end = end or (now + timedelta(days=settings.forecast_horizon_days))
    stmt = (
        select(Match)
        .join(Analysis, Analysis.match_id == Match.id)
        .where(
            and_(
                Match.kickoff >= start,
                Match.kickoff < end,
                Match.status == MatchStatus.SCHEDULED,
            )
        )
        .order_by(Match.kickoff.asc())
    )
    return list(session.scalars(stmt).all())


def best_opportunities(
    session: Session,
    profile: str,
    limit: int = 5,
    day: Optional[datetime] = None,
) -> List[Opportunity]:
    """Rank the best matches for a profile across the forecast horizon."""
    if day is not None:
        start = datetime(day.year, day.month, day.day)
        end = start + timedelta(days=1)
        matches = _scheduled_analysed_matches(session, start, end)
    else:
        matches = _scheduled_analysed_matches(session)

    opportunities: List[Opportunity] = []
    for match in matches:
        analysis = match.analysis
        if analysis is None:
            continue
        result = _analysis_to_result(analysis)
        choice = pick_for_profile(result, profile)
        if choice is None:
            continue
        opportunities.append(
            Opportunity(
                match=match,
                analysis=analysis,
                pick=choice["pick"],
                odds=choice["odds"],
                probability=choice["probability"],
                value=choice["value"],
                confidence=analysis.confidence,
                rationale=choice["rationale"],
                fallback=choice.get("fallback", False),
            )
        )

    # Ranking: profile-aware blend of value and confidence.
    tuning = tuning_for(profile)
    vw = tuning["value_weight"]
    opportunities.sort(
        key=lambda o: vw * o.value + (1 - vw) * (o.probability) + o.confidence / 200,
        reverse=True,
    )
    return opportunities[:limit]


def generate_broadcast_tips(session: Session, limit_per_profile: int = 3) -> dict:
    """Create today's broadcast tips for every risk profile."""
    today = datetime.utcnow()
    summary = {}
    for profile in RiskProfile.ALL:
        opportunities = best_opportunities(session, profile, limit=limit_per_profile, day=today)
        created = []
        for opp in opportunities:
            tip = repo.record_tip(
                session,
                match=opp.match,
                analysis=opp.analysis,
                pick=opp.pick,
                odds=opp.odds,
                profile=profile,
                confidence=opp.confidence,
                user_id=None,
                is_broadcast=True,
            )
            created.append(tip)
        summary[profile] = opportunities
    return summary


def build_ai_combo(
    session: Session,
    profile: str,
    user_id: Optional[int] = None,
    persist: bool = True,
) -> Optional[Combo]:
    """Build an optimised combo (accumulator) tuned to the profile."""
    tuning = tuning_for(profile)
    size = tuning["combo_size"]
    opportunities = best_opportunities(session, profile, limit=size * 3)

    # Pick distinct matches with the best blend; cap legs at profile size.
    chosen: List[Opportunity] = []
    seen_matches = set()
    for opp in opportunities:
        if opp.match.id in seen_matches:
            continue
        chosen.append(opp)
        seen_matches.add(opp.match.id)
        if len(chosen) >= size:
            break

    if len(chosen) < 2:
        return None

    total_odds = 1.0
    combined_prob = 1.0
    for opp in chosen:
        total_odds *= opp.odds
        combined_prob *= opp.probability

    combo = Combo(
        user_id=user_id,
        profile=profile,
        total_odds=round(total_odds, 2),
        combined_probability=round(combined_prob, 4),
        ai_generated=True,
        status=TipStatus.PENDING,
    )
    for opp in chosen:
        combo.selections.append(
            ComboSelection(
                match_id=opp.match.id,
                pick=opp.pick,
                odds=opp.odds,
                status=TipStatus.PENDING,
            )
        )

    if persist:
        session.add(combo)
        session.flush()
    return combo
