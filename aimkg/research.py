"""research(p): find what allowed sources say about one person (docs/DESIGN.md §2.3).

IDs first; fan out across every source that covers the person, letting one source's new IDs
make another cover them; stop when it's dry. A weak identity match writes nothing."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import extract
from .connectors.base import Connector
from .models import FactDraft, Reason, Trigger
from .store import Store


@dataclass
class Research:
    person_id: str
    drafts: list[tuple[FactDraft, str]] = field(default_factory=list)  # (fact, source id)
    sources_used: list[str] = field(default_factory=list)
    ambiguous: bool = False


def research(store: Store, connectors: list[Connector], person_id: str, reason: Reason, trigger: Trigger,
             calls_per_person: int, dry_after: int, identity_threshold: float) -> Research:
    out = Research(person_id)
    used: set[str] = set()
    dry = 0
    while len(used) < calls_per_person and dry < dry_after:
        person = store.entity(person_id)
        plan = [c for c in connectors if c.name not in used and c.covers(person)]
        if not plan:
            break
        c = min(plan, key=lambda c: c.expected_cost(person))
        used.add(c.name)
        out.sources_used.append(c.name)
        new = 0
        for rec in c.lookup(person, reason, trigger):
            if rec.payload.get("match", 1.0) < identity_threshold:
                out.ambiguous = True
                return out
            sid = store.add_source(rec)
            store.add_ids(person["id"], rec.payload.get("ids", {}))   # may make another source cover them
            for d in extract.structured(rec):
                out.drafts.append((d, sid))
                new += 1
        dry = 0 if new else dry + 1
    out.person_id = store.entity(person_id)["id"]   # a merge may have moved them
    return out
