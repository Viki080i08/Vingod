"""Helpers to classify and resolve user-supplied tickers."""
from __future__ import annotations

import re
from typing import Optional, Tuple

from ..models import AssetClass

FOREX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "AUDJPY", "XAUUSD", "XAGUSD",
    "EURCHF", "GBPCHF", "USDMXN", "USDTRY", "USDZAR",
}

INDEX_SYMBOLS = {
    "SPX", "SPX500", "US500", "NDX", "NAS100", "US100", "DJI", "US30",
    "DAX", "GER40", "FTSE", "UK100", "CAC", "FRA40", "NIKKEI", "JP225",
}

CRYPTO_QUOTES = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "EUR", "FDUSD", "TRY")

# Well-known crypto base tickers — if the user types only ``BTC`` or ``PEPE``,
# treat as crypto (not stock).
KNOWN_CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "MATIC",
    "POL", "LINK", "UNI", "ATOM", "LTC", "BCH", "NEAR", "APT", "ARB", "OP",
    "FIL", "ICP", "HBAR", "VET", "ALGO", "SAND", "MANA", "AAVE", "MKR", "CRV",
    "SNX", "PEPE", "SHIB", "WIF", "BONK", "FLOKI", "TRX", "TON", "SUI", "SEI",
    "INJ", "FTM", "RUNE", "EGLD", "XTZ", "EOS", "XLM", "XMR", "ETC", "USDT",
    "USDC", "RENDER", "FET", "TAO", "WLD", "JUP", "TIA", "STRK", "ENA", "ONDO",
    "PENDLE", "STX", "IMX", "GRT", "LDO", "CAKE", "ENS", "CFX", "ORDI", "PYTH",
}


def normalize(symbol: str) -> str:
    return re.sub(r"[\s/\-_]", "", symbol.strip().upper())


def base_ticker(symbol: str) -> str:
    """Extract the base asset from a pair like BTCUSDT → BTC."""
    s = normalize(symbol)
    for quote in sorted(CRYPTO_QUOTES, key=len, reverse=True):
        if s.endswith(quote) and len(s) > len(quote):
            return s[: -len(quote)]
    return s


def classify(symbol: str) -> AssetClass:
    """Best effort classification of a ticker into an asset class."""
    s = normalize(symbol)

    if s in INDEX_SYMBOLS:
        return AssetClass.INDEX
    if s in FOREX_PAIRS:
        return AssetClass.FOREX

    # Metals quoted as forex.
    if s in ("XAUUSD", "XAGUSD"):
        return AssetClass.FOREX

    # Full crypto pair (BTCUSDT, ETHUSDC…).
    for quote in CRYPTO_QUOTES:
        if s.endswith(quote) and len(s) > len(quote):
            return AssetClass.CRYPTO

    # Short ticker that is a known crypto base (BTC, ETH, PEPE…).
    if s in KNOWN_CRYPTO_BASES:
        return AssetClass.CRYPTO

    # 6-letter all-alpha → forex (EURUSD) unless it's a known crypto base combo.
    if len(s) == 6 and s.isalpha() and s not in KNOWN_CRYPTO_BASES:
        return AssetClass.FOREX

    # 2-5 letter tickers: prefer crypto if in known list, else stock.
    if 1 <= len(s) <= 5 and s.isalpha():
        return AssetClass.STOCK

    return AssetClass.UNKNOWN


def crypto_pair_candidates(symbol: str) -> Tuple[str, ...]:
    """Possible Binance pair names to try for a user symbol."""
    s = normalize(symbol)
    base = base_ticker(s)
    if s in KNOWN_CRYPTO_BASES or base in KNOWN_CRYPTO_BASES:
        b = base if base in KNOWN_CRYPTO_BASES else s
        return tuple(dict.fromkeys([s, f"{b}USDT", f"{b}USDC", f"{b}FDUSD", f"{b}BUSD", f"{b}BTC"]))
    # Already looks like a pair.
    for quote in CRYPTO_QUOTES:
        if s.endswith(quote):
            return (s,)
    return (f"{s}USDT", f"{s}USDC", s)


def display_symbol(symbol: str, resolved: Optional[str] = None) -> str:
    return resolved or normalize(symbol)


def to_forex_pair(symbol: str) -> tuple[str, str]:
    """Split a 6-char forex symbol into (base, quote)."""
    s = normalize(symbol)
    return s[:3], s[3:]
