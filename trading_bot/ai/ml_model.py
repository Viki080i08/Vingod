"""Lightweight machine-learning direction model.

For each asset we build engineered features from the enriched candles and train
a gradient-boosted classifier on the fly to predict whether price will be
higher ``horizon`` bars ahead. Models are cached in-memory per (symbol, tf).

This is intentionally self-contained (no pre-trained weights to ship) and
degrades gracefully to a neutral 0.5 probability when there is not enough data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from . import indicators

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "ret1",
    "ret3",
    "ret5",
    "rsi",
    "macd_hist",
    "adx",
    "stoch_k",
    "bb_pos",
    "ema_gap",
    "vol_ratio",
    "atr_pct",
]


@dataclass
class ModelPrediction:
    proba_up: float
    trained: bool
    accuracy: float
    samples: int


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    e = indicators.enrich(df)
    close = e["close"]
    feats = pd.DataFrame(index=e.index)
    feats["ret1"] = close.pct_change(1)
    feats["ret3"] = close.pct_change(3)
    feats["ret5"] = close.pct_change(5)
    feats["rsi"] = e["rsi"] / 100.0
    feats["macd_hist"] = e["macd_hist"] / close.replace(0, np.nan)
    feats["adx"] = e["adx"] / 100.0
    feats["stoch_k"] = e["stoch_k"] / 100.0
    bb_range = (e["bb_upper"] - e["bb_lower"]).replace(0, np.nan)
    feats["bb_pos"] = (close - e["bb_lower"]) / bb_range
    feats["ema_gap"] = (e["ema20"] - e["ema50"]) / close.replace(0, np.nan)
    feats["vol_ratio"] = e["volume"] / e["vol_sma20"].replace(0, np.nan)
    feats["atr_pct"] = e["atr"] / close.replace(0, np.nan)
    return feats


class DirectionModel:
    def __init__(self, horizon: int = 5) -> None:
        self.horizon = horizon
        self._cache: Dict[str, Tuple[GradientBoostingClassifier, float]] = {}

    def _train(self, df: pd.DataFrame) -> Optional[Tuple[GradientBoostingClassifier, float]]:
        feats = _build_features(df)
        target = (df["close"].shift(-self.horizon) > df["close"]).astype(int)
        data = feats.copy()
        data["target"] = target
        data = data.replace([np.inf, -np.inf], np.nan).dropna()
        if len(data) < 80:
            return None

        X = data[FEATURE_COLUMNS].to_numpy()
        y = data["target"].to_numpy()

        # Time-ordered split for an honest accuracy estimate.
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        if len(np.unique(y_train)) < 2:
            return None

        model = GradientBoostingClassifier(
            n_estimators=120, max_depth=3, learning_rate=0.05, subsample=0.9
        )
        model.fit(X_train, y_train)
        if len(X_test) >= 5:
            acc = float((model.predict(X_test) == y_test).mean())
        else:
            acc = float((model.predict(X_train) == y_train).mean())

        # Refit on the full dataset for the live prediction.
        model.fit(X, y)
        return model, round(acc, 3)

    def predict(self, symbol_key: str, df: pd.DataFrame) -> ModelPrediction:
        try:
            if symbol_key not in self._cache:
                trained = self._train(df)
                if trained is None:
                    return ModelPrediction(proba_up=0.5, trained=False, accuracy=0.0, samples=len(df))
                self._cache[symbol_key] = trained
            model, acc = self._cache[symbol_key]

            feats = _build_features(df).replace([np.inf, -np.inf], np.nan).ffill().dropna()
            if feats.empty:
                return ModelPrediction(proba_up=0.5, trained=True, accuracy=acc, samples=len(df))
            x = feats[FEATURE_COLUMNS].to_numpy()[-1:].astype(float)
            proba = float(model.predict_proba(x)[0][list(model.classes_).index(1)])
            return ModelPrediction(proba_up=round(proba, 3), trained=True, accuracy=acc, samples=len(df))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("ML prediction failed for %s: %s", symbol_key, exc)
            return ModelPrediction(proba_up=0.5, trained=False, accuracy=0.0, samples=len(df))

    def invalidate(self, symbol_key: Optional[str] = None) -> None:
        if symbol_key is None:
            self._cache.clear()
        else:
            self._cache.pop(symbol_key, None)


direction_model = DirectionModel()
