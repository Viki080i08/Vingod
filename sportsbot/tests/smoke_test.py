"""Offline smoke test: exercises DB, provider, AI engine, sync and tips.

Run with:  python -m tests.smoke_test
It uses the demo provider and a temporary SQLite database, so it needs neither
a Telegram token nor a Postgres server.
"""

from __future__ import annotations

import os
import tempfile

# Configure an isolated environment BEFORE importing the package.
_tmp = tempfile.mkdtemp(prefix="pronoia-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["TELEGRAM_BOT_TOKEN"] = "0:TEST"
os.environ["DATA_PROVIDER"] = "demo"
os.environ["LOG_LEVEL"] = "WARNING"


def main() -> None:
    from sportsbot.ai.engine import (
        analyse_match,
        elo_expected_score,
        pick_for_profile,
        score_matrix,
        update_elo,
    )
    from sportsbot.ai.profiles import PROFILE_TUNING
    from sportsbot.db import init_db, session_scope
    from sportsbot.db import repo
    from sportsbot.db.base import RiskProfile
    from sportsbot.providers.demo import DemoProvider
    from sportsbot.providers.base import ProviderTeam
    from sportsbot.services.sync import sync_fixtures_and_analyse, update_results_and_settle
    from sportsbot.services.tips import best_opportunities, build_ai_combo, generate_broadcast_tips

    print("== init db ==")
    init_db()

    print("== engine internals (Elo + Dixon-Coles) ==")
    # Score matrix must be a normalised probability distribution.
    matrix = score_matrix(1.6, 1.1)
    total_mass = sum(sum(row) for row in matrix)
    assert abs(total_mass - 1.0) < 1e-6, f"score matrix must sum to 1 (got {total_mass})"
    # Elo expected score: stronger + home team should be clearly favoured.
    e = elo_expected_score(1900, 1600)
    assert e > 0.75, f"strong home side expected score too low: {e}"
    # Elo learning: an underdog winning gains rating; favourite loses some.
    new_h, new_a = update_elo(1500, 1800, home_goals=3, away_goals=0)
    assert new_h > 1500 and new_a < 1800, "Elo must move toward the actual result"
    print(f"   score-matrix mass={total_mass:.6f}; elo E(home)={e:.2f}; "
          f"upset update 1500->{new_h:.1f}, 1800->{new_a:.1f}")

    print("== engine sanity ==")
    home = ProviderTeam(name="Strong FC", attack_rating=1.6, defense_rating=1.5,
                        goals_for_avg=2.1, goals_against_avg=0.8, recent_form="WWWDW",
                        home_strength=1.25, momentum=0.5)
    away = ProviderTeam(name="Weak United", attack_rating=0.8, defense_rating=0.85,
                        goals_for_avg=0.9, goals_against_avg=1.8, recent_form="LLDLL",
                        away_strength=0.85, momentum=-0.4, key_absences=2)
    result = analyse_match(home, away, {"home_wins": 4, "draws": 1, "away_wins": 0})
    total = result.prob_home + result.prob_draw + result.prob_away
    assert 0.99 <= total <= 1.01, f"probabilities must sum to 1 (got {total})"
    assert result.prob_home > result.prob_away, "stronger home team should be favourite"
    assert 0 < result.recommended_odds, "odds must be positive"
    assert 35 <= result.confidence <= 95
    print(f"   probs H/D/A = {result.prob_home:.2f}/{result.prob_draw:.2f}/{result.prob_away:.2f}")
    print(f"   pick={result.recommended_pick} odds={result.recommended_odds} "
          f"conf={result.confidence} risk={result.risk_level} value={result.value_score}")
    print(f"   explanation:\n   " + result.explanation.replace("\n", "\n   "))

    print("== profile picks ==")
    for profile in RiskProfile.ALL:
        choice = pick_for_profile(result, profile)
        print(f"   {profile:9s} -> {choice}")

    print("== demo provider fixtures ==")
    provider = DemoProvider()
    fixtures = provider.fetch_fixtures(5)
    print(f"   {len(fixtures)} fixtures generated over 5 days")
    assert len(fixtures) > 0

    print("== sync + analyse ==")
    summary = sync_fixtures_and_analyse()
    print(f"   {summary}")
    assert summary["analysed"] > 0

    print("== best opportunities per profile ==")
    with session_scope() as session:
        for profile in RiskProfile.ALL:
            opps = best_opportunities(session, profile, limit=3)
            print(f"   {profile:9s}: {len(opps)} opportunities")
            for o in opps:
                print(f"      {o.match.home_name} vs {o.match.away_name} -> "
                      f"{o.pick} @ {o.odds} (p={o.probability:.2f}, val={o.value:.2f})")

    print("== AI combo ==")
    with session_scope() as session:
        combo = build_ai_combo(session, RiskProfile.BALANCED)
        if combo:
            print(f"   combo legs={len(combo.selections)} odds={combo.total_odds} "
                  f"prob={combo.combined_probability:.3f}")
            assert len(combo.selections) >= 2

    print("== broadcast tips ==")
    with session_scope() as session:
        tips = generate_broadcast_tips(session, limit_per_profile=3)
        for profile, opps in tips.items():
            print(f"   {profile}: {len(opps)} tips recorded")

    print("== subscription lifecycle ==")
    with session_scope() as session:
        user, _ = repo.get_or_create_user(session, telegram_id=999001, first_name="Tester")
        assert not user.has_active_subscription
        repo.activate_subscription(session, user, days=30, amount=19.99, currency="EUR")
        assert user.has_active_subscription
        print(f"   activated until {user.subscription_expiry}")
        history = repo.payment_history(session, user.id)
        assert len(history) == 1

    print("== results update + settlement ==")
    res = update_results_and_settle()
    print(f"   {res}")

    print("== stats ==")
    with session_scope() as session:
        stats = repo.tip_stats(session)
        print(f"   global: {stats}")

    print("\nALL SMOKE TESTS PASSED ✅")


if __name__ == "__main__":
    main()
