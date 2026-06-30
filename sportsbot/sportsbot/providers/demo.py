"""Built-in demo provider.

Generates realistic-looking football fixtures for today + the next few days
using a deterministic, seeded random generator. It requires no API key and
works completely offline, so the whole product is testable end-to-end out of
the box. Team strengths are derived deterministically from the team name so
that ratings stay stable across runs, while fixtures and results are seeded by
the match date and identifier.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, time, timedelta
from typing import Dict, List

from .base import MatchResult, ProviderMatch, ProviderTeam

PROVIDER_NAME = "demo"

# A handful of leagues with real-world team names for a believable experience.
LEAGUES: Dict[str, List[str]] = {
    "Ligue 1": [
        "Paris SG", "Marseille", "Lyon", "Monaco", "Lille", "Rennes",
        "Nice", "Lens", "Reims", "Strasbourg", "Nantes", "Montpellier",
    ],
    "Premier League": [
        "Manchester City", "Arsenal", "Liverpool", "Manchester Utd",
        "Chelsea", "Tottenham", "Newcastle", "Aston Villa",
        "Brighton", "West Ham", "Everton", "Wolves",
    ],
    "La Liga": [
        "Real Madrid", "Barcelone", "Atletico Madrid", "Real Sociedad",
        "Villarreal", "Betis", "Athletic Bilbao", "Valence",
        "Séville", "Getafe", "Osasuna", "Celta Vigo",
    ],
    "Serie A": [
        "Inter Milan", "Juventus", "AC Milan", "Naples", "Roma",
        "Lazio", "Atalanta", "Fiorentina", "Bologne", "Torino",
    ],
    "Bundesliga": [
        "Bayern Munich", "Dortmund", "Leipzig", "Leverkusen",
        "Francfort", "Fribourg", "Wolfsburg", "Stuttgart",
    ],
}


def _hash_seed(*parts) -> int:
    raw = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2**32)


def _team_profile(name: str, league: str) -> ProviderTeam:
    """Deterministic, stable rating for a team based on its name."""
    rng = random.Random(_hash_seed("team", name, league))

    # Base quality 0..1; top teams (listed first) skew higher via index hint.
    quality = rng.uniform(0.35, 0.95)
    attack = round(0.75 + quality * 0.9 + rng.uniform(-0.08, 0.08), 3)
    defense = round(0.75 + quality * 0.9 + rng.uniform(-0.08, 0.08), 3)
    goals_for = round(0.9 + quality * 1.4, 2)
    goals_against = round(2.1 - quality * 1.3, 2)

    # Form string for the last 5 games biased by quality.
    form_chars = []
    for _ in range(5):
        roll = rng.random()
        if roll < 0.25 + quality * 0.4:
            form_chars.append("W")
        elif roll < 0.55 + quality * 0.3:
            form_chars.append("D")
        else:
            form_chars.append("L")
    form = "".join(form_chars)

    momentum = round(rng.uniform(-0.6, 0.6) + (quality - 0.5) * 0.6, 2)
    return ProviderTeam(
        name=name,
        league=league,
        attack_rating=attack,
        defense_rating=defense,
        goals_for_avg=goals_for,
        goals_against_avg=goals_against,
        recent_form=form,
        home_strength=round(rng.uniform(1.02, 1.28), 3),
        away_strength=round(rng.uniform(0.78, 1.02), 3),
        key_absences=rng.choices([0, 1, 2, 3], weights=[55, 28, 12, 5])[0],
        momentum=max(-1.0, min(1.0, momentum)),
    )


def _head_to_head(home: str, away: str) -> dict:
    rng = random.Random(_hash_seed("h2h", *sorted([home, away])))
    hw = rng.randint(0, 5)
    aw = rng.randint(0, 5)
    dr = rng.randint(0, 4)
    return {"home_wins": hw, "draws": dr, "away_wins": aw}


class DemoProvider:
    name = PROVIDER_NAME

    def fetch_fixtures(self, horizon_days: int) -> List[ProviderMatch]:
        matches: List[ProviderMatch] = []
        today = datetime.utcnow().date()

        for day_offset in range(horizon_days):
            day = today + timedelta(days=day_offset)
            day_seed = _hash_seed("day", day.isoformat())
            rng = random.Random(day_seed)

            for league, teams in LEAGUES.items():
                pool = teams[:]
                rng.shuffle(pool)
                # 2-3 fixtures per league per day.
                n_fixtures = rng.randint(2, 3)
                for i in range(n_fixtures):
                    if len(pool) < 2:
                        break
                    home_name = pool.pop()
                    away_name = pool.pop()

                    # Kickoff times spread across the afternoon/evening (UTC).
                    hour = rng.choice([12, 14, 16, 18, 19, 20])
                    minute = rng.choice([0, 15, 30, 45])
                    kickoff = datetime.combine(day, time(hour, minute))

                    ext_id = f"{day.isoformat()}-{league}-{home_name}-{away_name}".replace(" ", "_")
                    matches.append(
                        ProviderMatch(
                            external_id=ext_id,
                            provider=self.name,
                            league=league,
                            sport="football",
                            home=_team_profile(home_name, league),
                            away=_team_profile(away_name, league),
                            kickoff=kickoff,
                            head_to_head=_head_to_head(home_name, away_name),
                            status="scheduled",
                        )
                    )
        return matches

    def fetch_results(self, external_ids: List[str]) -> List[MatchResult]:
        """Simulate results for matches whose kickoff is in the past."""
        results: List[MatchResult] = []
        now = datetime.utcnow()
        for ext_id in external_ids:
            # external id starts with YYYY-MM-DD
            try:
                date_part = ext_id.split("-", 3)
                match_date = datetime.fromisoformat(
                    f"{date_part[0]}-{date_part[1]}-{date_part[2]}"
                )
            except (ValueError, IndexError):
                continue
            # Only "play out" matches from a day that has already passed.
            if match_date.date() >= now.date():
                continue
            rng = random.Random(_hash_seed("result", ext_id))
            home_goals = rng.choices([0, 1, 2, 3, 4], weights=[18, 32, 27, 15, 8])[0]
            away_goals = rng.choices([0, 1, 2, 3, 4], weights=[24, 33, 24, 12, 7])[0]
            results.append(
                MatchResult(
                    external_id=ext_id,
                    home_score=home_goals,
                    away_score=away_goals,
                    status="finished",
                )
            )
        return results
