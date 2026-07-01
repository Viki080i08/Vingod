"""The PronoIA analysis engine — 100% maison, sans API sportive.

This is a fully self-contained predictive model. It does NOT depend on any
external sports API. It combines two complementary, well-established football
modelling techniques and blends them for robustness:

  1. An **Elo rating** system (like chess / FiveThirtyEight) that measures each
     team's strength on a single scale and learns continuously from results.
  2. A **bivariate Poisson goal model with the Dixon-Coles correction**, which
     is the academic standard for football score prediction and notably fixes
     the under-estimation of low scores (0-0, 1-0, 0-1, 1-1).

On top of these it layers the contextual signals required by the brief:
    * recent form              * home / away factor
    * previous results          * key absences (injuries / suspensions)
    * offensive / defensive     * recent trends (momentum)
    * head-to-head history

For each match it outputs a probability distribution, fair & market odds, a
confidence score, a risk level, an expected-value score and a fully
explainable analysis in French. Everything is pure-Python, deterministic and
fast — no heavy ML dependency, no paid data feed.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..db.base import Pick
from .profiles import tuning_for

# --------------------------------------------------------------------------- #
# Tunable model constants
# --------------------------------------------------------------------------- #
LEAGUE_AVG_GOALS = 1.35           # average goals per team per match
HOME_ADVANTAGE = 1.18             # multiplier applied to home expected goals
AWAY_PENALTY = 0.96               # multiplier applied to away expected goals
MAX_GOALS = 8                     # truncation of the Poisson score matrix
BOOKMAKER_MARGIN = 0.06           # 6% overround baked into fair odds
ABSENCE_ATTACK_PENALTY = 0.045    # per key absence
ABSENCE_DEFENSE_PENALTY = 0.04    # per key absence (concedes more)
MOMENTUM_SWING = 0.12             # max +/- expected-goal swing from momentum

# --- Elo model ---
DEFAULT_ELO = 1500.0
HOME_FIELD_ELO = 65.0             # Elo points granted by home advantage
ELO_TO_GOALS = 0.0040             # goal supremacy per Elo point of difference
ELO_BLEND = 0.50                  # weight of the Elo signal vs the goal model
ELO_K = 24.0                      # Elo update speed when learning from results

# --- Dixon-Coles low-score correlation ---
DIXON_COLES_RHO = -0.08


@dataclass
class TeamSnapshot:
    """Lightweight, engine-friendly view of a team's stats."""

    name: str
    attack_rating: float = 1.0
    defense_rating: float = 1.0
    goals_for_avg: float = LEAGUE_AVG_GOALS
    goals_against_avg: float = LEAGUE_AVG_GOALS
    recent_form: str = ""
    home_strength: float = 1.0
    away_strength: float = 1.0
    key_absences: int = 0
    momentum: float = 0.0
    elo: float = DEFAULT_ELO

    @classmethod
    def from_team(cls, team) -> "TeamSnapshot":
        return cls(
            name=team.name,
            attack_rating=team.attack_rating or 1.0,
            defense_rating=team.defense_rating or 1.0,
            goals_for_avg=team.goals_for_avg or LEAGUE_AVG_GOALS,
            goals_against_avg=team.goals_against_avg or LEAGUE_AVG_GOALS,
            recent_form=team.recent_form or "",
            home_strength=team.home_strength or 1.0,
            away_strength=team.away_strength or 1.0,
            key_absences=team.key_absences or 0,
            momentum=team.momentum or 0.0,
            elo=getattr(team, "elo", None) or DEFAULT_ELO,
        )


@dataclass
class AnalysisResult:
    prob_home: float
    prob_draw: float
    prob_away: float
    expected_home_goals: float
    expected_away_goals: float
    odds_home: float
    odds_draw: float
    odds_away: float
    recommended_pick: str
    recommended_odds: float
    confidence: float
    risk_level: str
    value_score: float
    explanation: str
    key_factors: Dict[str, str] = field(default_factory=dict)

    def prob_for(self, pick: str) -> float:
        return {
            Pick.HOME: self.prob_home,
            Pick.DRAW: self.prob_draw,
            Pick.AWAY: self.prob_away,
        }.get(pick, 0.0)

    def odds_for(self, pick: str) -> float:
        return {
            Pick.HOME: self.odds_home,
            Pick.DRAW: self.odds_draw,
            Pick.AWAY: self.odds_away,
        }.get(pick, 1.0)


