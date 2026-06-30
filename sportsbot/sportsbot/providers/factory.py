"""Selects the configured data provider, with safe fallback to demo."""

from __future__ import annotations

from ..config import get_settings
from ..logging_conf import get_logger
from .base import SportsDataProvider
from .demo import DemoProvider
from .footballdata import FootballDataProvider
from .thesportsdb import TheSportsDBProvider

logger = get_logger(__name__)


def get_provider() -> SportsDataProvider:
    """Return the active data source.

    Default: TheSportsDB (real worldwide matches, free key). football-data.org
    is available when a key is set. "demo"/"internal" uses the offline engine.
    """
    provider = get_settings().data_provider

    if provider in ("demo", "internal", "engine"):
        logger.info("Using internal PronoIA engine (offline, no API).")
        return DemoProvider()  # type: ignore[return-value]

    if provider == "footballdata":
        settings = get_settings()
        if settings.football_data_api_key:
            logger.info("Using football-data.org provider.")
            return FootballDataProvider(settings.football_data_api_key)  # type: ignore[return-value]
        logger.warning("FOOTBALL_DATA_API_KEY missing; using TheSportsDB instead.")

    # Default + explicit "thesportsdb": real worldwide fixtures.
    logger.info("Using TheSportsDB provider (real matches, all competitions).")
    return TheSportsDBProvider(get_settings().thesportsdb_api_key)  # type: ignore[return-value]


def provider_by_name(name: str) -> SportsDataProvider:
    """Return a provider instance matching a stored match.provider value."""
    settings = get_settings()
    if name == "footballdata" and settings.football_data_api_key:
        return FootballDataProvider(settings.football_data_api_key)  # type: ignore[return-value]
    if name == "thesportsdb":
        return TheSportsDBProvider(settings.thesportsdb_api_key)  # type: ignore[return-value]
    return DemoProvider()  # type: ignore[return-value]
