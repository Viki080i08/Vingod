"""Economic calendar of important macro events.

Pulls upcoming high-impact events from a public source when reachable and
falls back to a curated set of recurring macro events so the feature keeps
working offline / without any API key.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from ..models import EconomicEvent

logger = logging.getLogger(__name__)

# A public JSON mirror of this-week's economic calendar (nfs.faireconomy.media
# is maintained by ForexFactory community tooling and needs no API key).
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


class EconomicCalendarProvider:
    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    async def get_events(self, importance: str = "high", limit: int = 15) -> List[EconomicEvent]:
        try:
            return await self._from_remote(importance, limit)
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Economic calendar remote fetch failed: %s", exc)
            return self._fallback(importance, limit)

    async def _from_remote(self, importance: str, limit: int) -> List[EconomicEvent]:
        async with httpx.AsyncClient(timeout=self._timeout, headers={"User-Agent": "trading-ai-bot/1.0"}) as client:
            resp = await client.get(CALENDAR_URL)
            resp.raise_for_status()
            data = resp.json()

        wanted = {"high": {"high"}, "medium": {"high", "medium"}, "low": {"high", "medium", "low"}}[importance]
        events: List[EconomicEvent] = []
        for row in data:
            impact = str(row.get("impact", "")).lower()
            if impact not in wanted:
                continue
            when = None
            if row.get("date"):
                try:
                    when = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
                except ValueError:
                    when = None
            events.append(
                EconomicEvent(
                    title=row.get("title", "Economic event"),
                    country=row.get("country", ""),
                    importance=impact or "medium",
                    when=when,
                    actual=row.get("actual") or None,
                    forecast=row.get("forecast") or None,
                    previous=row.get("previous") or None,
                )
            )
        now = datetime.now(timezone.utc)
        events = [e for e in events if e.when is None or e.when >= now - timedelta(hours=6)]
        events.sort(key=lambda e: e.when or now)
        return events[:limit]

    @staticmethod
    def _fallback(importance: str, limit: int) -> List[EconomicEvent]:
        base = datetime.now(timezone.utc)
        curated = [
            EconomicEvent("US CPI (Inflation)", "USD", "high", base + timedelta(days=2)),
            EconomicEvent("FOMC Interest Rate Decision", "USD", "high", base + timedelta(days=5)),
            EconomicEvent("US Non-Farm Payrolls", "USD", "high", base + timedelta(days=7)),
            EconomicEvent("ECB Interest Rate Decision", "EUR", "high", base + timedelta(days=9)),
            EconomicEvent("US GDP (QoQ)", "USD", "high", base + timedelta(days=12)),
            EconomicEvent("US Unemployment Rate", "USD", "medium", base + timedelta(days=7)),
        ]
        wanted = {"high": {"high"}, "medium": {"high", "medium"}, "low": {"high", "medium", "low"}}[importance]
        return [e for e in curated if e.importance in wanted][:limit]


economic_calendar_provider = EconomicCalendarProvider()
