"""AI scoring engine: combine every analysis into a 0-100 score.

The score is a weighted sum of six factors (per the product spec):
    - Trend quality           (max 20)
    - Indicator confirmation  (max 20)
    - Volatility              (max 15)
    - Volume                  (max 15)
    - Historical analog       (max 15)
    - Market context          (max 15)
Total = 100.
"""
from __future__ import annotations

from ..models import ScoreBreakdown
from .ml_model import ModelPrediction
from .patterns import PatternResult
from .technical import TechnicalAssessment


def _trend_quality(tech: TechnicalAssessment) -> float:
    # ADX 0..~60 -> 0..20, only rewarded when a directional bias exists.
    if tech.bias == 0:
        return min(tech.trend_strength / 60.0, 1.0) * 8.0
    return min(tech.trend_strength / 40.0, 1.0) * 20.0


def _indicator_confirmation(tech: TechnicalAssessment, ml: ModelPrediction) -> float:
    # How aligned are the indicators (0.5..1.0) scaled to 0..14, plus ML agreement.
    conf = tech.confirmation_ratio  # 0.5 (split) .. 1.0 (unanimous)
    base = max(0.0, (conf - 0.5) / 0.5) * 14.0
    ml_edge = abs(ml.proba_up - 0.5) * 2.0  # 0..1
    ml_aligned = (ml.proba_up >= 0.5) == (tech.bias >= 0)
    bonus = (ml_edge * 6.0) if ml_aligned else 0.0
    return min(base + bonus, 20.0)


def _volatility(tech: TechnicalAssessment) -> float:
    # Sweet spot around 1.5%-4% ATR. Too low = no move, too high = risky.
    atr = tech.atr_pct
    if atr <= 0:
        return 4.0
    if atr < 0.5:
        return 5.0
    if atr <= 4.0:
        return 15.0
    if atr <= 7.0:
        return 10.0
    return 5.0


def _volume(tech: TechnicalAssessment) -> float:
    # Volume expansion confirms moves. ratio 1.0 -> ~7.5, >=2.0 -> 15.
    ratio = tech.volume_ratio
    return max(0.0, min(ratio / 2.0, 1.0)) * 15.0


def _historical(pattern: PatternResult, bias: int) -> float:
    if pattern.sample_size == 0:
        return 7.5
    rate = pattern.historical_up_rate  # probability of up move
    edge = rate if bias >= 0 else (1.0 - rate)
    # Map 0.5..1.0 edge -> 0..15
    return max(0.0, (edge - 0.5) / 0.5) * 15.0


def _market_context(sentiment: float, bias: int) -> float:
    # Sentiment in [-1, 1] aligned with the trade direction.
    aligned = sentiment if bias >= 0 else -sentiment
    # Map -1..1 -> 0..15 with neutral at ~7.5.
    return max(0.0, min((aligned + 1.0) / 2.0, 1.0)) * 15.0


def compute_score(
    tech: TechnicalAssessment,
    pattern: PatternResult,
    ml: ModelPrediction,
    sentiment: float,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        trend_quality=_trend_quality(tech),
        indicator_confirmation=_indicator_confirmation(tech, ml),
        volatility=_volatility(tech),
        volume=_volume(tech),
        historical_analog=_historical(pattern, tech.bias),
        market_context=_market_context(sentiment, tech.bias),
    )


def estimate_probability(score: float, ml: ModelPrediction, tech: TechnicalAssessment) -> float:
    """Blend the heuristic score with the ML edge into a calibrated probability.

    Deliberately conservative and capped well below 100% - we never imply
    certainty of profit.
    """
    score_component = score / 100.0  # 0..1
    ml_edge = ml.proba_up if tech.bias >= 0 else (1.0 - ml.proba_up)
    blended = 0.6 * score_component + 0.4 * ml_edge
    # Compress into a realistic 35%-85% band.
    prob = 35.0 + blended * 50.0
    return round(min(prob, 85.0), 1)
