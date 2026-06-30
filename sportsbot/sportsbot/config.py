"""Centralised application configuration loaded from environment variables.

All settings are read once at import time into a frozen ``Settings`` instance
accessible via :func:`get_settings`. A ``.env`` file (if present) is loaded
automatically so the project runs out-of-the-box for local development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Project root = the directory that contains this package's parent.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from the project root if it exists. Real environment variables
# always take precedence over .env values.
load_dotenv(PROJECT_ROOT / ".env")


def _parse_time(value: str, default: str) -> time:
    raw = (value or default).strip()
    try:
        hour, minute = raw.split(":")
        return time(hour=int(hour), minute=int(minute))
    except (ValueError, AttributeError):
        hour, minute = default.split(":")
        return time(hour=int(hour), minute=int(minute))


def _parse_admin_ids(value: str) -> List[int]:
    ids: List[int] = []
    for chunk in (value or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            ids.append(int(chunk))
    return ids


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Telegram
    bot_token: str
    admin_ids: List[int] = field(default_factory=list)

    # Payments
    payment_provider_token: str = ""
    subscription_price_eur: float = 19.99
    subscription_currency: str = "EUR"
    subscription_duration_days: int = 30

    # Database
    database_url: str = "sqlite:///pronoia.db"

    # Data provider
    data_provider: str = "auto"
    football_data_api_key: str = ""
    thesportsdb_api_key: str = "3"
    apifootball_api_key: str = ""
    forecast_horizon_days: int = 5

    # Scheduled jobs
    daily_sync_time: time = field(default_factory=lambda: time(6, 0))
    daily_push_time: time = field(default_factory=lambda: time(9, 0))
    results_update_time: time = field(default_factory=lambda: time(23, 30))

    # Admin web dashboard
    admin_web_host: str = "0.0.0.0"
    admin_web_port: int = 8080
    admin_web_username: str = "admin"
    admin_web_password: str = "changeme"
    admin_web_secret: str = "please-change-this-secret-key"

    # Misc
    timezone: str = "Europe/Paris"
    log_level: str = "INFO"

    @property
    def payments_enabled(self) -> bool:
        """True when a real Telegram payment provider token is configured."""
        return bool(self.payment_provider_token.strip())

    @property
    def price_minor_units(self) -> int:
        """Subscription price expressed in the smallest currency unit (cents)."""
        return int(round(self.subscription_price_eur * 100))

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    horizon = int(os.getenv("FORECAST_HORIZON_DAYS", "5") or 5)
    horizon = max(1, min(horizon, 5))  # clamp to 1..5 days as required by spec

    return Settings(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        payment_provider_token=os.getenv("TELEGRAM_PAYMENT_PROVIDER_TOKEN", "").strip(),
        subscription_price_eur=float(os.getenv("SUBSCRIPTION_PRICE_EUR", "19.99") or 19.99),
        subscription_currency=os.getenv("SUBSCRIPTION_CURRENCY", "EUR").strip() or "EUR",
        subscription_duration_days=int(os.getenv("SUBSCRIPTION_DURATION_DAYS", "30") or 30),
        database_url=os.getenv("DATABASE_URL", "sqlite:///pronoia.db").strip(),
        data_provider=os.getenv("DATA_PROVIDER", "auto").strip().lower() or "auto",
        football_data_api_key=os.getenv("FOOTBALL_DATA_API_KEY", "").strip(),
        thesportsdb_api_key=os.getenv("THESPORTSDB_API_KEY", "3").strip() or "3",
        apifootball_api_key=os.getenv("APIFOOTBALL_API_KEY", "").strip(),
        forecast_horizon_days=horizon,
        daily_sync_time=_parse_time(os.getenv("DAILY_SYNC_TIME", ""), "06:00"),
        daily_push_time=_parse_time(os.getenv("DAILY_PUSH_TIME", ""), "09:00"),
        results_update_time=_parse_time(os.getenv("RESULTS_UPDATE_TIME", ""), "23:30"),
        admin_web_host=os.getenv("ADMIN_WEB_HOST", "0.0.0.0").strip(),
        admin_web_port=int(os.getenv("ADMIN_WEB_PORT", "8080") or 8080),
        admin_web_username=os.getenv("ADMIN_WEB_USERNAME", "admin").strip(),
        admin_web_password=os.getenv("ADMIN_WEB_PASSWORD", "changeme"),
        admin_web_secret=os.getenv("ADMIN_WEB_SECRET", "please-change-this-secret-key"),
        timezone=os.getenv("TIMEZONE", "Europe/Paris").strip() or "Europe/Paris",
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
