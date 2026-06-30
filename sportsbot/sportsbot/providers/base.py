"""Provider interfaces and shared data structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ProviderTeam:
    name: str
    league: str = ""
    attack_rating: float = 1.0
    defense_rating: float = 1.0
    goals_for_avg: float = 1.35
    goals_against_avg: float = 1.35
    recent_form: str = ""
    home_strength: float = 1.0
    away_strength: float = 1.0
    key_absences: int = 0
    momentum: float = 0.0


@dataclass
class ProviderMatch:
    external_id: str
    provider: str
    league: str
    sport: str
    home: ProviderTeam
    away: ProviderTeam
    kickoff: datetime
    head_to_head: Optional[dict] = None
    status: str = "scheduled"
    home_score: Optional[int] = None
    away_score: Optional[int] = None


@dataclass
class MatchResult:
    external_id: str
    home_score: int
    away_score: int
    status: str = "finished"


class SportsDataProvider(ABC):
    """Abstract base class every data provider must implement."""

    name: str = "base"

    @abstractmethod
    def fetch_fixtures(self, horizon_days: int) -> List[ProviderMatch]:
        """Return scheduled matches for today + ``horizon_days`` days."""

    @abstractmethod
    def fetch_results(self, external_ids: List[str]) -> List[MatchResult]:
        """Return final results for the given match external ids (if known)."""
