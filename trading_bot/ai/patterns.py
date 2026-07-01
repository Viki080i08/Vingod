"""Candlestick & chart pattern recognition plus historical analog matching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass
class PatternResult:
    detected: List[str]
    # Historical analog score: how often a similar recent shape led to an up move.
    historical_up_rate: float  # 0..1
    sample_size: int


def _candle_patterns(df: pd.DataFrame) -> List[str]:
    out: List[str] = []
    if len(df) < 3:
        return out
    o = df["open"].to_numpy()
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    c = df["close"].to_numpy()

    body = abs(c[-1] - o[-1])
    rng = max(h[-1] - l[-1], 1e-12)
    upper_wick = h[-1] - max(c[-1], o[-1])
    lower_wick = min(c[-1], o[-1]) - l[-1]

    # Doji
    if body <= 0.1 * rng:
        out.append("Doji (indécision)")
    # Hammer / hanging man
    if lower_wick >= 2 * body and upper_wick <= body:
        out.append("Marteau (retournement haussier potentiel)")
    # Shooting star
    if upper_wick >= 2 * body and lower_wick <= body:
        out.append("Étoile filante (retournement baissier potentiel)")
    # Bullish / bearish engulfing
    prev_body_up = c[-2] > o[-2]
    curr_body_up = c[-1] > o[-1]
    if curr_body_up and not prev_body_up and c[-1] >= o[-2] and o[-1] <= c[-2]:
        out.append("Avalement haussier (bullish engulfing)")
    if not curr_body_up and prev_body_up and o[-1] >= c[-2] and c[-1] <= o[-2]:
        out.append("Avalement baissier (bearish engulfing)")
    return out


def _chart_patterns(df: pd.DataFrame, lookback: int = 40) -> List[str]:
    out: List[str] = []
    if len(df) < lookback:
        return out
    window = df["close"].tail(lookback)
    highs = df["high"].tail(lookback)
    lows = df["low"].tail(lookback)

    # Breakout: close breaks above the prior range high / below range low.
    prior_high = highs.iloc[:-1].max()
    prior_low = lows.iloc[:-1].min()
    last_close = window.iloc[-1]
    if last_close > prior_high:
        out.append("Cassure de résistance (breakout haussier)")
    elif last_close < prior_low:
        out.append("Cassure de support (breakdown baissier)")

    # Simple higher-highs / lower-lows structure.
    first_half = window.iloc[: lookback // 2].mean()
    second_half = window.iloc[lookback // 2 :].mean()
    if second_half > first_half * 1.01:
        out.append("Structure de sommets/creux ascendants")
    elif second_half < first_half * 0.99:
        out.append("Structure de sommets/creux descendants")
    return out


def _historical_analog(df: pd.DataFrame, window: int = 10, horizon: int = 5) -> tuple[float, int]:
    """Find past windows whose normalised shape resembles the most recent one
    and measure how often price rose ``horizon`` bars later.

    This is a lightweight nearest-neighbour analog (quant style) rather than a
    heavy model, so it runs instantly with no training step.
    """
    closes = df["close"].to_numpy()
    n = len(closes)
    if n < window + horizon + 30:
        return 0.5, 0

    def normalize(seg: np.ndarray) -> np.ndarray:
        base = seg[0]
        if base == 0:
            return seg - seg.mean()
        return seg / base - 1.0

    current = normalize(closes[-window:])
    distances = []
    for start in range(0, n - window - horizon):
        seg = normalize(closes[start : start + window])
        dist = float(np.sqrt(np.sum((seg - current) ** 2)))
        future_ret = closes[start + window + horizon - 1] / closes[start + window - 1] - 1.0
        distances.append((dist, future_ret))

    distances.sort(key=lambda x: x[0])
    k = min(20, len(distances))
    nearest = distances[:k]
    up = sum(1 for _, ret in nearest if ret > 0)
    return up / k, k


def detect(df: pd.DataFrame) -> PatternResult:
    detected = _candle_patterns(df) + _chart_patterns(df)
    up_rate, sample = _historical_analog(df)
    return PatternResult(detected=detected, historical_up_rate=round(up_rate, 3), sample_size=sample)
