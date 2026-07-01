"""Yahoo Finance chart API — stocks, forex, indices, no API key required."""
from __future__ import annotations

import logging
from typing import Optional

import httpx
import pandas as pd

from ..models import AssetClass

logger = logging.getLogger(__name__)

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

# Friendly ticker → Yahoo symbol.
INDEX_MAP = {
    "SPX": "^GSPC",
    "SPX500": "^GSPC",
    "US500": "^GSPC",
    "NDX": "^NDX",
    "NAS100": "^NDX",
    "US100": "^NDX",
    "DJI": "^DJI",
    "US30": "^DJI",
    "DAX": "^GDAXI",
    "GER40": "^GDAXI",
    "FTSE": "^FTSE",
    "UK100": "^FTSE",
    "CAC": "^FCHI",
    "FRA40": "^FCHI",
    "NIKKEI": "^N225",
    "JP225": "^N225",
}

_INTERVAL = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}  # 4h resampled later
_RANGE = {"15m": "5d", "1h": "1mo", "4h": "3mo", "1d": "1y"}


class YahooFinanceProvider:
    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout

    def yahoo_symbol(self, symbol: str, asset_class: AssetClass) -> str:
        s = symbol.upper().replace("/", "").replace("-", "")
        if asset_class == AssetClass.INDEX or s in INDEX_MAP:
            return INDEX_MAP.get(s, s if s.startswith("^") else f"^{s}")
        if asset_class == AssetClass.FOREX:
            if s.endswith("USD") or len(s) == 6:
                return f"{s}=X"
            return f"{s}=X"
        if s == "XAUUSD":
            return "GC=F"  # gold futures
        if s == "XAGUSD":
            return "SI=F"  # silver futures
        return s

    async def fetch_chart(
        self, symbol: str, asset_class: AssetClass, timeframe: str = "1h"
    ) -> dict:
        ysym = self.yahoo_symbol(symbol, asset_class)
        interval = _INTERVAL.get(timeframe, "1h")
        range_ = _RANGE.get(timeframe, "1mo")
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; trading-ai-bot/1.0)"},
        ) as client:
            resp = await client.get(
                f"{CHART_URL}/{ysym}",
                params={"interval": interval, "range": range_},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Yahoo Finance erreur {resp.status_code} pour {symbol}.")
            data = resp.json()
        result = data.get("chart", {}).get("result")
        if not result:
            err = data.get("chart", {}).get("error", {})
            raise RuntimeError(f"Symbole {symbol} introuvable sur Yahoo Finance ({err}).")
        return result[0]

    async def quote(self, symbol: str, asset_class: AssetClass) -> tuple[float, Optional[float]]:
        chart = await self.fetch_chart(symbol, asset_class, "1h")
        meta = chart["meta"]
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change_pct = None
        if prev and float(prev) > 0:
            change_pct = (price / float(prev) - 1.0) * 100.0
        return price, change_pct

    async def candles(
        self, symbol: str, asset_class: AssetClass, timeframe: str = "1h"
    ) -> pd.DataFrame:
        chart = await self.fetch_chart(symbol, asset_class, timeframe)
        ts = chart.get("timestamp") or []
        quote = (chart.get("indicators") or {}).get("quote", [{}])[0]
        if not ts:
            raise RuntimeError(f"Pas de bougies pour {symbol}.")
        rows = []
        for i, t in enumerate(ts):
            o = quote.get("open", [None])[i]
            h = quote.get("high", [None])[i]
            l = quote.get("low", [None])[i]
            c = quote.get("close", [None])[i]
            v = quote.get("volume", [None])[i]
            if c is None:
                continue
            rows.append(
                {
                    "time": pd.to_datetime(t, unit="s", utc=True),
                    "open": float(o or c),
                    "high": float(h or c),
                    "low": float(l or c),
                    "close": float(c),
                    "volume": float(v or 0),
                }
            )
        df = pd.DataFrame(rows).set_index("time")
        if timeframe == "4h" and not df.empty:
            df = (
                df.resample("4h")
                .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
                .dropna()
            )
        return df


yahoo_provider = YahooFinanceProvider()
