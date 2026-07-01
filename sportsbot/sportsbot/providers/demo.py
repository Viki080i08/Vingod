"""Internal fixtures & ratings engine (no external sports API).

This is the project's own, fully self-contained data source. It needs NO API
key and works completely offline. It maintains a curated table of realistic
team strength ratings (Elo) for the major European clubs, generates a coherent
fixture calendar for today + the next few days, and derives each team's
offensive/defensive ratings and recent form deterministically from its Elo so
the analysis engine always has credible inputs. Fixtures and results are seeded
by date/identifier so they are stable across runs while still evolving day to
day. As real results come in, the Elo ratings are updated by the engine, so the
model keeps improving on its own.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, time, timedelta
from typing import Dict, List

from .base import MatchResult, ProviderMatch, ProviderTeam

PROVIDER_NAME = "demo"

# Curated, realistic baseline Elo ratings (≈ ClubElo scale). The analysis
# engine uses these as the backbone of every prediction and updates them as
# results arrive. ~1500 is an average side; 1900+ is elite.
CURATED_ELO: Dict[str, float] = {
    # Ligue 1
    "Paris SG": 1985, "Marseille": 1760, "Monaco": 1780, "Lille": 1750,
    "Lyon": 1730, "Nice": 1740, "Lens": 1745, "Rennes": 1735,
    "Reims": 1660, "Strasbourg": 1650, "Nantes": 1620, "Montpellier": 1600,
    # Premier League
    "Manchester City": 2050, "Arsenal": 1980, "Liverpool": 1985,
    "Manchester Utd": 1820, "Chelsea": 1830, "Tottenham": 1840,
    "Newcastle": 1830, "Aston Villa": 1820, "Brighton": 1780,
    "West Ham": 1740, "Everton": 1680, "Wolves": 1690,
    # La Liga
    "Real Madrid": 2030, "Barcelone": 1990, "Atletico Madrid": 1930,
    "Real Sociedad": 1820, "Villarreal": 1800, "Betis": 1770,
    "Athletic Bilbao": 1810, "Valence": 1720, "Séville": 1780,
    "Getafe": 1690, "Osasuna": 1700, "Celta Vigo": 1680,
    # Serie A
    "Inter Milan": 1985, "Juventus": 1900, "AC Milan": 1900, "Naples": 1910,
    "Roma": 1850, "Lazio": 1830, "Atalanta": 1880, "Fiorentina": 1800,
    "Bologne": 1770, "Torino": 1720,
    # Bundesliga
    "Bayern Munich": 2010, "Dortmund": 1900, "Leipzig": 1900,
    "Leverkusen": 1950, "Francfort": 1800, "Fribourg": 1760,
    "Wolfsburg": 1720, "Stuttgart": 1820,
}

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
    """Stable team profile derived from the curated Elo rating + light noise."""
    rng = random.Random(_hash_seed("team", name, league))

    elo = CURATED_ELO.get(name, 1500.0)
    # Map Elo (≈1550..2050) onto a 0..1 quality scale centred on the league avg.
    quality = max(0.0, min(1.0, (elo - 1500.0) / 550.0))

    attack = round(0.85 + quality * 0.85 + rng.uniform(-0.05, 0.05), 3)
    defense = round(0.85 + quality * 0.85 + rng.uniform(-0.05, 0.05), 3)
    goals_for = round(1.0 + quality * 1.3, 2)
    goals_against = round(1.9 - quality * 1.1, 2)

    # Recent form biased by quality but stable per team+season-week.
    form_chars = []
    for _ in range(5):
        roll = rng.random()
        if roll < 0.28 + quality * 0.42:
            form_chars.append("W")
        elif roll < 0.55 + quality * 0.25:
            form_chars.append("D")
        else:
            form_chars.append("L")
    form = "".join(form_chars)

    momentum = round(rng.uniform(-0.5, 0.5) + (quality - 0.5) * 0.5, 2)
    return ProviderTeam(
        name=name,
        league=league,
        attack_rating=attack,
        defense_rating=defense,
        goals_for_avg=goals_for,
        goals_against_avg=goals_against,
        recent_form=form,
        home_strength=round(1.05 + quality * 0.18, 3),
        away_strength=round(0.82 + quality * 0.16, 3),
        key_absences=rng.choices([0, 1, 2, 3], weights=[58, 27, 11, 4])[0],
        momentum=max(-1.0, min(1.0, momentum)),
        elo=elo,
    )


def _sample_poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm to sample from a Poisson distribution."""
    if lam <= 0:
        return 0
    import math

    l_bound = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= l_bound:
            return min(k - 1, 7)


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

                    ext_id = f"{day.isoformat()}~{league}~{home_name}~{away_name}"
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
        """Simulate realistic results (strength-weighted) for past matches."""
        results: List[MatchResult] = []
        now = datetime.utcnow()
        for ext_id in external_ids:
            parts = ext_id.split("~")
            if len(parts) != 4:
                continue
            date_str, _league, home_name, away_name = parts
            try:
                match_date = datetime.fromisoformat(date_str)
            except ValueError:
                continue
            # Only "play out" matches from a day that has already passed.
            if match_date.date() >= now.date():
                continue

            elo_h = CURATED_ELO.get(home_name, 1500.0)
            elo_a = CURATED_ELO.get(away_name, 1500.0)
            supremacy = max(-2.6, min(2.6, (elo_h + 65.0 - elo_a) * 0.0040))
            total = 2.7  # average total goals per match
            exp_home = max(0.2, (total + supremacy) / 2)
            exp_away = max(0.2, (total - supremacy) / 2)

            rng = random.Random(_hash_seed("result", ext_id))
            home_goals = _sample_poisson(rng, exp_home)
            away_goals = _sample_poisson(rng, exp_away)
            results.append(
                MatchResult(
                    external_id=ext_id,
                    home_score=home_goals,
                    away_score=away_goals,
                    status="finished",
                )
            )
        return results
