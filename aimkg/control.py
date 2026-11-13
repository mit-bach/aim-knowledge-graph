"""Control (DESIGN.md §1.3): budgets, source rules, and when territories open."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .store import Store

CONFIG = Path(__file__).resolve().parent.parent / "schema" / "territories.yaml"


@dataclass
class Control:
    store: Store
    open_threshold: int = 10
    max_hops_inside: int = 2
    max_hops_past_border: int = 1
    budget_used: Counter = field(default_factory=Counter)      # per territory, per run
    source_calls: Counter = field(default_factory=Counter)     # per connector, per run

    @classmethod
    def from_config(cls, store: Store, path: Path = CONFIG) -> "Control":
        cfg = yaml.safe_load(path.read_text())
        c = cls(store, cfg["open_threshold"], cfg["max_hops_inside"], cfg["max_hops_past_border"])
        for t in cfg.get("seed", []):
            store.open_territory(t["path"], budget=t.get("budget", 200))
        return c

    def may_spend(self, territory: str) -> bool:
        row = self.store.db.execute("SELECT budget FROM territories WHERE path=?", (territory,)).fetchone()
        return row is not None and self.budget_used[territory] < row["budget"]

    def spend(self, territory: str) -> None:
        self.budget_used[territory] += 1

    def allow_source(self, name: str, daily_limit: int) -> bool:
        return self.source_calls[name] < daily_limit

    def record_source_call(self, name: str) -> None:
        self.source_calls[name] += 1

    def maybe_open(self, territory: str, parent: str | None = None) -> bool:
        """Open a territory once enough reasons point at it (its holding list)."""
        if self.store.territory_exists(territory):
            return False
        if self.store.holding_count(territory) >= self.open_threshold:
            self.store.open_territory(territory, parent=parent)
            self.store.release_holding(territory)
            return True
        return False

    def open_now(self, territory: str, parent: str | None = None) -> None:
        """A person asked about it: open without waiting for the threshold."""
        self.store.open_territory(territory, parent=parent)
        self.store.release_holding(territory)
