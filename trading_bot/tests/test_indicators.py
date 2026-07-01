import numpy as np
import pandas as pd

from trading_bot.ai import indicators


def test_rsi_bounds(uptrend_df):
    r = indicators.rsi(uptrend_df["close"])
    valid = r.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()
    # A steady uptrend should push RSI above the midline on average.
    assert valid.tail(50).mean() > 50


def test_ema_follows_price(uptrend_df):
    e = indicators.ema(uptrend_df["close"], 20)
    assert e.dropna().iloc[-1] > e.dropna().iloc[0]


def test_macd_shapes(uptrend_df):
    line, signal, hist = indicators.macd(uptrend_df["close"])
    assert len(line) == len(uptrend_df)
    assert len(signal) == len(uptrend_df)
    assert len(hist) == len(uptrend_df)


def test_bollinger_ordering(flat_df):
    upper, middle, lower = indicators.bollinger_bands(flat_df["close"])
    valid = upper.notna() & middle.notna() & lower.notna()
    assert (upper[valid] >= middle[valid]).all()
    assert (middle[valid] >= lower[valid]).all()


def test_atr_positive(uptrend_df):
    a = indicators.atr(uptrend_df["high"], uptrend_df["low"], uptrend_df["close"])
    assert (a.dropna() >= 0).all()


def test_enrich_adds_columns(uptrend_df):
    enriched = indicators.enrich(uptrend_df)
    for col in ["ema20", "ema50", "rsi", "macd", "bb_upper", "atr", "adx", "obv"]:
        assert col in enriched.columns
