"""Background scanner that finds trade opportunities across the watchlist.

Used both by the /signaux and /top commands (on demand) and by the periodic
alert job that pushes high-conviction signals to subscribers.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List, Optional

from ..ai.engine import ai_engine
from ..config import settings
from ..models import TradingSignal

logger = logging.getLogger(__name__)


class SignalScanner:
    def __init__(self, cache_ttl: int = 120) -> None:
        self._cache_ttl = cache_ttl
        self._cache: List[TradingSignal] = []
        self._cache_ts: float = 0.0
        self._lock = asyncio.Lock()

    async def scan(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1h",
        use_cache: bool = True,
    ) -> List[TradingSignal]:
        symbols = symbols or settings.default_watchlist
        now = time.monotonic()
        if use_cache and self._cache and now - self._cache_ts < self._cache_ttl:
            return self._cache

        async with self._lock:
            # Re-check cache after acquiring the lock.
            now = time.monotonic()
            if use_cache and self._cache and now - self._cache_ts < self._cache_ttl:
                return self._cache

            results: List[TradingSignal] = []
            # Analyse concurrently but with a small bound to be gentle on APIs.
            sem = asyncio.Semaphore(4)

            async def _one(sym: str) -> Optional[TradingSignal]:
                async with sem:
                    try:
                        analysis = await ai_engine.analyze_symbol(sym, timeframe=timeframe)
                        return analysis.signal
                    except Exception as exc:  # pragma: no cover - network dependent
                        logger.debug("Scan failed for %s: %s", sym, exc)
                        return None

            gathered = await asyncio.gather(*(_one(s) for s in symbols))
            results = [s for s in gathered if s is not None]
            results.sort(key=lambda s: s.score, reverse=True)

            self._cache = results
            self._cache_ts = time.monotonic()
            return results

    async def best_opportunities(
        self, min_score: Optional[float] = None, limit: int = 5, symbols: Optional[List[str]] = None
    ) -> List[TradingSignal]:
        threshold = settings.signal_min_score if min_score is None else min_score
        signals = await self.scan(symbols=symbols)
        return [s for s in signals if s.score >= threshold][:limit]

    async def top(self, limit: int = 10, symbols: Optional[List[str]] = None) -> List[TradingSignal]:
        signals = await self.scan(symbols=symbols)
        return signals[:limit]


signal_scanner = SignalScanner()
