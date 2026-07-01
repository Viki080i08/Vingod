"""Central configuration loaded from environment variables / .env file.

All secrets are read from the environment. Nothing sensitive is hard-coded so
the repository stays safe to publish.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_PACKAGE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    # Package .env wins over inherited shell env (common source of broken tokens
    # with stray newlines when copy-pasted into a hosting dashboard).
    load_dotenv(_PACKAGE_DIR / ".env", override=True)
    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass


def _clean_token(raw: str) -> str:
    """Strip whitespace / newlines accidentally pasted into a bot token."""
    return raw.strip().replace("\n", "").replace("\r", "").replace(" ", "")


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_list(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_int_list(name: str) -> List[int]:
    out: List[int] = []
    for item in _get_list(name):
        try:
            out.append(int(item))
        except ValueError:
            continue
    return out


@dataclass
class Settings:
    """Application settings resolved from the environment."""

    telegram_bot_token: str = field(
        default_factory=lambda: _clean_token(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    )
    admin_user_ids: List[int] = field(default_factory=lambda: _get_int_list("ADMIN_USER_IDS"))
    alerts_chat_id: str = field(default_factory=lambda: os.getenv("ALERTS_CHAT_ID", "").strip())

    twelve_data_api_key: str = field(default_factory=lambda: os.getenv("TWELVE_DATA_API_KEY", "").strip())
    alpha_vantage_api_key: str = field(default_factory=lambda: os.getenv("ALPHA_VANTAGE_API_KEY", "").strip())
    news_api_key: str = field(default_factory=lambda: os.getenv("NEWS_API_KEY", "").strip())

    signal_min_score: float = field(default_factory=lambda: _get_float("SIGNAL_MIN_SCORE", 70.0))
    scan_interval_seconds: int = field(default_factory=lambda: _get_int("SCAN_INTERVAL_SECONDS", 900))

    rate_limit_max_calls: int = field(default_factory=lambda: _get_int("RATE_LIMIT_MAX_CALLS", 20))
    rate_limit_window_seconds: int = field(default_factory=lambda: _get_int("RATE_LIMIT_WINDOW_SECONDS", 60))

    database_path: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_PATH", str(_PACKAGE_DIR / "trading_bot.db")
        ).strip()
    )
    default_watchlist: List[str] = field(
        default_factory=lambda: _get_list("DEFAULT_WATCHLIST")
        or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    )

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").strip().upper())

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def has_forex_stock_provider(self) -> bool:
        return bool(self.twelve_data_api_key or self.alpha_vantage_api_key)

    def validate(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN est vide. Copiez trading_bot/.env.example vers "
                "trading_bot/.env et collez votre token (créé via @BotFather)."
            )
        if "\n" in self.telegram_bot_token or " " in self.telegram_bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN invalide (espaces ou retours à la ligne détectés). "
                "Recopiez le token sur une seule ligne dans trading_bot/.env"
            )
        if ":" not in self.telegram_bot_token or len(self.telegram_bot_token) < 20:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN invalide. Format attendu : 123456789:ABCdefGHI..."
            )

    def configure_logging(self) -> None:
        level = getattr(logging, self.log_level, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )
        # Reduce noise from third-party libraries.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.INFO)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)


settings = Settings()
