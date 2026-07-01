"""Position sizing and risk calculations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskResult:
    account_balance: float
    risk_pct: float
    risk_amount: float
    entry: float
    stop_loss: float
    stop_distance: float
    stop_distance_pct: float
    position_size: float      # units of the asset
    position_value: float     # notional in account currency
    risk_reward: float


def position_size(
    account_balance: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
    target: float | None = None,
) -> RiskResult:
    """Compute position size so that a stop-out loses ``risk_pct`` of the account.

    Raises ValueError on invalid inputs.
    """
    if account_balance <= 0:
        raise ValueError("Le capital doit être positif.")
    if not 0 < risk_pct <= 100:
        raise ValueError("Le risque doit être compris entre 0 et 100%.")
    if entry <= 0 or stop_loss <= 0:
        raise ValueError("Le prix d'entrée et le stop doivent être positifs.")
    stop_distance = abs(entry - stop_loss)
    if stop_distance <= 0:
        raise ValueError("Le stop-loss ne peut pas être égal au prix d'entrée.")

    risk_amount = account_balance * (risk_pct / 100.0)
    size = risk_amount / stop_distance
    position_value = size * entry

    rr = 0.0
    if target is not None and target > 0:
        reward = abs(target - entry)
        rr = round(reward / stop_distance, 2) if stop_distance else 0.0

    return RiskResult(
        account_balance=account_balance,
        risk_pct=risk_pct,
        risk_amount=round(risk_amount, 2),
        entry=entry,
        stop_loss=stop_loss,
        stop_distance=stop_distance,
        stop_distance_pct=round(stop_distance / entry * 100, 2),
        position_size=round(size, 8),
        position_value=round(position_value, 2),
        risk_reward=rr,
    )