# --------------------------------------------------------------------------- #
# Core maths
# --------------------------------------------------------------------------- #
def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _form_score(form: str) -> float:
    """Convert a form string like 'WWDLW' into a -1..+1 momentum-style score."""
    if not form:
        return 0.0
    weights = {"W": 1.0, "D": 0.0, "L": -1.0}
    total = 0.0
    weight_sum = 0.0
    # More recent matches (left side) weigh more.
    for i, ch in enumerate(form.upper()[:6]):
        w = 1.0 / (i + 1)
        total += weights.get(ch, 0.0) * w
        weight_sum += w
    return total / weight_sum if weight_sum else 0.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _expected_goals(
    attacker: TeamSnapshot,
    defender: TeamSnapshot,
    is_home: bool,
) -> float:
    """Estimate expected goals for ``attacker`` against ``defender``."""
    # Blend the explicit attack/defense ratings with observed goal averages.
    attack = (attacker.attack_rating + attacker.goals_for_avg / LEAGUE_AVG_GOALS) / 2
    # defense_rating > 1 means a strong defense (concedes less) -> divide.
    defense = (defender.defense_rating + LEAGUE_AVG_GOALS / max(defender.goals_against_avg, 0.4)) / 2

    exp = LEAGUE_AVG_GOALS * attack / max(defense, 0.4)

    # Home / away adjustment.
    if is_home:
        exp *= HOME_ADVANTAGE * _clamp(attacker.home_strength, 0.6, 1.6)
    else:
        exp *= AWAY_PENALTY * _clamp(attacker.away_strength, 0.6, 1.6)

    # Momentum + recent form swing.
    form = _form_score(attacker.recent_form)
    combined_trend = _clamp((attacker.momentum + form) / 2, -1.0, 1.0)
    exp *= 1.0 + MOMENTUM_SWING * combined_trend

    # Key absences weaken the attack and the opponent's absences help.
    exp *= max(0.55, 1.0 - ABSENCE_ATTACK_PENALTY * attacker.key_absences)
    exp *= 1.0 + ABSENCE_DEFENSE_PENALTY * defender.key_absences

    return _clamp(exp, 0.15, 4.5)


def _dixon_coles_tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles correction factor for low-scoring correlated outcomes."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(exp_home: float, exp_away: float) -> list[list[float]]:
    """Full (Dixon-Coles corrected) probability matrix of exact scores."""
    home_pmf = [_poisson_pmf(i, exp_home) for i in range(MAX_GOALS + 1)]
    away_pmf = [_poisson_pmf(j, exp_away) for j in range(MAX_GOALS + 1)]
    matrix = [[0.0] * (MAX_GOALS + 1) for _ in range(MAX_GOALS + 1)]
    total = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = home_pmf[i] * away_pmf[j] * _dixon_coles_tau(
                i, j, exp_home, exp_away, DIXON_COLES_RHO
            )
            p = max(p, 0.0)
            matrix[i][j] = p
            total += p
    if total > 0:
        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                matrix[i][j] /= total
    return matrix


def _outcome_probabilities(exp_home: float, exp_away: float) -> Tuple[float, float, float]:
    """1X2 probabilities from the Dixon-Coles corrected score matrix."""
    matrix = score_matrix(exp_home, exp_away)
    p_home = p_draw = p_away = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = matrix[i][j]
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    total = p_home + p_draw + p_away
    if total <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return p_home / total, p_draw / total, p_away / total


def elo_expected_score(elo_home: float, elo_away: float) -> float:
    """Elo expected score for the home side (0..1), including home advantage."""
    diff = (elo_home + HOME_FIELD_ELO) - elo_away
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def _elo_goal_supremacy(elo_home: float, elo_away: float) -> float:
    """Convert an Elo difference into an expected home goal supremacy."""
    diff = (elo_home + HOME_FIELD_ELO) - elo_away
    return _clamp(diff * ELO_TO_GOALS, -2.6, 2.6)


