"""The trail: how the graph is explored and grows (docs/DESIGN.md §2.2).

One frontier of people, each with a reason. select() picks by expected information gain,
with a little random exploration; research() finds what sources say; upkeep.write() puts it
in the graph; everyone the facts name goes on the frontier. The trail never decides the
graph's structure: the facts do."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from . import upkeep
from .config import trail_settings
from .connectors.base import Connector
from .models import Reason, Ref
from .research import research
from .store import Store


@dataclass
class Step:
    person_id: str
    sources_used: list[str]
    facts: int
    new_on_frontier: int
    ambiguous: bool


class Trail:
    def __init__(self, store: Store, connectors: list[Connector], settings: dict[str, Any] | None = None,
                 rng: random.Random | None = None) -> None:
        self.store, self.connectors = store, connectors
        self.cfg = settings or trail_settings()
        self.rng = rng or random.Random(0)
        self.researched_today = 0

    # ---- putting people on the frontier --------------------------------------------
    def seed(self, ref: Ref, why: str, synthetic: bool = False) -> str:
        pid = self.store.resolve(ref, synthetic)
        self.store.frontier_add(pid, Reason(why=why).__dict__, hops=0)
        return pid

    def ask(self, name: str, why: str) -> dict[str, Any]:
        """A person asked about someone (follow_person): they jump the queue."""
        pid = self.store.resolve(Ref("person", name), synthetic=name.startswith("Synthetic "))
        fid = self.store.frontier_add(pid, Reason(why=f"asked: {why}").__dict__, hops=0, asked=True)
        state = self.store.entity(pid)["status"]
        return {"person_id": pid, "frontier_id": fid, "state": "queued" if state == "referenced" else state}

    # ---- why this person next --------------------------------------------------------
    def features(self, entry: dict[str, Any]) -> dict[str, float]:
        pid = entry["person_id"]
        nbrs = self.store.neighbors(pid)
        known = [self.store.entity(o) for o, _ in nbrs]
        unexplored = sum(1 for e in known if e and e["status"] != "researched")
        new_place = any(e and e["kind"] == "org" and not any(
            self.store.entity(s)["status"] == "researched"
            for s, _ in self.store.neighbors(e["id"]) if self.store.entity(s)["kind"] == "person" and s != pid)
            for e in known)
        return {"novelty": 1.0 if not known else unexplored / len(known),
                "bridging": 1.0 if new_place else 0.0,
                "relevance": (1.0 / (1 + entry["hops"])) * (3.0 if entry["asked"] else 1.0),
                "evidence": min(1.0, entry["n_reasons"] / 3),
                "cost": 0.1}

    def score(self, entry: dict[str, Any]) -> float:
        w, f = self.cfg["weights"], self.features(entry)
        return sum(w[k] * f[k] for k in ("novelty", "bridging", "relevance", "evidence")) - w["cost"] * f["cost"]

    def select(self) -> dict[str, Any] | None:
        queued = [e for e in self.store.frontier_queued() if e["hops"] <= self.cfg["max_hops"]]
        if not queued:
            return None
        if self.rng.random() < self.cfg["explore_share"]:
            return self.rng.choice(queued)
        return max(queued, key=self.score)

    # ---- one step of the trail -------------------------------------------------------
    def step(self) -> Step | None:
        if self.researched_today >= self.cfg["daily_budget"]:
            return None
        entry = self.select()
        if entry is None:
            return None
        self.store.frontier_set(entry["id"], "claimed")
        reason = Reason(**entry["reason"])
        trigger = "person" if entry["asked"] else "trail"
        r = research(self.store, self.connectors, entry["person_id"], reason, trigger,
                     self.cfg["calls_per_person"], self.cfg["dry_after"], self.cfg["identity_threshold"])
        self.researched_today += 1
        if r.ambiguous:   # nothing written; a teammate checks who this is
            self.store.set_status(r.person_id, "ambiguous")
            self.store.frontier_set(entry["id"], "ambiguous")
            return Step(r.person_id, r.sources_used, 0, 0, True)
        synthetic = bool(self.store.entity(r.person_id)["synthetic"])
        named = upkeep.write(self.store, r.drafts, synthetic)
        self.store.set_status(r.person_id, "researched")
        self.store.frontier_set(entry["id"], "done")
        added = 0
        for pid, fid in named:
            if pid == r.person_id:
                continue
            why = Reason(why=f"named in a fact about {self.store.entity(r.person_id)['name']}",
                         from_id=r.person_id, fact_id=fid)
            if self.store.frontier_add(pid, why.__dict__, hops=entry["hops"] + 1) is not None:
                added += 1
        return Step(r.person_id, r.sources_used, len(r.drafts), added, False)

    def run(self, max_steps: int) -> list[Step]:
        steps = []
        for _ in range(max_steps):
            s = self.step()
            if s is None:
                break
            steps.append(s)
        return steps
