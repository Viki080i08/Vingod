"""API-Football (api-sports.io) provider — complete real worldwide fixtures.

This is the recommended real-data source. The free plan (100 requests/day,
https://www.api-football.com/) covers EVERY competition: all domestic leagues,
the World Cup, international friendlies, cups, etc., via a single
``/fixtures?date=YYYY-MM-DD`` call per day.

Set the key via ``APIFOOTBALL_API_KEY``. On any error the sync layer falls back
to another source so the bot keeps working.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import httpx

from ..logging_conf import get_logger
from . import ratings
from .base import MatchResult, ProviderMatch, ProviderTeam

logger = get_logger(__name__)

PROVIDER_NAME = "apifootball"
BASE_URL = "https://v3.football.api-sports.io"
FINISHED_STATUSES = {"FT", "AET", "PEN"}


def _team_profile(name: str, league: str) -> ProviderTeam:
    elo = ratings.elo_for(name)
    quality = max(0.0, min(1.0, (elo - 1500.0) / 550.0))
    return ProviderTeam(
        name=name,
        league=league,
        attack_rating=round(0.92 + quality * 0.45, 3),
        defense_rating=round(0.92 + quality * 0.45, 3),
        goals_for_avg=round(1.15 + quality * 0.7, 2),
        goals_against_avg=round(1.55 - quality * 0.55, 2),
        recent_form="",
        home_strength=1.1,
        away_strength=0.92,
        key_absences=0,
        momentum=0.0,
        elo=elo,
    )


class APIFootballProvider:
    name = PROVIDER_NAME

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=BASE_URL,
            headers={"x-apisports-key": self.api_key},
            timeout=25.0,
        )

    def _parse_item(self, item: dict) -> ProviderMatch | None:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        goals = item.get("goals") or {}

        home_name = (teams.get("home") or {}).get("name")
        away_name = (teams.get("away") or {}).get("name")
        if not home_name or not away_name:
            return None

        date_str = fixture.get("date")
        try:
            kickoff = datetime.fromisoformat(date_str).astimezone(tz=None).replace(tzinfo=None)
        except (ValueError, TypeError):
            try:
                kickoff = datetime.fromisoformat((date_str or "").replace("Z", "")).replace(tzinfo=None)
            except (ValueError, TypeError):
                return None

        league_name = league.get("name") or "Football"
        country = league.get("country")
        if country and country.lower() not in league_name.lower():
            league_name = f"{league_name} ({country})"

        status = ((fixture.get("status") or {}).get("short") or "NS")
        finished = status in FINISHED_STATUSES
        hg, ag = goals.get("home"), goals.get("away")

        return ProviderMatch(
            external_id=str(fixture.get("id")),
            provider=self.name,
            league=league_name,
            sport="football",
            home=_team_profile(home_name, league_name),
            away=_team_profile(away_name, league_name),
            kickoff=kickoff,
            head_to_head=None,
            status="finished" if finished else "scheduled",
            home_score=int(hg) if finished and hg is not None else None,
            away_score=int(ag) if finished and ag is not None else None,
        )

    def fetch_fixtures(self, horizon_days: int) -> List[ProviderMatch]:
        matches: List[ProviderMatch] = []
        today = datetime.utcnow().date()
        with self._client() as client:
            for offset in range(horizon_days):
                day = today + timedelta(days=offset)
                resp = client.get(
                    "/fixtures", params={"date": day.isoformat(), "timezone": "UTC"}
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("errors"):
                    logger.warning("API-Football errors: %s", payload["errors"])
                for item in payload.get("response", []):
                    m = self._parse_item(item)
                    if m:
                        matches.append(m)
        logger.info("API-Football: %s matchs réels récupérés.", len(matches))
        return matches

    def fetch_results(self, external_ids: List[str]) -> List[MatchResult]:
        results: List[MatchResult] = []
        with self._client() as client:
            # API-Football accepts up to 20 ids per call (dash-separated).
            for i in range(0, len(external_ids), 20):
                batch = external_ids[i : i + 20]
                try:
                    resp = client.get("/fixtures", params={"ids": "-".join(batch)})
                    resp.raise_for_status()
                    for item in resp.json().get("response", []):
                        fixture = item.get("fixture") or {}
                        goals = item.get("goals") or {}
                        status = ((fixture.get("status") or {}).get("short") or "")
                        if status not in FINISHED_STATUSES:
                            continue
                        hg, ag = goals.get("home"), goals.get("away")
                        if hg is None or ag is None:
                            continue
                        results.append(
                            MatchResult(
                                external_id=str(fixture.get("id")),
                                home_score=int(hg),
                                away_score=int(ag),
                            )
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("API-Football results batch failed: %s", exc)
                    continue
        return results