def update_elo(elo_home: float, elo_away: float, home_goals: int, away_goals: int) -> Tuple[float, float]:
    """Return updated Elo ratings after a result (used for continuous learning).

    Uses a goal-difference multiplier so that heavy wins move ratings more,
    mirroring the FiveThirtyEight approach.
    """
    if home_goals > away_goals:
        actual = 1.0
    elif home_goals < away_goals:
        actual = 0.0
    else:
        actual = 0.5
    expected = elo_expected_score(elo_home, elo_away)
    margin = abs(home_goals - away_goals)
    multiplier = math.log(max(margin, 1) + 1.0)  # 0.69 for 1-goal, grows slowly
    change = ELO_K * multiplier * (actual - expected)
    return elo_home + change, elo_away - change


def _apply_head_to_head(
    probs: Tuple[float, float, float], h2h: Optional[dict]
) -> Tuple[float, float, float]:
    """Nudge probabilities with historical head-to-head dominance."""
    if not h2h:
        return probs
    hw = h2h.get("home_wins", 0)
    dr = h2h.get("draws", 0)
    aw = h2h.get("away_wins", 0)
    n = hw + dr + aw
    if n < 2:
        return probs
    weight = 0.15  # how much H2H influences the final number
    h2h_probs = (hw / n, dr / n, aw / n)
    blended = tuple(
        (1 - weight) * p + weight * hp for p, hp in zip(probs, h2h_probs)
    )
    total = sum(blended)
    return tuple(p / total for p in blended)  # type: ignore[return-value]


def _fair_odds(prob: float) -> float:
    prob = _clamp(prob, 0.001, 0.999)
    raw = 1.0 / prob
    # Apply a small bookmaker margin so odds look realistic.
    odds = raw * (1.0 - BOOKMAKER_MARGIN) + 1.0 * BOOKMAKER_MARGIN
    return round(max(odds, 1.01), 2)


def _market_deviation(home_name: str, away_name: str, outcome: str) -> float:
    """Deterministic bookmaker mispricing factor for an outcome.

    Real bookmakers never price exactly at the model's fair value. We simulate
    this with a stable, name-seeded factor in roughly [0.94, 1.16]. Factors
    above ~1.07 create genuine positive expected-value spots that the riskier
    profiles can exploit, while secure profiles stick to high-probability picks.
    """
    seed = hashlib.sha256(f"{home_name}|{away_name}|{outcome}".encode()).hexdigest()
    unit = int(seed[:8], 16) / 0xFFFFFFFF  # 0..1
    return 0.94 + unit * 0.22


def _market_odds(prob: float, home_name: str, away_name: str, outcome: str) -> float:
    odds = _fair_odds(prob) * _market_deviation(home_name, away_name, outcome)
    return round(max(odds, 1.01), 2)


def _risk_level(prob: float) -> str:
    if prob >= 0.58:
        return "low"
    if prob >= 0.44:
        return "medium"
    return "high"


def _confidence(probs: Tuple[float, float, float], data_quality: float) -> float:
    """Confidence based on how separated the top outcome is, scaled 40..95."""
    ordered = sorted(probs, reverse=True)
    separation = ordered[0] - ordered[1]
    raw = 45 + ordered[0] * 45 + separation * 40
    raw *= 0.85 + 0.15 * data_quality
    return round(_clamp(raw, 35.0, 95.0), 1)


RISK_LABELS = {"low": "🟢 Faible", "medium": "🟡 Modéré", "high": "🔴 Élevé"}


