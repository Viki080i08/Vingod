"""SQLite persistence for users, subscriptions, portfolio and predictions.

All blocking sqlite calls are dispatched to a worker thread so they never block
the asyncio event loop that runs the Telegram bot.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..models import TradingSignal

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    is_admin    INTEGER DEFAULT 0,
    is_blocked  INTEGER DEFAULT 0,
    alerts_on   INTEGER DEFAULT 0,
    created_at  TEXT,
    last_seen   TEXT
);

CREATE TABLE IF NOT EXISTS portfolio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    symbol      TEXT NOT NULL,
    quantity    REAL NOT NULL,
    entry_price REAL NOT NULL,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol         TEXT NOT NULL,
    direction      TEXT NOT NULL,
    entry          REAL NOT NULL,
    target         REAL NOT NULL,
    stop_loss      REAL NOT NULL,
    score          REAL NOT NULL,
    probability    REAL NOT NULL,
    timeframe      TEXT,
    created_at     TEXT NOT NULL,
    resolved       INTEGER DEFAULT 0,
    outcome        TEXT,             -- 'win' / 'loss' / 'expired'
    resolved_price REAL,
    resolved_at    TEXT,
    payload        TEXT              -- JSON snapshot of the signal
);

CREATE INDEX IF NOT EXISTS idx_predictions_open ON predictions(resolved);
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio(user_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    async def _run(self, fn, *args):
        return await asyncio.to_thread(fn, *args)

    def _init_sync(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    async def init(self) -> None:
        await self._run(self._init_sync)

    # ------------------------------------------------------------------ users
    def _upsert_user_sync(self, user_id: int, username: str, first_name: str, is_admin: bool) -> None:
        with self._connect() as conn:
            existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET username=?, first_name=?, last_seen=?, is_admin=? WHERE user_id=?",
                    (username, first_name, _now(), int(is_admin), user_id),
                )
            else:
                conn.execute(
                    "INSERT INTO users (user_id, username, first_name, is_admin, created_at, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, first_name, int(is_admin), _now(), _now()),
                )

    async def upsert_user(self, user_id: int, username: str, first_name: str, is_admin: bool = False) -> None:
        await self._run(self._upsert_user_sync, user_id, username, first_name, is_admin)

    def _get_user_sync(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return await self._run(self._get_user_sync, user_id)

    def _set_blocked_sync(self, user_id: int, blocked: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (int(blocked), user_id))

    async def set_blocked(self, user_id: int, blocked: bool) -> None:
        await self._run(self._set_blocked_sync, user_id, blocked)

    def _set_alerts_sync(self, user_id: int, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET alerts_on=? WHERE user_id=?", (int(enabled), user_id))

    async def set_alerts(self, user_id: int, enabled: bool) -> None:
        await self._run(self._set_alerts_sync, user_id, enabled)

    def _alert_subscribers_sync(self) -> List[int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_id FROM users WHERE alerts_on=1 AND is_blocked=0"
            ).fetchall()
            return [r["user_id"] for r in rows]

    async def alert_subscribers(self) -> List[int]:
        return await self._run(self._alert_subscribers_sync)

    def _count_users_sync(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]

    async def count_users(self) -> int:
        return await self._run(self._count_users_sync)

    # -------------------------------------------------------------- portfolio
    def _add_position_sync(self, user_id: int, symbol: str, qty: float, price: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO portfolio (user_id, symbol, quantity, entry_price, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, symbol, qty, price, _now()),
            )

    async def add_position(self, user_id: int, symbol: str, qty: float, price: float) -> None:
        await self._run(self._add_position_sync, user_id, symbol, qty, price)

    def _get_portfolio_sync(self, user_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio WHERE user_id=? ORDER BY created_at", (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    async def get_portfolio(self, user_id: int) -> List[Dict[str, Any]]:
        return await self._run(self._get_portfolio_sync, user_id)

    def _clear_portfolio_sync(self, user_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM portfolio WHERE user_id=?", (user_id,))
            return cur.rowcount

    async def clear_portfolio(self, user_id: int) -> int:
        return await self._run(self._clear_portfolio_sync, user_id)

    # ------------------------------------------------------------- predictions
    def _record_prediction_sync(self, signal: TradingSignal) -> int:
        payload = json.dumps(
            {
                "score_breakdown": signal.score_breakdown.as_dict(),
                "technical": signal.technical_summary,
                "sentiment": signal.sentiment_summary,
                "reasons": signal.reasons,
                "asset_class": signal.asset_class.value,
            }
        )
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO predictions "
                "(symbol, direction, entry, target, stop_loss, score, probability, timeframe, created_at, payload) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    signal.symbol,
                    signal.direction.value,
                    signal.entry,
                    signal.target,
                    signal.stop_loss,
                    signal.score,
                    signal.probability,
                    signal.timeframe,
                    signal.created_at.isoformat(),
                    payload,
                ),
            )
            return int(cur.lastrowid)

    async def record_prediction(self, signal: TradingSignal) -> int:
        return await self._run(self._record_prediction_sync, signal)

    def _open_predictions_sync(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM predictions WHERE resolved=0").fetchall()
            return [dict(r) for r in rows]

    async def open_predictions(self) -> List[Dict[str, Any]]:
        return await self._run(self._open_predictions_sync)

    def _resolve_prediction_sync(self, pred_id: int, outcome: str, price: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE predictions SET resolved=1, outcome=?, resolved_price=?, resolved_at=? WHERE id=?",
                (outcome, price, _now(), pred_id),
            )

    async def resolve_prediction(self, pred_id: int, outcome: str, price: float) -> None:
        await self._run(self._resolve_prediction_sync, pred_id, outcome, price)

    def _recent_predictions_sync(self, limit: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    async def recent_predictions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return await self._run(self._recent_predictions_sync, limit)

    def _performance_sync(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM predictions").fetchone()["c"]
            resolved = conn.execute("SELECT COUNT(*) AS c FROM predictions WHERE resolved=1").fetchone()["c"]
            wins = conn.execute(
                "SELECT COUNT(*) AS c FROM predictions WHERE outcome='win'"
            ).fetchone()["c"]
            losses = conn.execute(
                "SELECT COUNT(*) AS c FROM predictions WHERE outcome='loss'"
            ).fetchone()["c"]
            avg_score = conn.execute(
                "SELECT AVG(score) AS a FROM predictions"
            ).fetchone()["a"]
        decided = wins + losses
        win_rate = (wins / decided * 100.0) if decided else 0.0
        return {
            "total": total,
            "resolved": resolved,
            "open": total - resolved,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "avg_score": round(avg_score, 1) if avg_score is not None else 0.0,
        }

    async def performance(self) -> Dict[str, Any]:
        return await self._run(self._performance_sync)


_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        from ..config import settings

        _db = Database(settings.database_path)
    return _db
