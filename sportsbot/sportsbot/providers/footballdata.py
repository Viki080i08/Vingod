"""football-data.org (v4) provider.

Uses the free tier of https://www.football-data.org/ . Requires an API key set
via ``FOOTBALL_DATA_API_KEY``. The free plan covers the major competitions and
is rate-limited (10 requests/minute), so calls are kept minimal and wrapped in
defensive error handling — on any failure the sync layer falls back to the
demo provider so the product keeps working.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

import httpx

from ..logging_conf import get_logger
from .base import MatchResult, ProviderMatch, ProviderTeam

logger = get_logger(__name__)

BASE_URL = "https://api.football-data.org/v4"
PROVIDER_NAME = "footballdata"


class FootballDataProvider:
    name = PROVIDER_NAME

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._standings_cache: Dict[str, dict] = {}

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=BASE_URL,
            headers={"X-Auth-Token": self.api_key},
            timeout=20.0,
        )

    # ------------------------------------------------------------------ #
    def _team_from_standing(self, name: str, league: str, stats: dict | None) -> ProviderTeam:
        if not stats:
            return ProviderTeam(name=name, league=league)
        played = max(stats.get("playedGames", 0), 1)
        gf = stats.get("goalsFor", played) / played
        ga = stats.get("goalsAgainst", played) / played
        form = (stats.get("form") or "").replace(",", "")[:5]
        attack = round(max(0.6, gf / 1.35), 3)
        defense = round(max(0.6, 1.35 / max(ga, 0.4)), 3)
        return ProviderTeam(
            name=name,
            league=league,
            attack_rating=attack,
            defense_rating=defense,
            goals_for_avg=round(gf, 2),
            goals_against_avg=round(ga, 2),
            recent_form=form,
            home_strength=1.12,
            away_strength=0.92,
            key_absences=0,
            momentum=0.0,
        )

    def _load_standings(self, client: httpx.Client, competition_code: str) -> Dict[str, dict]:
        if competition_code in self._standings_cache:
            return self._standings_cache[competition_code]
        table: Dict[str, dict] = {}
        try:
            resp = client.get(f"/competitions/{competition_code}/standings")
            resp.raise_for_status()
            data = resp.json()
            for standing in data.get("standings", []):
                if standing.get("type") != "TOTAL":
                    continue
                for row in standing.get("table", []):
                    team = row.get("team", {})
                    table[team.get("name", "")] = row
        except Exception as exc:  # noqa: BLE001
            logger.warning("Standings fetch failed for %s: %s", competition_code, exc)
        self._standings_cache[competition_code] = table
        return table

    # ------------------------------------------------------------------ #
    def fetch_fixtures(self, horizon_days: int) -> List[ProviderMatch]:
        date_from = datetime.utcnow().date()
        date_to = date_from + timedelta(days=max(0, horizon_days - 1))
        matches: List[ProviderMatch] = []

        try:
            with self._client() as client:
                resp = client.get(
                    "/matches",
                    params={
                        "dateFrom": date_from.isoformat(),
                        "dateTo": date_to.isoformat(),
                    },
                )
                resp.raise_for_status()
                payload = resp.json()

                for m in payload.get("matches", []):
                    competition = m.get("competition", {})
                    comp_code = competition.get("code", "")
                    league = competition.get("name", "Football")
                    standings = self._load_standings(client, comp_code) if comp_code else {}

                    home = m.get("homeTeam", {})
                    away = m.get("awayTeam", {})
                    home_name = home.get("name") or home.get("shortName") or "Home"
                    away_name = away.get("name") or away.get("shortName") or "Away"

                    kickoff = datetime.fromisoformat(
                        m.get("utcDate", "").replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                    status = "finished" if m.get("status") == "FINISHED" else "scheduled"
                    score = m.get("score", {}).get("fullTime", {})

                    matches.append(
                        ProviderMatch(
                            external_id=str(m.get("id")),
                            provider=self.name,
                            league=league,
                            sport="football",
                            home=self._team_from_standing(
                                home_name, league, standings.get(home_name)
                            ),
                            away=self._team_from_standing(
                                away_name, league, standings.get(away_name)
                            ),
                            kickoff=kickoff,
                            status=status,
                            home_score=score.get("home"),
                            away_score=score.get("away"),
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error("football-data fixtures fetch failed: %s", exc)
            raise

        return matches

    def fetch_results(self, external_ids: List[str]) -> List[MatchResult]:
        results: List[MatchResult] = []
        try:
            with self._client() as client:
                for ext_id in external_ids:
                    try:
                        resp = client.get(f"/matches/{ext_id}")
                        resp.raise_for_status()
                        m = resp.json()
                        if m.get("status") != "FINISHED":
                            continue
                        score = m.get("score", {}).get("fullTime", {})
                        if score.get("home") is None:
                            continue
                        results.append(
                            MatchResult(
                                external_id=str(ext_id),
                                home_score=int(score["home"]),
                                away_score=int(score["away"]),
                            )
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Result fetch failed for %s: %s", ext_id, exc)
                        continue
        except Exception as exc:  # noqa: BLE001
            logger.error("football-data results fetch failed: %s", exc)
        return results