def _build_explanation(
    home: TeamSnapshot,
    away: TeamSnapshot,
    probs: Tuple[float, float, float],
    exp_home: float,
    exp_away: float,
    pick: str,
    h2h: Optional[dict],
) -> Tuple[str, Dict[str, str]]:
    p_home, p_draw, p_away = probs
    factors: Dict[str, str] = {}
    lines = []

    favourite = home.name if p_home >= p_away else away.name
    lines.append(
        f"Probabilités estimées — {home.name} {p_home*100:.0f}% / "
        f"Nul {p_draw*100:.0f}% / {away.name} {p_away*100:.0f}%."
    )
    lines.append(
        f"Score attendu (xG) : {exp_home:.1f} - {exp_away:.1f}, "
        f"avantage à *{favourite}*."
    )
    factors["Force (Elo)"] = (
        f"{home.name} {home.elo:.0f} vs {away.name} {away.elo:.0f} "
        f"(écart {home.elo - away.elo:+.0f})"
    )

    # Form
    fh, fa = _form_score(home.recent_form), _form_score(away.recent_form)
    if home.recent_form or away.recent_form:
        factors["Forme récente"] = (
            f"{home.name} [{home.recent_form or 'n/d'}] vs "
            f"{away.name} [{away.recent_form or 'n/d'}]"
        )
        if fh - fa > 0.25:
            lines.append(f"📈 {home.name} est en bien meilleure forme récente.")
        elif fa - fh > 0.25:
            lines.append(f"📈 {away.name} est en bien meilleure forme récente.")

    # Attack / defense
    factors["Attaque/Défense"] = (
        f"{home.name} att {home.attack_rating:.2f}/def {home.defense_rating:.2f} — "
        f"{away.name} att {away.attack_rating:.2f}/def {away.defense_rating:.2f}"
    )

    # Home advantage
    factors["Domicile/Extérieur"] = (
        f"{home.name} à domicile (force {home.home_strength:.2f}), "
        f"{away.name} à l'extérieur (force {away.away_strength:.2f})"
    )

    # Absences
    if home.key_absences or away.key_absences:
        factors["Absences"] = (
            f"{home.name}: {home.key_absences} absence(s) clé(s), "
            f"{away.name}: {away.key_absences} absence(s) clé(s)"
        )
        if home.key_absences > away.key_absences:
            lines.append(f"⚠️ {home.name} est fragilisé par des absences importantes.")
        elif away.key_absences > home.key_absences:
            lines.append(f"⚠️ {away.name} est fragilisé par des absences importantes.")

    # H2H
    if h2h:
        hw, dr, aw = h2h.get("home_wins", 0), h2h.get("draws", 0), h2h.get("away_wins", 0)
        if hw + dr + aw >= 2:
            factors["Confrontations directes"] = (
                f"{home.name} {hw} - {dr} nuls - {aw} {away.name}"
            )

    # Trend
    if abs(home.momentum) > 0.3 or abs(away.momentum) > 0.3:
        factors["Tendance"] = (
            f"Dynamique {home.name}: {home.momentum:+.2f}, "
            f"{away.name}: {away.momentum:+.2f}"
        )

    pick_label = {
        Pick.HOME: f"Victoire de {home.name}",
        Pick.DRAW: "Match nul",
        Pick.AWAY: f"Victoire de {away.name}",
    }[pick]
    lines.append(f"✅ Recommandation IA : *{pick_label}*.")

    return "\n".join(lines), factors


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def analyse_match(
    home_team,
    away_team,
    head_to_head: Optional[dict] = None,
) -> AnalysisResult:
    """Run the full analysis pipeline for a single match."""
    home = TeamSnapshot.from_team(home_team) if not isinstance(home_team, TeamSnapshot) else home_team
    away = TeamSnapshot.from_team(away_team) if not isinstance(away_team, TeamSnapshot) else away_team

    # Signal 1: goal model from attack/defense, form, home/away, absences.
    gm_home = _expected_goals(home, away, is_home=True)
    gm_away = _expected_goals(away, home, is_home=False)

    # Signal 2: Elo ratings translated into expected goals.
    supremacy = _elo_goal_supremacy(home.elo, away.elo)
    total_goals = _clamp(gm_home + gm_away, 1.4, 4.4)
    elo_home = _clamp((total_goals + supremacy) / 2, 0.15, 4.5)
    elo_away = _clamp((total_goals - supremacy) / 2, 0.15, 4.5)

    # Blend both signals for a robust expected-goals estimate.
    exp_home = _clamp(ELO_BLEND * elo_home + (1 - ELO_BLEND) * gm_home, 0.12, 4.6)
    exp_away = _clamp(ELO_BLEND * elo_away + (1 - ELO_BLEND) * gm_away, 0.12, 4.6)

    probs = _outcome_probabilities(exp_home, exp_away)
    probs = _apply_head_to_head(probs, head_to_head)
    p_home, p_draw, p_away = probs

    odds_home = _market_odds(p_home, home.name, away.name, Pick.HOME)
    odds_draw = _market_odds(p_draw, home.name, away.name, Pick.DRAW)
    odds_away = _market_odds(p_away, home.name, away.name, Pick.AWAY)

    # Default recommendation = most probable outcome.
    pick_probs = {Pick.HOME: p_home, Pick.DRAW: p_draw, Pick.AWAY: p_away}
    recommended_pick = max(pick_probs, key=pick_probs.get)
    recommended_prob = pick_probs[recommended_pick]
    recommended_odds = {
        Pick.HOME: odds_home,
        Pick.DRAW: odds_draw,
        Pick.AWAY: odds_away,
    }[recommended_pick]

    # Data quality: penalise missing form strings / default ratings.
    data_quality = 0.0
    data_quality += 0.4 if (home.recent_form and away.recent_form) else 0.0
    data_quality += 0.2 if head_to_head else 0.0
    data_quality += 0.2 if (home.attack_rating != 1.0 or away.attack_rating != 1.0) else 0.0
    data_quality += 0.2 if (home.elo != DEFAULT_ELO or away.elo != DEFAULT_ELO) else 0.0

    confidence = _confidence(probs, data_quality)
    risk_level = _risk_level(recommended_prob)
    value_score = round(recommended_prob * recommended_odds - 1.0, 3)

    explanation, factors = _build_explanation(
        home, away, probs, exp_home, exp_away, recommended_pick, head_to_head
    )

    return AnalysisResult(
        prob_home=round(p_home, 4),
        prob_draw=round(p_draw, 4),
        prob_away=round(p_away, 4),
        expected_home_goals=round(exp_home, 2),
        expected_away_goals=round(exp_away, 2),
        odds_home=odds_home,
        odds_draw=odds_draw,
        odds_away=odds_away,
        recommended_pick=recommended_pick,
        recommended_odds=recommended_odds,
        confidence=confidence,
        risk_level=risk_level,
        value_score=value_score,
        explanation=explanation,
        key_factors=factors,
    )


