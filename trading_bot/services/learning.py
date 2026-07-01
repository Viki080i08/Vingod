"""Self-learning / performance tracking.

The engine records every signal it produces. This module periodically checks
open predictions against live prices, marks them win / loss / expired, and
exposes aggregate performance so the bot can report (and improve) over time.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from ..data.market_data import market_data_provider
from ..models import SignalDirection
from ..storage.database import get_db

logger = logging.getLogger(__name__)

# Predictions still open after this many hours are marked as expired.
_EXPIRY_HOURS = 24 * 14


async def resolve_open_predictions() -> Dict[str, int]:
    """Check open predictions and resolve those that hit target / stop / expiry."""
    db = get_db()
    open_preds = await db.open_predictions()
    counts = {"win": 0, "loss": 0, "expired": 0, "checked": 0}

    for pred in open_preds:
        counts["checked"] += 1
        symbol = pred["symbol"]
        try:
            quote = await market_data_provider.get_quote(symbol)
            price = quote.price
        except Exception as exc:  # pragma: no cover - network dependent
            logger.debug("Could not price %s for resolution: %s", symbol, exc)
            continue

        direction = pred["direction"]
        target = pred["target"]
        stop = pred["stop_loss"]
        outcome = None

        if direction == SignalDirection.LONG.value:
            if price >= target:
                outcome = "win"
            elif price <= stop:
                outcome = "loss"
        else:  # SHORT
            if price <= target:
                outcome = "win"
            elif price >= stop:
                outcome = "loss"

        if outcome is None:
            created = _parse_dt(pred["created_at"])
            if created and datetime.now(timezone.utc) - created > timedelta(hours=_EXPIRY_HOURS):
                outcome = "expired"

        if outcome:
            await db.resolve_prediction(pred["id"], outcome, price)
            counts[outcome] += 1
            logger.info("Prediction %s (%s) resolved: %s @ %s", pred["id"], symbol, outcome, price)

    return counts


async def get_performance() -> Dict[str, Any]:
    return await get_db().performance()


def _parse_dt(value: str):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
