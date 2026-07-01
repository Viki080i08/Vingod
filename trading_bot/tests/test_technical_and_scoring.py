from trading_bot.ai import patterns, scoring, technical
from trading_bot.ai.ml_model import direction_model
from trading_bot.models import ScoreBreakdown


def test_uptrend_is_bullish(uptrend_df):
    assessment = technical.analyze(uptrend_df)
    assert assessment.bias >= 0
    assert assessment.trend in {"haussière", "neutre"}
    assert 0 <= assessment.rsi <= 100


def test_downtrend_is_bearish(downtrend_df):
    assessment = technical.analyze(downtrend_df)
    assert assessment.bias <= 0


def test_score_within_bounds(uptrend_df):
    tech = technical.analyze(uptrend_df)
    pat = patterns.detect(uptrend_df)
    ml = direction_model.predict("TEST:1h", uptrend_df)
    breakdown = scoring.compute_score(tech, pat, ml, sentiment=0.2)
    total = breakdown.total()
    assert 0 <= total <= 100


def test_probability_capped(uptrend_df):
    tech = technical.analyze(uptrend_df)
    pat = patterns.detect(uptrend_df)
    ml = direction_model.predict("TEST2:1h", uptrend_df)
    breakdown = scoring.compute_score(tech, pat, ml, sentiment=1.0)
    prob = scoring.estimate_probability(breakdown.total(), ml, tech)
    assert 35.0 <= prob <= 85.0


def test_score_breakdown_total():
    b = ScoreBreakdown(10, 10, 10, 10, 10, 10)
    assert b.total() == 60.0


def test_patterns_detect_runs(uptrend_df):
    result = patterns.detect(uptrend_df)
    assert 0.0 <= result.historical_up_rate <= 1.0
    assert result.sample_size >= 0
