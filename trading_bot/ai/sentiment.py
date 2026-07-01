"""News / text sentiment analysis using VADER (offline, no API key).

VADER is tuned for social/financial short text. We additionally inject a small
finance-specific lexicon so words like "bullish", "rally", "hawkish" carry the
right polarity.
"""
from __future__ import annotations

from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Domain specific words VADER does not know well (score range roughly -4..+4).
_FINANCE_LEXICON = {
    "bullish": 2.5,
    "bearish": -2.5,
    "rally": 2.0,
    "rallies": 2.0,
    "surge": 2.2,
    "surges": 2.2,
    "soar": 2.5,
    "soars": 2.5,
    "plunge": -2.5,
    "plunges": -2.5,
    "crash": -3.0,
    "crashes": -3.0,
    "selloff": -2.2,
    "sell-off": -2.2,
    "downturn": -1.8,
    "rebound": 1.8,
    "breakout": 1.8,
    "breakdown": -1.8,
    "outperform": 2.0,
    "underperform": -2.0,
    "upgrade": 1.8,
    "downgrade": -1.8,
    "hawkish": -1.2,
    "dovish": 1.2,
    "recession": -2.5,
    "default": -2.0,
    "bankruptcy": -3.0,
    "hack": -2.5,
    "exploit": -2.0,
    "adoption": 1.5,
    "partnership": 1.3,
    "record": 1.2,
    "all-time": 1.2,
    "beat": 1.5,
    "beats": 1.5,
    "miss": -1.5,
    "misses": -1.5,
}


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    analyzer = SentimentIntensityAnalyzer()
    analyzer.lexicon.update(_FINANCE_LEXICON)
    return analyzer


def score_text(text: str) -> float:
    """Return a compound sentiment score in the range [-1, 1]."""
    if not text or not text.strip():
        return 0.0
    return round(_analyzer().polarity_scores(text)["compound"], 4)


def label(score: float) -> str:
    if score >= 0.35:
        return "Très positif"
    if score >= 0.1:
        return "Positif"
    if score <= -0.35:
        return "Très négatif"
    if score <= -0.1:
        return "Négatif"
    return "Neutre"
