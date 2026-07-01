"""Technical analysis: turn enriched candles into a structured assessment."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

from . import indicators


@dataclass
class TechnicalAssessment:
    trend: str  # "haussière" / "baissière" / "neutre"
    trend_strength: float  # 0-100 (ADX based)
    bias: int  # -1 short, 0 neutral, +1 long
    rsi: float
    macd_hist: float
    atr_pct: float  # ATR relative to price (%)
    volume_ratio: float  # last volume / avg volume
    last_price: float
    signals: List[str] = field(default_factory=list)
    bullish_points: int = 0
    bearish_points: int = 0

    @property
    def confirmation_ratio(self) -> float:
        total = self.bullish_points + self.bearish_points
        if total == 0:
            return 0.0
        dominant = max(self.bullish_points, self.bearish_points)
        return dominant / total


def analyze(df: pd.DataFrame) -> TechnicalAssessment:
    """Compute a technical assessment from an OHLCV dataframe."""
    enriched = indicators.enrich(df)
    last = enriched.iloc[-1]
    price = float(last["close"])

    bullish: List[str] = []
    bearish: List[str] = []

    # --- Trend via EMA stack -------------------------------------------------
    ema20, ema50, ema200 = last.get("ema20"), last.get("ema50"), last.get("ema200")
    if not np.isnan(ema20) and not np.isnan(ema50):
        if ema20 > ema50:
            bullish.append("EMA20 au-dessus de l'EMA50 (momentum haussier)")
        else:
            bearish.append("EMA20 sous l'EMA50 (momentum baissier)")
    if not np.isnan(ema200):
        if price > ema200:
            bullish.append("Prix au-dessus de l'EMA200 (tendance de fond haussière)")
        else:
            bearish.append("Prix sous l'EMA200 (tendance de fond baissière)")

    # --- ADX (trend strength) ------------------------------------------------
    adx_val = float(last.get("adx", 0.0) or 0.0)

    # --- RSI -----------------------------------------------------------------
    rsi_val = float(last.get("rsi", 50.0))
    if rsi_val < 30:
        bullish.append(f"RSI en survente ({rsi_val:.0f})")
    elif rsi_val > 70:
        bearish.append(f"RSI en surachat ({rsi_val:.0f})")
    elif rsi_val >= 50:
        bullish.append(f"RSI > 50 ({rsi_val:.0f})")
    else:
        bearish.append(f"RSI < 50 ({rsi_val:.0f})")

    # --- MACD ----------------------------------------------------------------
    macd_hist = float(last.get("macd_hist", 0.0) or 0.0)
    if macd_hist > 0:
        bullish.append("Histogramme MACD positif")
    elif macd_hist < 0:
        bearish.append("Histogramme MACD négatif")

    # --- Stochastic ----------------------------------------------------------
    stoch_k = float(last.get("stoch_k", 50.0))
    if stoch_k < 20:
        bullish.append("Stochastique en survente")
    elif stoch_k > 80:
        bearish.append("Stochastique en surachat")

    # --- Bollinger position --------------------------------------------------
    bb_upper, bb_lower = last.get("bb_upper"), last.get("bb_lower")
    if not np.isnan(bb_lower) and price <= bb_lower:
        bullish.append("Prix sur la bande de Bollinger inférieure")
    elif not np.isnan(bb_upper) and price >= bb_upper:
        bearish.append("Prix sur la bande de Bollinger supérieure")

    # --- Volume --------------------------------------------------------------
    vol = float(last.get("volume", 0.0) or 0.0)
    vol_avg = float(last.get("vol_sma20", 0.0) or 0.0)
    volume_ratio = (vol / vol_avg) if vol_avg > 0 else 1.0

    # --- ATR (volatility) ----------------------------------------------------
    atr_val = float(last.get("atr", 0.0) or 0.0)
    atr_pct = (atr_val / price * 100) if price > 0 else 0.0

    bias = 0
    if len(bullish) > len(bearish):
        bias = 1
    elif len(bearish) > len(bullish):
        bias = -1

    if bias > 0:
        trend = "haussière"
    elif bias < 0:
        trend = "baissière"
    else:
        trend = "neutre"

    signals = (bullish if bias >= 0 else bearish) or bullish + bearish

    return TechnicalAssessment(
        trend=trend,
        trend_strength=round(adx_val, 1),
        bias=bias,
        rsi=round(rsi_val, 1),
        macd_hist=round(macd_hist, 6),
        atr_pct=round(atr_pct, 2),
        volume_ratio=round(volume_ratio, 2),
        last_price=price,
        signals=signals[:6],
        bullish_points=len(bullish),
        bearish_points=len(bearish),
    )
