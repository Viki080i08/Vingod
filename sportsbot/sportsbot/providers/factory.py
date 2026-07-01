"""Selects the configured data provider, with safe fallback to demo."""

from __future__ import annotations

from ..config import get_settings
from ..logging_conf import get_logger
from .apifootball import APIFootballProvider
from .base import SportsDataProvider
from .demo import DemoProvider
from .footballdata import FootballDataProvider
from .thesportsdb import TheSportsDBProvider

logger = get_logger(__name__)


def get_provider() -> SportsDataProvider:
    """Return the active data source.

    "auto" (default) picks the best available real source:
        API-Football key  >  football-data.org key  >  TheSportsDB (free).
    Explicit values force a specific source: apifootball, footballdata,
    thesportsdb, or demo/internal (offline engine).
    """
    settings = get_settings()
    provider = settings.data_provider

    if provider in ("demo", "internal", "engine"):
        logger.info("Using internal PronoIA engine (offline, no API).")
        return DemoProvider()  # type: ignore[return-value]

    if provider in ("apifootball", "auto") and settings.apifootball_api_key:
        logger.info("Using API-Football provider (real, all competitions).")
        return APIFootballProvider(settings.apifootball_api_key)  # type: ignore[return-value]

    if provider in ("footballdata", "auto") and settings.football_data_api_key:
        logger.info("Using football-data.org provider.")
        return FootballDataProvider(settings.football_data_api_key)  # type: ignore[return-value]

    if provider == "apifootball":
        logger.warning("APIFOOTBALL_API_KEY missing; using TheSportsDB instead.")
    if provider == "footballdata":
        logger.warning("FOOTBALL_DATA_API_KEY missing; using TheSportsDB instead.")

    if provider == "auto":
        logger.warning(
            "Aucune clé API réelle configurée — couverture LIMITÉE via la clé "
            "de test TheSportsDB. Ajoutez APIFOOTBALL_API_KEY (gratuit) pour "
            "TOUS les vrais matchs du jour."
        )
    logger.info("Using TheSportsDB provider (free key, partial coverage).")
    return TheSportsDBProvider(settings.thesportsdb_api_key)  # type: ignore[return-value]


def provider_by_name(name: str) -> SportsDataProvider:
    """Return a provider instance matching a stored match.provider value."""
    settings = get_settings()
    if name == "apifootball" and settings.apifootball_api_key:
        return APIFootballProvider(settings.apifootball_api_key)  # type: ignore[return-value]
    if name == "footballdata" and settings.football_data_api_key:
        return FootballDataProvider(settings.football_data_api_key)  # type: ignore[return-value]
    if name == "thesportsdb":
        return TheSportsDBProvider(settings.thesportsdb_api_key)  # type: ignore[return-value]
    return DemoProvider()  # type: ignore[return-value]
