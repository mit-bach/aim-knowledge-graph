"""Router (DESIGN.md §1.3): picks the sources that cover an entity, inside their rules, and
writes what comes back to the Evidence archive."""
from __future__ import annotations

import time
from typing import Any

from .connectors.base import Connector
from .control import Control
from .models import Reason, Trigger
from .store import Store


class Router:
    def __init__(self, store: Store, control: Control, connectors: list[Connector]) -> None:
        self.store, self.control, self.connectors = store, control, connectors
        self._last_call: dict[str, float] = {}

    def plan(self, entity: dict[str, Any]) -> list[Connector]:
        hits = [c for c in self.connectors if c.covers(entity)]
        return sorted(hits, key=lambda c: c.expected_cost(entity))

    def lookup(self, entity: dict[str, Any], reason: Reason, trigger: Trigger) -> list[str]:
        evidence_ids: list[str] = []
        for c in self.plan(entity):
            if not self.control.allow_source(c.name, c.rules.daily_limit):
                continue
            self._respect_rate(c)
            for ev in c.lookup(entity, reason, trigger):
                evidence_ids.append(self.store.add_evidence(ev, reason))
            self.control.record_source_call(c.name)
        return evidence_ids

    def _respect_rate(self, c: Connector) -> None:
        gap = 1.0 / max(c.rules.rate_per_sec, 1e-9)
        wait = self._last_call.get(c.name, 0.0) + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_call[c.name] = time.monotonic()
