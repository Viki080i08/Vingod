"""Shared data structures used across the whole application."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import pandas as pd


class AssetClass(str, Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    STOCK = "stock"
    INDEX = "index"
    UNKNOWN = "unknown"


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class Quote:
    """A real-time snapshot of an asset."""

    symbol: str
    asset_class: AssetClass
    price: float
    change_pct_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published: Optional[datetime] = None
    summary: str = ""
    sentiment: float = 0.0  # -1 (very negative) .. +1 (very positive)


@dataclass
class EconomicEvent:
    title: str
    country: str
    importance: str  # low / medium / high
    when: Optional[datetime] = None
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


@dataclass
class ScoreBreakdown:
    """Detailed contribution of each factor to the final AI score (0-100)."""

    trend_quality: float = 0.0
    indicator_confirmation: float = 0.0
    volatility: float = 0.0
    volume: float = 0.0
    historical_analog: float = 0.0
    market_context: float = 0.0

    def total(self) -> float:
        return round(
            self.trend_quality
            + self.indicator_confirmation
            + self.volatility
            + self.volume
            + self.historical_analog
            + self.market_context,
            1,
        )

    def as_dict(self) -> Dict[str, float]:
        return {
            "trend_quality": round(self.trend_quality, 1),
            "indicator_confirmation": round(self.indicator_confirmation, 1),
            "volatility": round(self.volatility, 1),
            "volume": round(self.volume, 1),
            "historical_analog": round(self.historical_analog, 1),
            "market_context": round(self.market_context, 1),
        }


@dataclass
class TradingSignal:
    """A complete trade opportunity produced by the AI engine."""

    symbol: str
    asset_class: AssetClass
    direction: SignalDirection
    entry: float
    target: float
    stop_loss: float
    timeframe: str = "1h"
    estimated_duration: str = "—"
    score: float = 0.0
    probability: float = 0.0
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    technical_summary: str = ""
    fundamental_summary: str = ""
    sentiment_summary: str = ""
    reasons: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_reward(self) -> float:
        risk = abs(self.entry - self.stop_loss)
        reward = abs(self.target - self.entry)
        if risk <= 0:
            return 0.0
        return round(reward / risk, 2)


@dataclass
class MarketData:
    """Bundle of everything the AI needs to reason about a single asset."""

    symbol: str
    asset_class: AssetClass
    quote: Quote
    candles: "pd.DataFrame"  # columns: open, high, low, close, volume ; index: datetime
    news: List[NewsItem] = field(default_factory=list)

    @property
    def has_candles(self) -> bool:
        return self.candles is not None and not self.candles.empty