def pick_for_profile(result: AnalysisResult, profile: str) -> Optional[dict]:
    """Choose the best pick for a given risk profile.

    Returns ``None`` when no outcome matches the profile's tolerance, otherwise
    a dict with ``pick``, ``odds``, ``probability``, ``value`` and ``rationale``.
    """
    tuning = tuning_for(profile)
    candidates = []
    for pick in (Pick.HOME, Pick.DRAW, Pick.AWAY):
        prob = result.prob_for(pick)
        odds = result.odds_for(pick)
        if prob < tuning["min_prob"]:
            continue
        if not (tuning["min_odds"] <= odds <= tuning["max_odds"]):
            continue
        value = prob * odds - 1.0
        # Score blends raw probability and expected value per the profile.
        score = (1 - tuning["value_weight"]) * prob + tuning["value_weight"] * (value + 1) / 2
        candidates.append((score, pick, prob, odds, value))

    if not candidates:
        # Only the secure profile falls back to the safest high-probability
        # pick when nothing matches its odds band. Balanced/risky profiles
        # return None so they surface genuinely differentiated value bets.
        from ..db.base import RiskProfile

        if profile != RiskProfile.SECURE:
            return None
        if result.confidence < tuning["confidence_floor"]:
            return None
        if result.prob_for(result.recommended_pick) < 0.5:
            return None
        return {
            "pick": result.recommended_pick,
            "odds": result.recommended_odds,
            "probability": result.prob_for(result.recommended_pick),
            "value": round(
                result.prob_for(result.recommended_pick) * result.recommended_odds - 1, 3
            ),
            "rationale": "Choix le plus sûr disponible (forte probabilité).",
            "fallback": True,
        }

    candidates.sort(reverse=True)
    _, pick, prob, odds, value = candidates[0]
    return {
        "pick": pick,
        "odds": odds,
        "probability": round(prob, 4),
        "value": round(value, 3),
        "rationale": f"Sélection adaptée au profil {profile}.",
        "fallback": False,
    }
