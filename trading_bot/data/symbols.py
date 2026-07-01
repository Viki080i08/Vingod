"""Helpers to classify a user supplied symbol into an asset class."""
from __future__ import annotations

import re

from ..models import AssetClass

# A small, extendable set of well known forex pairs and index tickers.
FOREX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "AUDJPY", "XAUUSD", "XAGUSD",
}

INDEX_SYMBOLS = {
    "SPX", "SPX500", "US500", "NDX", "NAS100", "US100", "DJI", "US30",
    "DAX", "GER40", "FTSE", "UK100", "CAC", "FRA40", "NIKKEI", "JP225",
}

# Common quote currencies used by crypto exchanges.
CRYPTO_QUOTES = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "EUR", "FDUSD")


def normalize(symbol: str) -> str:
    return re.sub(r"[\s/\-_]", "", symbol.strip().upper())


def classify(symbol: str) -> AssetClass:
    """Best effort classification of a ticker into an asset class."""
    s = normalize(symbol)

    if s in INDEX_SYMBOLS:
        return AssetClass.INDEX
    if s in FOREX_PAIRS:
        return AssetClass.FOREX

    # 6-letter all-alpha strings that look like two 3-letter currencies.
    if len(s) == 6 and s.isalpha():
        return AssetClass.FOREX

    # Crypto: ends with a known quote currency (e.g. BTCUSDT, ETHUSDC).
    for quote in CRYPTO_QUOTES:
        if s.endswith(quote) and len(s) > len(quote):
            return AssetClass.CRYPTO

    # Fallback: short all-alpha ticker -> treat as a stock (AAPL, TSLA...).
    if 1 <= len(s) <= 5 and s.isalpha():
        return AssetClass.STOCK

    return AssetClass.UNKNOWN


def to_forex_pair(symbol: str) -> tuple[str, str]:
    """Split a 6-char forex symbol into (base, quote)."""
    s = normalize(symbol)
    return s[:3], s[3:]
