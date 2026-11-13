"""The Agent API's five calls (DESIGN.md §2.7), as plain functions over the store.
`api.py` serves them as an MCP server. Relevance order is implicit: lists come back in
order of usefulness, and the number itself is never returned."""
from __future__ import annotations

import re
import uuid
from collections import Counter
from typing import Any

from . import frontier
from .models import Reason, top_territory
from .store import Store

Filter = tuple[list[str], list[str]] | None
STOP = {"the", "a", "an", "of", "to", "is", "who", "what", "how", "and", "in", "at", "for", "with", "are", "does"}


def _words(q: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9]+", q) if w.lower() not in STOP and len(w) > 2]


def _passes(values: list[str], flt: Filter) -> bool:
    if not flt:
        return True
    include, exclude = flt
    if include and not any(v in include for v in values):
        return False
    return not any(v in exclude for v in values)


class AgentAPI:
    def __init__(self, store: Store) -> None:
        self.store = store

    def open_task(self, question: str, user_id: str, task_id: str | None = None) -> dict[str, Any]:
        tid = task_id or uuid.uuid4().hex[:12]
        init = self.store.search(_words(question), limit=5)
        territories = sorted({top_territory(self.store.entity(e)["territory_path"]) for e in init} - {""})
        existing = self.store.task(tid)
        self.store.save_task(tid, question, user_id, existing["reads"] if existing else [],
                             existing["lookups"] if existing else [])
        return {"task_id": tid, "init_entities": init, "required_entities": [],
                "default_territory_filter": (territories, [])}

    def continue_task(self, question: str, task_id: str) -> dict[str, Any]:
        t = self.store.task(task_id)
        return self.open_task(question, t["user_id"] if t else "unknown", task_id)

    def get_entities(self, entity_ids: list[str]) -> dict[str, Any]:
        out = {}
        for eid in entity_ids:
            e = self.store.entity(eid)
            if e is None:
                continue
            counts = Counter(ln["link_path"] for ln in self.store.links_of(eid))
            out[e["name"]] = {"id": eid, "desc": e["desc"], "link_counts": dict(counts),
                              "territory_path": e["territory_path"]}
        return out

    def read_entity(self, entity_id: str, territory_filter: Filter = None, link_filter: Filter = None,
                    tag_filter: Filter = None, link_verbosity: str = "description",
                    reason_for_reading: str = "", task_id: str | None = None) -> dict[str, Any]:
        e = self.store.entity(entity_id)
        if e is None:
            return {"error": f"no entity {entity_id}; use request_lookup"}
        self.store.bump_relevance(entity_id, 0.5)   # feeds relevance order; never shown
        if task_id and (t := self.store.task(task_id)):
            t["reads"].append({"entity_id": entity_id, "reason_for_reading": reason_for_reading})
            self.store.save_task(task_id, t["question"], t["user_id"], t["reads"], t["lookups"])
        doc: dict[str, Any] = {"id": entity_id, "name": e["name"], "desc": e["desc"], "tags": e["tags"],
                               "territory_path": e["territory_path"], "synthetic": bool(e["synthetic"]),
                               "attributes": {k: {"value": a["value"], "evidence_ids": a["evidence_ids"]}
                                              for k, a in e["attributes"].items()}}
        if link_verbosity == "none":
            return doc
        links = []
        for ln in self.store.links_of(entity_id):
            other = self.store.entity(ln["other"])
            if not _passes(other["territory_path"], territory_filter):
                continue
            if not _passes([ln["link_path"], ln["link_path"].split("::")[0]], link_filter):
                continue
            if not _passes(other["tags"], tag_filter):
                continue
            item: dict[str, Any] = {"to": {"id": other["id"], "name": other["name"], "desc": other["desc"],
                                           "territory_path": other["territory_path"]},
                                    "link_path": ln["link_path"], "link_desc": ln["desc"],
                                    "direction": "out" if ln["from_id"] == entity_id else "in"}
            if link_verbosity in ("evidence", "full"):
                item["evidence"] = [{k: ev[k] for k in ("source", "url", "fetched_at")}
                                    for ev in map(self.store.evidence, ln["evidence_ids"]) if ev]
            links.append(item)
        doc["links"] = links
        return doc

    def request_lookup(self, name_or_id: str, reason: str, task_id: str | None = None,
                       territory: str = "1::mit") -> dict[str, Any]:
        eid = name_or_id if self.store.entity(name_or_id) else None
        if eid is None:
            from .models import EntityRef
            from .resolve import Resolver
            eid = Resolver(self.store).resolve(EntityRef("person", name_or_id, [territory]))
        r = Reason(requested_by="task", note=reason)
        terr = top_territory(self.store.entity(eid)["territory_path"]) or territory
        score = frontier.score(hops=0, requested_by="task", bridging=False, novelty=1.0, evidence=0.5, cost=0.1)
        state = "queued" if self.store.territory_exists(terr) else "holding"
        fid = self.store.push_frontier(eid, terr, r, score, hops=0, state=state)
        if task_id and (t := self.store.task(task_id)):
            t["lookups"].append({"entity_id": eid, "reason": reason})
            self.store.save_task(task_id, t["question"], t["user_id"], t["reads"], t["lookups"])
        return {"entity_id": eid, "frontier_item_id": fid, "state": state}
