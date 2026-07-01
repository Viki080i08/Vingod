"""Risk profile tuning parameters that steer the AI recommendations.

Each profile defines how the engine selects a pick for a given match:

* ``min_prob``      minimum estimated probability accepted for a selection
* ``min_odds`` /
  ``max_odds``      odds band the profile is comfortable with
* ``value_weight``  how strongly expected value (odds * prob) is favoured over
                    raw probability when ranking opportunities
* ``combo_size``    default number of legs in an AI-generated combo
"""

from __future__ import annotations

from ..db.base import RiskProfile

PROFILE_TUNING = {
    RiskProfile.SECURE: {
        "min_prob": 0.55,
        "min_odds": 1.20,
        "max_odds": 1.95,
        "value_weight": 0.20,
        "combo_size": 2,
        "confidence_floor": 60.0,
    },
    RiskProfile.BALANCED: {
        "min_prob": 0.42,
        "min_odds": 1.55,
        "max_odds": 2.80,
        "value_weight": 0.55,
        "combo_size": 3,
        "confidence_floor": 50.0,
    },
    RiskProfile.RISKY: {
        "min_prob": 0.28,
        "min_odds": 2.10,
        "max_odds": 8.00,
        "value_weight": 0.85,
        "combo_size": 4,
        "confidence_floor": 40.0,
    },
}

PROFILE_DESCRIPTIONS = {
    RiskProfile.SECURE: (
        "🟢 *Sécurisé* — On privilégie les pronostics avec la plus forte "
        "probabilité de réussite. Cotes faibles, mais régularité maximale."
    ),
    RiskProfile.BALANCED: (
        "🟡 *Équilibré* — Le bon compromis entre sécurité et rendement. "
        "L'IA cherche les meilleures valeurs avec un risque maîtrisé."
    ),
    RiskProfile.RISKY: (
        "🔴 *Risqué* — On accepte plus de variance pour viser des cotes "
        "élevées et un rendement potentiel supérieur."
    ),
}


def describe_profile(profile: str) -> str:
    return PROFILE_DESCRIPTIONS.get(profile, PROFILE_DESCRIPTIONS[RiskProfile.BALANCED])


def tuning_for(profile: str) -> dict:
    return PROFILE_TUNING.get(profile, PROFILE_TUNING[RiskProfile.BALANCED])
