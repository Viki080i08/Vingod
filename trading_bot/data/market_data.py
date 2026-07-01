"""Real-time market data acquisition.

Crypto uses the Binance public REST API (no API key required).
Forex / stocks / indices use Twelve Data or Alpha Vantage if a key is set,
otherwise the caller receives ``None`` and can render a graceful message.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
import pandas as pd

from ..config import settings
from ..models import AssetClass, MarketData, Quote
from . import symbols

logger = logging.getLogger(__name__)

# Public market-data hosts, tried in order. ``data-api.binance.vision`` is the
# official read-only data endpoint and is not geo-restricted, so it works from
# cloud regions where ``api.binance.com`` returns HTTP 451.
BINANCE_HOSTS = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api-gcp.binance.com",
)
TWELVE_DATA_BASE = "https://api.twelvedata.com"
ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"

# Map our generic timeframe labels to provider-specific interval strings.
_BINANCE_INTERVALS = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
_TWELVE_INTERVALS = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1day"}


class MarketDataError(RuntimeError):
    """Raised when data for a symbol cannot be retrieved."""


class MarketDataProvider:
    """Fetches quotes and OHLCV candles across asset classes."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, headers={"User-Agent": "trading-ai-bot/1.0"})

    async def _binance_get(self, path: str, params: dict | None = None):
        """GET a Binance endpoint, falling back across hosts on failure."""
        last_status = None
        async with await self._client() as client:
            for host in BINANCE_HOSTS:
                try:
                    resp = await client.get(f"{host}{path}", params=params)
                except httpx.HTTPError as exc:  # pragma: no cover - network dependent
                    last_status = str(exc)
                    continue
                if resp.status_code == 200:
                    return resp.json()
                last_status = resp.status_code
        raise MarketDataError(f"Binance request {path} failed (last status: {last_status}).")

    # ------------------------------------------------------------------ crypto
    async def _binance_quote(self, symbol: str) -> Quote:
        d = await self._binance_get("/api/v3/ticker/24hr", params={"symbol": symbol})
        return Quote(
            symbol=symbol,
            asset_class=AssetClass.CRYPTO,
            price=float(d["lastPrice"]),
            change_pct_24h=float(d["priceChangePercent"]),
            volume_24h=float(d["quoteVolume"]),
            high_24h=float(d["highPrice"]),
            low_24h=float(d["lowPrice"]),
        )

    async def _binance_candles(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        interval = _BINANCE_INTERVALS.get(timeframe, "1h")
        raw = await self._binance_get(
            "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
        )
        rows = [
            {
                "time": pd.to_datetime(item[0], unit="ms", utc=True),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
            for item in raw
        ]
        df = pd.DataFrame(rows).set_index("time")
        return df

    # ----------------------------------------------------------- twelve data
    async def _twelve_quote(self, symbol: str, asset_class: AssetClass) -> Quote:
        api_symbol = self._twelve_symbol(symbol, asset_class)
        async with await self._client() as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": api_symbol, "apikey": settings.twelve_data_api_key},
            )
            d = resp.json()
        if "close" not in d:
            raise MarketDataError(f"Twelve Data quote failed for {symbol}: {d.get('message', d)}")
        return Quote(
            symbol=symbol,
            asset_class=asset_class,
            price=float(d["close"]),
            change_pct_24h=float(d.get("percent_change", 0) or 0),
            volume_24h=float(d["volume"]) if d.get("volume") not in (None, "") else None,
            high_24h=float(d["high"]) if d.get("high") not in (None, "") else None,
            low_24h=float(d["low"]) if d.get("low") not in (None, "") else None,
        )

    async def _twelve_candles(
        self, symbol: str, asset_class: AssetClass, timeframe: str, limit: int
    ) -> pd.DataFrame:
        api_symbol = self._twelve_symbol(symbol, asset_class)
        interval = _TWELVE_INTERVALS.get(timeframe, "1h")
        async with await self._client() as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/time_series",
                params={
                    "symbol": api_symbol,
                    "interval": interval,
                    "outputsize": min(limit, 5000),
                    "apikey": settings.twelve_data_api_key,
                },
            )
            d = resp.json()
        if "values" not in d:
            raise MarketDataError(f"Twelve Data series failed for {symbol}: {d.get('message', d)}")
        rows = [
            {
                "time": pd.to_datetime(v["datetime"], utc=True),
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                "volume": float(v.get("volume", 0) or 0),
            }
            for v in d["values"]
        ]
        df = pd.DataFrame(rows).set_index("time").sort_index()
        return df

    @staticmethod
    def _twelve_symbol(symbol: str, asset_class: AssetClass) -> str:
        if asset_class == AssetClass.FOREX:
            base, quote = symbols.to_forex_pair(symbol)
            return f"{base}/{quote}"
        return symbols.normalize(symbol)

    # ------------------------------------------------------------- public api
    async def get_quote(self, symbol: str) -> Quote:
        asset_class = symbols.classify(symbol)
        norm = symbols.normalize(symbol)
        if asset_class == AssetClass.CRYPTO:
            return await self._binance_quote(norm)
        if settings.twelve_data_api_key:
            return await self._twelve_quote(norm, asset_class)
        raise MarketDataError(
            f"No data provider configured for {symbol} ({asset_class.value}). "
            "Set TWELVE_DATA_API_KEY to enable forex/stocks/indices."
        )

    async def get_candles(self, symbol: str, timeframe: str = "1h", limit: int = 300) -> pd.DataFrame:
        asset_class = symbols.classify(symbol)
        norm = symbols.normalize(symbol)
        if asset_class == AssetClass.CRYPTO:
            return await self._binance_candles(norm, timeframe, limit)
        if settings.twelve_data_api_key:
            return await self._twelve_candles(norm, asset_class, timeframe, limit)
        raise MarketDataError(
            f"No data provider configured for {symbol} ({asset_class.value}). "
            "Set TWELVE_DATA_API_KEY to enable forex/stocks/indices."
        )

    async def get_market_data(
        self, symbol: str, timeframe: str = "1h", limit: int = 300
    ) -> MarketData:
        asset_class = symbols.classify(symbol)
        quote = await self.get_quote(symbol)
        candles = await self.get_candles(symbol, timeframe=timeframe, limit=limit)
        return MarketData(
            symbol=symbols.normalize(symbol),
            asset_class=asset_class,
            quote=quote,
            candles=candles,
        )

    async def get_top_movers(self, quote_currency: str = "USDT", limit: int = 20) -> list[Quote]:
        """Return the most active crypto pairs by 24h quote volume."""
        data = await self._binance_get("/api/v3/ticker/24hr")
        quotes: list[Quote] = []
        for d in data:
            sym = d.get("symbol", "")
            if not sym.endswith(quote_currency):
                continue
            # Skip leveraged tokens and low quality pairs.
            if any(token in sym for token in ("UP", "DOWN", "BULL", "BEAR")):
                continue
            try:
                quotes.append(
                    Quote(
                        symbol=sym,
                        asset_class=AssetClass.CRYPTO,
                        price=float(d["lastPrice"]),
                        change_pct_24h=float(d["priceChangePercent"]),
                        volume_24h=float(d["quoteVolume"]),
                        high_24h=float(d["highPrice"]),
                        low_24h=float(d["lowPrice"]),
                    )
                )
            except (KeyError, ValueError):
                continue
        quotes.sort(key=lambda q: q.volume_24h or 0, reverse=True)
        return quotes[:limit]


market_data_provider = MarketDataProvider()
