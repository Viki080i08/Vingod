"""The AI engine: orchestrates every analysis module into a trade signal.

Combines technical analysis, fundamental context (news), quantitative analog
matching, machine learning and the scoring engine into a single
:class:`~trading_bot.models.TradingSignal`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..data.market_data import MarketDataError, market_data_provider
from ..data.news import news_provider
from ..models import (
    AssetClass,
    MarketData,
    SignalDirection,
    TradingSignal,
)
from . import patterns as pattern_mod
from . import scoring
from . import sentiment as sentiment_mod
from . import technical
from .ml_model import direction_model

logger = logging.getLogger(__name__)

# ATR multiples used to derive stop-loss / target from volatility.
STOP_ATR_MULT = 1.5
TARGET_ATR_MULT = 3.0

# Rough duration estimate per timeframe (in bars -> human readable).
_DURATION_HINT = {
    "15m": "quelques heures",
    "1h": "1 à 3 jours",
    "4h": "3 à 10 jours",
    "1d": "2 à 6 semaines",
}


@dataclass
class Analysis:
    """Full analysis bundle for a single asset."""

    market_data: MarketData
    technical: technical.TechnicalAssessment
    patterns: pattern_mod.PatternResult
    ml_proba_up: float
    ml_accuracy: float
    ml_trained: bool
    sentiment: float
    signal: TradingSignal


class AIEngine:
    def __init__(self, min_candles: int = 60) -> None:
        self._min_candles = min_candles

    async def analyze_symbol(self, symbol: str, timeframe: str = "1h") -> Analysis:
        market = await market_data_provider.get_market_data(symbol, timeframe=timeframe, limit=400)
        if not market.has_candles or len(market.candles) < self._min_candles:
            raise MarketDataError(f"Pas assez de données pour analyser {symbol}.")

        df = market.candles

        tech = technical.analyze(df)
        pat = pattern_mod.detect(df)

        model_key = f"{market.symbol}:{timeframe}"
        ml = direction_model.predict(model_key, df)

        # Fundamental / sentiment context from news.
        query = self._news_query(symbol, market.asset_class)
        try:
            sentiment_score = await news_provider.market_sentiment(query=query, limit=15)
            news = await news_provider.get_news(query=query, limit=5)
            market.news = news
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Sentiment fetch failed for %s: %s", symbol, exc)
            sentiment_score = 0.0

        breakdown = scoring.compute_score(tech, pat, ml, sentiment_score)
        score = breakdown.total()
        probability = scoring.estimate_probability(score, ml, tech)

        signal = self._build_signal(
            market, tech, pat, ml, sentiment_score, breakdown, score, probability, timeframe
        )

        return Analysis(
            market_data=market,
            technical=tech,
            patterns=pat,
            ml_proba_up=ml.proba_up,
            ml_accuracy=ml.accuracy,
            ml_trained=ml.trained,
            sentiment=sentiment_score,
            signal=signal,
        )

    def _build_signal(
        self,
        market: MarketData,
        tech: technical.TechnicalAssessment,
        pat: pattern_mod.PatternResult,
        ml,
        sentiment_score: float,
        breakdown,
        score: float,
        probability: float,
        timeframe: str,
    ) -> TradingSignal:
        price = tech.last_price
        atr_abs = (tech.atr_pct / 100.0) * price
        if atr_abs <= 0:
            atr_abs = price * 0.01

        direction = self._direction(tech, ml.proba_up)

        if direction == SignalDirection.LONG:
            stop = price - STOP_ATR_MULT * atr_abs
            target = price + TARGET_ATR_MULT * atr_abs
        elif direction == SignalDirection.SHORT:
            stop = price + STOP_ATR_MULT * atr_abs
            target = price - TARGET_ATR_MULT * atr_abs
        else:
            stop = price - STOP_ATR_MULT * atr_abs
            target = price + TARGET_ATR_MULT * atr_abs

        reasons = self._reasons(tech, pat, ml, sentiment_score)

        return TradingSignal(
            symbol=market.symbol,
            asset_class=market.asset_class,
            direction=direction,
            entry=round(price, 8),
            target=round(target, 8),
            stop_loss=round(stop, 8),
            timeframe=timeframe,
            estimated_duration=_DURATION_HINT.get(timeframe, "—"),
            score=score,
            probability=probability,
            score_breakdown=breakdown,
            technical_summary=self._technical_summary(tech),
            fundamental_summary=self._fundamental_summary(sentiment_score, market),
            sentiment_summary=f"{sentiment_mod.label(sentiment_score)} ({sentiment_score:+.2f})",
            reasons=reasons,
        )

    @staticmethod
    def _direction(tech: technical.TechnicalAssessment, proba_up: float) -> SignalDirection:
        if tech.bias > 0 and proba_up >= 0.5:
            return SignalDirection.LONG
        if tech.bias < 0 and proba_up <= 0.5:
            return SignalDirection.SHORT
        # Fall back to whichever signal is stronger.
        if tech.bias > 0:
            return SignalDirection.LONG
        if tech.bias < 0:
            return SignalDirection.SHORT
        return SignalDirection.LONG if proba_up >= 0.5 else SignalDirection.SHORT

    @staticmethod
    def _technical_summary(tech: technical.TechnicalAssessment) -> str:
        return (
            f"Tendance {tech.trend} (ADX {tech.trend_strength:.0f}), RSI {tech.rsi:.0f}, "
            f"ATR {tech.atr_pct:.1f}%, volume x{tech.volume_ratio:.2f}"
        )

    @staticmethod
    def _fundamental_summary(sentiment_score: float, market: MarketData) -> str:
        change = market.quote.change_pct_24h
        change_txt = f", variation 24h {change:+.2f}%" if change is not None else ""
        return (
            f"Contexte news {sentiment_mod.label(sentiment_score).lower()}{change_txt}"
        )

    @staticmethod
    def _reasons(tech, pat, ml, sentiment_score) -> List[str]:
        reasons: List[str] = list(tech.signals[:4])
        if pat.detected:
            reasons.extend(pat.detected[:2])
        if pat.sample_size:
            reasons.append(
                f"Analogues historiques: {pat.historical_up_rate*100:.0f}% de hausse sur {pat.sample_size} cas"
            )
        if ml.trained:
            reasons.append(
                f"Modèle ML: probabilité de hausse {ml.proba_up*100:.0f}% (précision backtest {ml.accuracy*100:.0f}%)"
            )
        if abs(sentiment_score) >= 0.1:
            reasons.append(f"Sentiment des news {sentiment_mod.label(sentiment_score).lower()}")
        return reasons[:8]

    @staticmethod
    def _news_query(symbol: str, asset_class: AssetClass) -> Optional[str]:
        base = symbol.upper()
        if asset_class == AssetClass.CRYPTO:
            for quote in ("USDT", "USDC", "BUSD", "USD", "FDUSD"):
                if base.endswith(quote):
                    base = base[: -len(quote)]
                    break
            mapping = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "Ripple"}
            return mapping.get(base, base)
        return base


ai_engine = AIEngine()
