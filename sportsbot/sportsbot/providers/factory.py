"""Selects the configured data provider, with safe fallback to demo."""

from __future__ import annotations

from ..config import get_settings
from ..logging_conf import get_logger
from .base import SportsDataProvider
from .demo import DemoProvider
from .footballdata import FootballDataProvider

logger = get_logger(__name__)


def get_provider() -> SportsDataProvider:
    settings = get_settings()
    if settings.data_provider == "footballdata" and settings.football_data_api_key:
        logger.info("Using football-data.org provider")
        return FootballDataProvider(settings.football_data_api_key)  # type: ignore[return-value]
    if settings.data_provider == "footballdata":
        logger.warning(
            "DATA_PROVIDER=footballdata but FOOTBALL_DATA_API_KEY missing; "
            "falling back to demo provider."
        )
    return DemoProvider()  # type: ignore[return-value]
