"""The connector interface (DESIGN.md §2.4). One module per source.

A connector never runs without a reason, and never fetches what its source's terms forbid.
Write the source's rules into `rules` from its own terms page (docs/PRD.md §5, docs/DESIGN.md §2.6).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import Evidence, Reason, Trigger


@dataclass
class SourceRules:
    terms_url: str
    rate_per_sec: float = 1.0          # stay under the source's published limit
    daily_limit: int = 1000
    cadence_days: int = 90             # scheduled refresh
    may_store: list[str] = field(default_factory=list)   # fields we may keep
    notes: str = ""


class Connector(ABC):
    name: str
    rules: SourceRules

    @abstractmethod
    def covers(self, entity: dict[str, Any]) -> bool:
        """Can this source say anything about this entity? (e.g. "has an ORCID")"""

    @abstractmethod
    def lookup(self, entity: dict[str, Any], reason: Reason, trigger: Trigger) -> list[Evidence]:
        """Fetch evidence about the entity. Return raw documents; extraction happens later."""

    def expected_cost(self, entity: dict[str, Any]) -> float:
        """Calls and time this lookup is likely to take, roughly 0..1. Feeds frontier scoring."""
        return 0.1
