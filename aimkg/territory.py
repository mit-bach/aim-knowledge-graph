"""Territory agent (DESIGN.md §1.6, §2.3): one turn of the people trail.

Pop the best frontier item (an entity and its reason), look it up, write what comes back,
and put everything it points to on a frontier, with a reason. Items whose territory is
somewhere else are handed across the border, or wait in that territory's holding list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import frontier
from .control import Control
from .extract import StructuredExtractor
from .models import Claim, EntityRef, Reason, top_territory
from .resolve import Resolver
from .router import Router
from .store import Store


@dataclass
class TurnResult:
    entity_id: str
    evidence: int
    new_links: int
    queued_here: int
    handed_off: int
    held: int
    opened: list[str]


class TerritoryAgent:
    def __init__(self, territory: str, store: Store, control: Control, router: Router,
                 extractor: StructuredExtractor | None = None, weights: frontier.Weights | None = None) -> None:
        self.territory = territory
        self.store, self.control, self.router = store, control, router
        self.extractor = extractor or StructuredExtractor()
        self.resolver = Resolver(store)
        self.weights = weights or frontier.Weights()

    # ---- seeding ---------------------------------------------------------------
    def seed(self, ref: EntityRef, note: str, synthetic: bool = False) -> str:
        eid = self.resolver.resolve(ref, synthetic)
        reason = Reason(requested_by="seed", note=note)
        self.store.push_frontier(eid, self.territory, reason, self._score(eid, reason, 0, False), hops=0)
        return eid

    # ---- one turn --------------------------------------------------------------
    def step(self) -> TurnResult | None:
        if not self.control.may_spend(self.territory):
            return None
        item = self.store.pop_frontier(self.territory)
        if item is None:
            return None
        self.control.spend(self.territory)
        entity = self.store.entity(item.entity_id)
        trigger = "person_asks" if item.reason.requested_by in ("task", "person") else "graph_asks"
        ev_ids = self.router.lookup(entity, item.reason, trigger)
        res = TurnResult(item.entity_id, len(ev_ids), 0, 0, 0, 0, [])
        for ev_id in ev_ids:
            row = self.store.evidence(ev_id)
            for claim in self.extractor.extract(row):
                self._write(claim, ev_id, item, bool(row["synthetic"]), res)
        self.store.mark_expanded(item.entity_id)
        self.store.finish_frontier(item.id)
        return res

    def run(self, max_turns: int) -> list[TurnResult]:
        out = []
        for _ in range(max_turns):
            r = self.step()
            if r is None:
                break
            out.append(r)
        return out

    # ---- internals -------------------------------------------------------------
    def _write(self, claim: Claim, ev_id: str, item: Any, synthetic: bool, res: TurnResult) -> None:
        subj = self.resolver.resolve(claim.subject, synthetic)
        if claim.predicate.startswith("attr:"):
            self.store.set_attribute(subj, claim.predicate[5:], claim.object, ev_id, claim.confidence)
            return
        obj = self.resolver.resolve(claim.object, synthetic)
        self.store.add_link(subj, obj, claim.predicate, claim.span.get("desc", ""), ev_id, claim.confidence)
        res.new_links += 1
        other = obj if subj == item.entity_id else subj
        if other == item.entity_id:
            return
        target = self.store.entity(other)
        if target["status"] != "referenced":
            return
        reason = Reason(requested_by="territory", note=f"linked from {item.entity_id}",
                        from_entity=item.entity_id, link_path=claim.predicate, evidence_id=ev_id)
        self._emit(other, top_territory(target["territory_path"]) or self.territory, reason,
                   item.hops + 1, claim.confidence, res)

    def _emit(self, eid: str, territory: str, reason: Reason, hops: int, confidence: float,
              res: TurnResult) -> None:
        crossing = territory != self.territory
        if crossing:
            if hops > self.control.max_hops_inside + self.control.max_hops_past_border:
                return
        elif hops > self.control.max_hops_inside:
            return
        score = self._score(eid, reason, hops, crossing, confidence)
        if not crossing:
            if self.store.push_frontier(eid, territory, reason, score, hops) is not None:
                res.queued_here += 1
        elif self.store.territory_exists(territory):
            # border handoff: straight into the neighbor's frontier, with the reason
            if self.store.push_frontier(eid, territory, reason, score, hops) is not None:
                res.handed_off += 1
        else:
            self.store.push_frontier(eid, territory, reason, score, hops, state="holding")
            res.held += 1
            if self.control.maybe_open(territory, parent=None):
                res.opened.append(territory)

    def _score(self, eid: str, reason: Reason, hops: int, crossing: bool, evidence: float = 1.0) -> float:
        links = self.store.links_of(eid)
        unexplored = sum(1 for ln in links if self.store.entity(ln["other"])["status"] == "referenced")
        novelty = 1.0 if not links else unexplored / len(links)
        return frontier.score(hops=hops, requested_by=reason.requested_by, bridging=crossing,
                              novelty=novelty, evidence=evidence, cost=0.1, w=self.weights)
