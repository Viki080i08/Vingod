"""CoinGecko public API — thousands of cryptos, no API key required.

Used as a fallback when a coin is not listed on Binance (or the user types only
the base ticker like ``DOGE`` / ``PEPE``).
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

BASE = "https://api.coingecko.com/api/v3"

# Fast lookup for the most traded tickers (symbol → coingecko id).
COMMON_IDS: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "FIL": "filecoin",
    "ICP": "internet-computer",
    "HBAR": "hedera-hashgraph",
    "VET": "vechain",
    "ALGO": "algorand",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AAVE": "aave",
    "MKR": "maker",
    "CRV": "curve-dao-token",
    "SNX": "havven",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "FLOKI": "floki",
    "TRX": "tron",
    "TON": "the-open-network",
    "SUI": "sui",
    "SEI": "sei-network",
    "INJ": "injective-protocol",
    "FTM": "fantom",
    "RUNE": "thorchain",
    "EGLD": "multiversx-egl",
    "XTZ": "tezos",
    "EOS": "eos",
    "XLM": "stellar",
    "XMR": "monero",
    "ETC": "ethereum-classic",
    "USDT": "tether",
    "USDC": "usd-coin",
}


class CoinGeckoProvider:
    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout
        self._id_cache: Dict[str, str] = dict(COMMON_IDS)
        self._last_search: float = 0.0

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "trading-ai-bot/1.0", "Accept": "application/json"},
        ) as client:
            resp = await client.get(f"{BASE}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()

    async def resolve_id(self, symbol: str) -> Optional[str]:
        base = symbol.upper().replace("USDT", "").replace("USDC", "").replace("USD", "")
        if base in self._id_cache:
            return self._id_cache[base]
        # Rate-limit searches (CoinGecko free tier).
        now = time.monotonic()
        if now - self._last_search < 1.2:
            return None
        self._last_search = now
        try:
            data = await self._get("/search", {"query": base})
            for coin in data.get("coins", [])[:5]:
                if coin.get("symbol", "").upper() == base:
                    cid = coin["id"]
                    self._id_cache[base] = cid
                    return cid
        except Exception as exc:  # pragma: no cover - network
            logger.debug("CoinGecko search failed for %s: %s", base, exc)
        return None

    async def quote(self, symbol: str) -> Tuple[float, Optional[float], Optional[float], Optional[float]]:
        """Return (price, change_pct_24h, high_24h, low_24h)."""
        cid = await self.resolve_id(symbol)
        if not cid:
            raise RuntimeError(f"Crypto {symbol} introuvable sur CoinGecko.")
        data = await self._get(
            "/simple/price",
            {
                "ids": cid,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
            },
        )
        row = data.get(cid, {})
        price = float(row.get("usd", 0))
        change = row.get("usd_24h_change")
        return price, float(change) if change is not None else None, None, None

    async def candles(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """OHLCV from CoinGecko (granularity auto: ~4h for 7-30 days)."""
        cid = await self.resolve_id(symbol)
        if not cid:
            raise RuntimeError(f"Crypto {symbol} introuvable sur CoinGecko.")
        # OHLC: [timestamp_ms, open, high, low, close]
        raw = await self._get(f"/coins/{cid}/ohlc", {"vs_currency": "usd", "days": str(days)})
        if not raw:
            raise RuntimeError(f"Pas de données OHLC pour {symbol}.")
        rows = [
            {
                "time": pd.to_datetime(item[0], unit="ms", utc=True),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": 0.0,
            }
            for item in raw
        ]
        df = pd.DataFrame(rows).set_index("time")
        # Enrich volume from market_chart if available.
        try:
            chart = await self._get(
                f"/coins/{cid}/market_chart",
                {"vs_currency": "usd", "days": str(days)},
            )
            vols = chart.get("total_volumes", [])
            if vols:
                vol_df = pd.DataFrame(vols, columns=["time", "volume"])
                vol_df["time"] = pd.to_datetime(vol_df["time"], unit="ms", utc=True)
                vol_df = vol_df.set_index("time").resample("4h").mean()
                df = df.join(vol_df, how="left")
                df["volume"] = df["volume"].fillna(0.0)
        except Exception:  # pragma: no cover
            pass
        return df


coingecko_provider = CoinGeckoProvider()
