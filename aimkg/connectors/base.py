"""The connector interface (docs/DESIGN.md §2.1). One module per source, each a black box.

Write the source's rules from its own terms page. A connector never runs without a reason.
Its records carry a payload: {"match": identity confidence, "ids": new IDs, "facts": [...]}.
New IDs are how one source triggers another: they make another connector `covers()` the person.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import Reason, Record, Trigger


@dataclass
class SourceRules:
    terms_url: str
    rate_per_sec: float = 1.0
    daily_limit: int = 1000
    cadence_days: int = 90
    may_store: list[str] = field(default_factory=list)
    notes: str = ""


class Connector(ABC):
    name: str
    rules: SourceRules

    @abstractmethod
    def covers(self, person: dict[str, Any]) -> bool:
        """Can this source say anything about this person, given what we know (their IDs)?"""

    @abstractmethod
    def lookup(self, person: dict[str, Any], reason: Reason, trigger: Trigger) -> list[Record]:
        """Fetch what the source says about the person."""

    def expected_cost(self, person: dict[str, Any]) -> float:
        return 0.1
