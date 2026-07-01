"""Real-time market data acquisition — multi-provider, no API key required.

Provider chain (automatic fallback):
  Crypto   → Binance (1000+ paires) → CoinGecko (10 000+ cryptos)
  Actions  → Yahoo Finance
  Forex    → Yahoo Finance
  Indices  → Yahoo Finance
  Optionnel → Twelve Data si ``TWELVE_DATA_API_KEY`` est configurée
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Set

import httpx
import pandas as pd

from ..config import settings
from ..models import AssetClass, MarketData, Quote
from . import symbols
from .coingecko import coingecko_provider
from .yahoo_finance import yahoo_provider

logger = logging.getLogger(__name__)

BINANCE_HOSTS = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api-gcp.binance.com",
)
TWELVE_DATA_BASE = "https://api.twelvedata.com"

_BINANCE_INTERVALS = {"15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
_TWELVE_INTERVALS = {"15m": "15min", "1h": "1h", "4h": "4h", "1d": "1day"}


class MarketDataError(RuntimeError):
    """Raised when data for a symbol cannot be retrieved."""


class MarketDataProvider:
    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._binance_symbols: Optional[Set[str]] = None
        self._binance_cache_ts: float = 0.0

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, headers={"User-Agent": "trading-ai-bot/1.0"})

    async def _binance_get(self, path: str, params: dict | None = None):
        last_status = None
        async with await self._client() as client:
            for host in BINANCE_HOSTS:
                try:
                    resp = await client.get(f"{host}{path}", params=params)
                except httpx.HTTPError as exc:  # pragma: no cover
                    last_status = str(exc)
                    continue
                if resp.status_code == 200:
                    return resp.json()
                last_status = resp.status_code
        raise MarketDataError(f"Binance indisponible ({last_status}).")

    async def _load_binance_symbols(self) -> Set[str]:
        if self._binance_symbols and time.monotonic() - self._binance_cache_ts < 3600:
            return self._binance_symbols
        info = await self._binance_get("/api/v3/exchangeInfo")
        self._binance_symbols = {
            s["symbol"]
            for s in info.get("symbols", [])
            if s.get("status") == "TRADING" and s.get("quoteAsset") in ("USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH")
        }
        self._binance_cache_ts = time.monotonic()
        logger.info("Binance: %d paires chargées", len(self._binance_symbols))
        return self._binance_symbols

    async def resolve_binance_pair(self, symbol: str) -> Optional[str]:
        """Map user input (BTC, PEPE, BTCUSDT…) to a valid Binance pair."""
        available = await self._load_binance_symbols()
        for candidate in symbols.crypto_pair_candidates(symbol):
            if candidate in available:
                return candidate
        return None

    # ------------------------------------------------------------------ Binance
    async def _binance_quote(self, pair: str) -> Quote:
        d = await self._binance_get("/api/v3/ticker/24hr", params={"symbol": pair})
        return Quote(
            symbol=pair,
            asset_class=AssetClass.CRYPTO,
            price=float(d["lastPrice"]),
            change_pct_24h=float(d["priceChangePercent"]),
            volume_24h=float(d["quoteVolume"]),
            high_24h=float(d["highPrice"]),
            low_24h=float(d["lowPrice"]),
        )

    async def _binance_candles(self, pair: str, timeframe: str, limit: int) -> pd.DataFrame:
        interval = _BINANCE_INTERVALS.get(timeframe, "1h")
        raw = await self._binance_get(
            "/api/v3/klines",
            params={"symbol": pair, "interval": interval, "limit": min(limit, 1000)},
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
        return pd.DataFrame(rows).set_index("time")

    # ----------------------------------------------------------- CoinGecko
    async def _coingecko_quote(self, symbol: str) -> Quote:
        base = symbols.base_ticker(symbol)
        price, change, _, _ = await coingecko_provider.quote(base)
        return Quote(
            symbol=base,
            asset_class=AssetClass.CRYPTO,
            price=price,
            change_pct_24h=change,
        )

    async def _coingecko_candles(self, symbol: str, timeframe: str) -> pd.DataFrame:
        base = symbols.base_ticker(symbol)
        days = {"15m": 7, "1h": 30, "4h": 90, "1d": 365}.get(timeframe, 30)
        return await coingecko_provider.candles(base, days=days)

    # --------------------------------------------------------- Yahoo Finance
    async def _yahoo_quote(self, symbol: str, asset_class: AssetClass) -> Quote:
        price, change = await yahoo_provider.quote(symbol, asset_class)
        return Quote(
            symbol=symbols.normalize(symbol),
            asset_class=asset_class,
            price=price,
            change_pct_24h=change,
        )

    async def _yahoo_candles(self, symbol: str, asset_class: AssetClass, timeframe: str) -> pd.DataFrame:
        return await yahoo_provider.candles(symbol, asset_class, timeframe)

    # ----------------------------------------------------------- Twelve Data
    async def _twelve_quote(self, symbol: str, asset_class: AssetClass) -> Quote:
        api_symbol = self._twelve_symbol(symbol, asset_class)
        async with await self._client() as client:
            resp = await client.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": api_symbol, "apikey": settings.twelve_data_api_key},
            )
            d = resp.json()
        if "close" not in d:
            raise MarketDataError(f"Twelve Data : {d.get('message', d)}")
        return Quote(
            symbol=symbols.normalize(symbol),
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
            raise MarketDataError(f"Twelve Data : {d.get('message', d)}")
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
        return pd.DataFrame(rows).set_index("time").sort_index()

    @staticmethod
    def _twelve_symbol(symbol: str, asset_class: AssetClass) -> str:
        if asset_class == AssetClass.FOREX:
            base, quote = symbols.to_forex_pair(symbol)
            return f"{base}/{quote}"
        return symbols.normalize(symbol)

    # ------------------------------------------------------------- public API
    async def get_quote(self, symbol: str) -> Quote:
        asset_class = symbols.classify(symbol)
        norm = symbols.normalize(symbol)

        if asset_class == AssetClass.CRYPTO:
            pair = await self.resolve_binance_pair(symbol)
            if pair:
                return await self._binance_quote(pair)
            try:
                return await self._coingecko_quote(symbol)
            except Exception as exc:
                raise MarketDataError(
                    f"Crypto « {norm} » introuvable. Essayez avec le suffixe USDT "
                    f"(ex: {symbols.base_ticker(norm)}USDT) ou vérifiez l'orthographe."
                ) from exc

        # Stocks / forex / indices → Yahoo (gratuit).
        try:
            return await self._yahoo_quote(symbol, asset_class)
        except Exception as yahoo_exc:
            if settings.twelve_data_api_key:
                try:
                    return await self._twelve_quote(symbol, asset_class)
                except Exception:
                    pass
            raise MarketDataError(
                f"Actif « {norm} » ({asset_class.value}) introuvable. "
                f"Exemples valides : AAPL, TSLA, EURUSD, SPX, BTC, ETH, SOL, PEPE. "
                f"Détail : {yahoo_exc}"
            ) from yahoo_exc

    async def get_candles(self, symbol: str, timeframe: str = "1h", limit: int = 300) -> pd.DataFrame:
        asset_class = symbols.classify(symbol)
        norm = symbols.normalize(symbol)

        if asset_class == AssetClass.CRYPTO:
            pair = await self.resolve_binance_pair(symbol)
            if pair:
                return await self._binance_candles(pair, timeframe, limit)
            try:
                return await self._coingecko_candles(symbol, timeframe)
            except Exception as exc:
                raise MarketDataError(
                    f"Pas de données historiques pour « {norm} ». "
                    f"Essayez {symbols.base_ticker(norm)}USDT."
                ) from exc

        try:
            return await self._yahoo_candles(symbol, asset_class, timeframe)
        except Exception as yahoo_exc:
            if settings.twelve_data_api_key:
                try:
                    return await self._twelve_candles(symbol, asset_class, timeframe, limit)
                except Exception:
                    pass
            raise MarketDataError(
                f"Pas de données pour « {norm} » ({asset_class.value}). Détail : {yahoo_exc}"
            ) from yahoo_exc

    async def get_market_data(
        self, symbol: str, timeframe: str = "1h", limit: int = 300
    ) -> MarketData:
        asset_class = symbols.classify(symbol)
        quote = await self.get_quote(symbol)
        candles = await self.get_candles(symbol, timeframe=timeframe, limit=limit)
        return MarketData(
            symbol=quote.symbol,
            asset_class=asset_class,
            quote=quote,
            candles=candles,
        )

    async def get_top_movers(self, quote_currency: str = "USDT", limit: int = 20) -> list[Quote]:
        data = await self._binance_get("/api/v3/ticker/24hr")
        quotes: list[Quote] = []
        for d in data:
            sym = d.get("symbol", "")
            if not sym.endswith(quote_currency):
                continue
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
