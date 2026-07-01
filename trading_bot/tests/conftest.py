"""Shared test fixtures: synthetic OHLCV data (no network required)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(prices: np.ndarray) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(prices), freq="1h", tz="UTC")
    high = prices * (1 + np.abs(np.random.default_rng(1).normal(0, 0.003, len(prices))))
    low = prices * (1 - np.abs(np.random.default_rng(2).normal(0, 0.003, len(prices))))
    open_ = np.concatenate([[prices[0]], prices[:-1]])
    volume = np.abs(np.random.default_rng(3).normal(1000, 100, len(prices)))
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": prices, "volume": volume},
        index=idx,
    )


@pytest.fixture
def uptrend_df() -> pd.DataFrame:
    n = 300
    trend = np.linspace(100, 200, n)
    noise = np.random.default_rng(42).normal(0, 1.5, n)
    prices = trend + noise
    return _make_ohlcv(prices)


@pytest.fixture
def downtrend_df() -> pd.DataFrame:
    n = 300
    trend = np.linspace(200, 100, n)
    noise = np.random.default_rng(7).normal(0, 1.5, n)
    prices = trend + noise
    return _make_ohlcv(prices)


@pytest.fixture
def flat_df() -> pd.DataFrame:
    n = 300
    prices = 150 + np.random.default_rng(11).normal(0, 1.0, n)
    return _make_ohlcv(prices)
