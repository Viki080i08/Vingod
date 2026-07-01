import pytest

from trading_bot.ai import sentiment
from trading_bot.bot.security import RateLimiter
from trading_bot.data import symbols
from trading_bot.models import AssetClass
from trading_bot.risk import position_size


def test_position_size_basic():
    r = position_size(account_balance=1000, risk_pct=1, entry=30000, stop_loss=29000, target=33000)
    # Risk 1% of 1000 = 10; stop distance 1000 -> size 0.01
    assert r.risk_amount == 10.0
    assert abs(r.position_size - 0.01) < 1e-9
    assert r.risk_reward == 3.0


def test_position_size_rejects_bad_input():
    with pytest.raises(ValueError):
        position_size(0, 1, 100, 90)
    with pytest.raises(ValueError):
        position_size(1000, 1, 100, 100)  # stop == entry


def test_symbol_classification():
    assert symbols.classify("BTCUSDT") == AssetClass.CRYPTO
    assert symbols.classify("ETHUSDC") == AssetClass.CRYPTO
    assert symbols.classify("EURUSD") == AssetClass.FOREX
    assert symbols.classify("AAPL") == AssetClass.STOCK
    assert symbols.classify("US500") == AssetClass.INDEX


def test_normalize():
    assert symbols.normalize("btc/usdt") == "BTCUSDT"
    assert symbols.normalize(" eur-usd ") == "EURUSD"


def test_rate_limiter_blocks():
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    uid = 123
    assert limiter.check(uid)
    assert limiter.check(uid)
    assert limiter.check(uid)
    assert not limiter.check(uid)  # 4th call blocked


def test_sentiment_polarity():
    pos = sentiment.score_text("Bitcoin rallies to record high on bullish adoption news")
    neg = sentiment.score_text("Market crashes as recession fears trigger massive selloff")
    assert pos > 0
    assert neg < 0
    assert -1.0 <= pos <= 1.0
