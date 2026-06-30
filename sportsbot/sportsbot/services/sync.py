"""Synchronisation service.

Pulls fixtures from the active provider, persists teams/matches, runs the AI
analysis for every upcoming match, and later reconciles results to keep the
statistics engine learning from past outcomes.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import select

from ..ai.engine import analyse_match, update_elo
from ..config import get_settings
from ..db import session_scope
from ..db.base import MatchStatus
from ..db.models import Match, Team
from ..db import repo
from ..logging_conf import get_logger
from ..providers import get_provider
from ..providers.base import ProviderTeam
from ..providers.demo import DemoProvider
from ..providers.factory import provider_by_name

logger = get_logger(__name__)


def _apply_team_stats(team: Team, data: ProviderTeam) -> None:
    team.league = data.league or team.league
    team.attack_rating = data.attack_rating
    team.defense_rating = data.defense_rating
    team.goals_for_avg = data.goals_for_avg
    team.goals_against_avg = data.goals_against_avg
    team.recent_form = data.recent_form or team.recent_form
    team.home_strength = data.home_strength
    team.away_strength = data.away_strength
    team.key_absences = data.key_absences
    team.momentum = data.momentum
    # Seed Elo from the provider only the first time; afterwards it is learned
    # continuously from real results and must not be overwritten.
    if not team.elo or team.elo == 1500.0:
        team.elo = data.elo or 1500.0


def sync_fixtures_and_analyse() -> dict:
    """Fetch fixtures for the configured horizon, persist and analyse them."""
    settings = get_settings()
    provider = get_provider()

    try:
        fixtures = provider.fetch_fixtures(settings.forecast_horizon_days)
    except Exception as exc:  # noqa: BLE001
        logger.error("Provider fetch failed (%s).", exc)
        fixtures = []

    # If the real source returned nothing (quiet day / outage), fall back to the
    # internal engine so the bot always has matches to show.
    if not fixtures and not isinstance(provider, DemoProvider):
        logger.warning("Aucun match réel récupéré ; repli sur le moteur interne.")
        try:
            fixtures = DemoProvider().fetch_fixtures(settings.forecast_horizon_days)
        except Exception as exc:  # noqa: BLE001
            logger.error("Internal engine fallback failed: %s", exc)
            return {"fixtures": 0, "analysed": 0, "error": str(exc)}

    created, updated, analysed = 0, 0, 0

    with session_scope() as session:
        for fx in fixtures:
            home_team = repo.get_or_create_team(session, fx.home.name, fx.home.league)
            away_team = repo.get_or_create_team(session, fx.away.name, fx.away.league)
            _apply_team_stats(home_team, fx.home)
            _apply_team_stats(away_team, fx.away)

            match = repo.find_match_by_external(session, fx.external_id, fx.provider)
            if match is None:
                match = Match(
                    external_id=fx.external_id,
                    provider=fx.provider,
                    sport=fx.sport,
                    league=fx.league,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_name=home_team.name,
                    away_name=away_team.name,
                    kickoff=fx.kickoff,
                    status=fx.status,
                    head_to_head=fx.head_to_head,
                )
                session.add(match)
                session.flush()
                created += 1
            else:
                match.league = fx.league
                match.kickoff = fx.kickoff
                match.head_to_head = fx.head_to_head or match.head_to_head
                if fx.status:
                    match.status = fx.status
                updated += 1

            # Run / refresh analysis for matches not yet finished.
            if match.status != MatchStatus.FINISHED:
                result = analyse_match(home_team, away_team, match.head_to_head)
                repo.upsert_analysis(
                    session,
                    match.id,
                    prob_home=result.prob_home,
                    prob_draw=result.prob_draw,
                    prob_away=result.prob_away,
                    expected_home_goals=result.expected_home_goals,
                    expected_away_goals=result.expected_away_goals,
                    recommended_pick=result.recommended_pick,
                    recommended_odds=result.recommended_odds,
                    confidence=result.confidence,
                    risk_level=result.risk_level,
                    value_score=result.value_score,
                    odds_home=result.odds_home,
                    odds_draw=result.odds_draw,
                    odds_away=result.odds_away,
                    explanation=result.explanation,
                    key_factors=result.key_factors,
                )
                analysed += 1

    logger.info(
        "Sync done: %s created, %s updated, %s analysed (%s fixtures).",
        created, updated, analysed, len(fixtures),
    )
    return {"fixtures": len(fixtures), "created": created, "updated": updated, "analysed": analysed}


def _update_form(team: Team, scored: int, conceded: int) -> None:
    """Roll the recent form string and the goal moving averages."""
    if scored > conceded:
        outcome = "W"
    elif scored < conceded:
        outcome = "L"
    else:
        outcome = "D"
    team.recent_form = (outcome + (team.recent_form or ""))[:6]

    alpha = 0.3  # exponential moving average weight
    team.goals_for_avg = round((1 - alpha) * (team.goals_for_avg or 1.3) + alpha * scored, 2)
    team.goals_against_avg = round(
        (1 - alpha) * (team.goals_against_avg or 1.3) + alpha * conceded, 2
    )
    # Momentum nudged by latest result.
    delta = 0.2 if outcome == "W" else (-0.2 if outcome == "L" else 0.0)
    team.momentum = round(max(-1.0, min(1.0, (team.momentum or 0.0) * 0.8 + delta)), 2)


def update_results_and_settle() -> dict:
    """Fetch results for past matches, settle tips/combos and learn from them."""
    from collections import defaultdict

    now = datetime.utcnow()

    with session_scope() as session:
        pending_stmt = select(Match).where(
            Match.status != MatchStatus.FINISHED,
            Match.kickoff < now,
        )
        pending = list(session.scalars(pending_stmt).all())
        if not pending:
            return {"checked": 0, "settled": 0}

        # Fetch results from each match's originating provider.
        groups: dict[str, list[str]] = defaultdict(list)
        for m in pending:
            groups[m.provider].append(m.external_id)

        results_by_id = {}
        for pname, ext_ids in groups.items():
            try:
                for r in provider_by_name(pname).fetch_results(ext_ids):
                    results_by_id[r.external_id] = r
            except Exception as exc:  # noqa: BLE001
                logger.error("Result fetch failed for provider %s: %s", pname, exc)
        settled_matches = 0

        for match in pending:
            res = results_by_id.get(match.external_id)
            if res is None:
                continue
            match.status = MatchStatus.FINISHED
            match.home_score = res.home_score
            match.away_score = res.away_score

            home_team = session.get(Team, match.home_team_id)
            away_team = session.get(Team, match.away_team_id)
            if home_team and away_team:
                # Continuous learning: update Elo ratings from the real result.
                new_home_elo, new_away_elo = update_elo(
                    home_team.elo or 1500.0,
                    away_team.elo or 1500.0,
                    res.home_score,
                    res.away_score,
                )
                home_team.elo = round(new_home_elo, 1)
                away_team.elo = round(new_away_elo, 1)
            if home_team:
                _update_form(home_team, res.home_score, res.away_score)
            if away_team:
                _update_form(away_team, res.away_score, res.home_score)

            repo.settle_tips_for_match(session, match)
            settled_matches += 1

        repo.settle_combos(session)

    logger.info("Results update: %s matches settled.", settled_matches)
    return {"checked": len(pending), "settled": settled_matches}
