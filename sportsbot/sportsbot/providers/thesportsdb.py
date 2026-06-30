"""TheSportsDB provider — real worldwide fixtures (free, no registration).

Covers virtually every competition: domestic leagues, the World Cup,
international friendlies, cups, etc. Uses the free API key (configurable via
THESPORTSDB_API_KEY, default the public test key "3").

For each upcoming match it builds a team profile from the curated Elo table
(falling back to 1500 for unknown teams). The engine then learns each team's
real strength automatically as results come in. On any network/parse error the
sync layer falls back to the internal engine, so the bot never breaks.
"""

from __future__ import annotations

import time as _time
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from ..logging_conf import get_logger
from . import ratings
from .base import MatchResult, ProviderMatch, ProviderTeam

logger = get_logger(__name__)

PROVIDER_NAME = "thesportsdb"
BASE_URL = "https://www.thesportsdb.com/api/v1/json"
MAX_RESULT_LOOKUPS = 80  # cap per run to stay within free-tier rate limits


def _parse_kickoff(ev: dict) -> Optional[datetime]:
    ts = ev.get("strTimestamp")
    if ts:
        try:
            return datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=None)
        except ValueError:
            pass
    date_str = ev.get("dateEvent")
    time_str = ev.get("strTime") or "00:00:00"
    if date_str:
        try:
            return datetime.fromisoformat(f"{date_str}T{time_str[:8]}")
        except ValueError:
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                return None
    return None


def _team_profile(name: str, league: str) -> ProviderTeam:
    elo = ratings.elo_for(name)
    quality = max(0.0, min(1.0, (elo - 1500.0) / 550.0))
    # Without per-team stats we lean on Elo + home advantage; attack/defense
    # start near league-average and the engine learns from results over time.
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


class TheSportsDBProvider:
    name = PROVIDER_NAME

    def __init__(self, api_key: str = "3"):
        self.api_key = api_key or "3"

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=f"{BASE_URL}/{self.api_key}", timeout=20.0)

    def fetch_fixtures(self, horizon_days: int) -> List[ProviderMatch]:
        matches: List[ProviderMatch] = []
        today = datetime.utcnow().date()
        now = datetime.utcnow()

        with self._client() as client:
            for offset in range(horizon_days):
                day = today + timedelta(days=offset)
                try:
                    resp = client.get(
                        "/eventsday.php", params={"d": day.isoformat(), "s": "Soccer"}
                    )
                    resp.raise_for_status()
                    events = resp.json().get("events") or []
                except Exception as exc:  # noqa: BLE001
                    logger.warning("TheSportsDB eventsday %s failed: %s", day, exc)
                    continue

                for ev in events:
                    home_name = (ev.get("strHomeTeam") or "").strip()
                    away_name = (ev.get("strAwayTeam") or "").strip()
                    if not home_name or not away_name:
                        continue
                    kickoff = _parse_kickoff(ev)
                    if kickoff is None:
                        continue

                    league = ev.get("strLeague") or "Football"
                    hs = ev.get("intHomeScore")
                    as_ = ev.get("intAwayScore")
                    has_score = hs not in (None, "") and as_ not in (None, "")
                    finished = has_score and kickoff < now
                    status = "finished" if finished else "scheduled"

                    matches.append(
                        ProviderMatch(
                            external_id=str(ev.get("idEvent")),
                            provider=self.name,
                            league=league,
                            sport="football",
                            home=_team_profile(home_name, league),
                            away=_team_profile(away_name, league),
                            kickoff=kickoff,
                            head_to_head=None,
                            status=status,
                            home_score=int(hs) if finished else None,
                            away_score=int(as_) if finished else None,
                        )
                    )

        logger.info("TheSportsDB: %s matchs réels récupérés.", len(matches))
        return matches

    def fetch_results(self, external_ids: List[str]) -> List[MatchResult]:
        results: List[MatchResult] = []
        with self._client() as client:
            for ext_id in external_ids[:MAX_RESULT_LOOKUPS]:
                try:
                    resp = client.get("/lookupevent.php", params={"id": ext_id})
                    resp.raise_for_status()
                    data = resp.json().get("events") or []
                    if not data:
                        continue
                    ev = data[0]
                    hs = ev.get("intHomeScore")
                    as_ = ev.get("intAwayScore")
                    if hs in (None, "") or as_ in (None, ""):
                        continue
                    results.append(
                        MatchResult(
                            external_id=str(ext_id),
                            home_score=int(hs),
                            away_score=int(as_),
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("TheSportsDB lookupevent %s failed: %s", ext_id, exc)
                    continue
                _time.sleep(0.25)  # be gentle with the free tier
        return results
