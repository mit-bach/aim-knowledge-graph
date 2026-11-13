"""Checks run after each batch (docs/DESIGN.md §2.5)."""
from __future__ import annotations

import json

from .config import fact_types
from .store import Store


def run_checks(store: Store) -> dict[str, list]:
    db = store.db
    types = fact_types()
    live = {r["id"] for r in db.execute("SELECT id FROM entities WHERE status!='merged'")}
    srcs = {r["id"] for r in db.execute("SELECT id FROM sources")}
    fact_ids = {r["id"] for r in db.execute("SELECT id FROM facts")}
    out: dict[str, list] = {"broken_links": [], "unsourced_facts": [], "unknown_fact_types": [],
                            "dangling_supersession": [], "dossiers_without_links": [], "ambiguity_queue": []}
    linked: set[str] = set()
    for f in db.execute("SELECT * FROM facts"):
        if f["subject_id"] not in live or (f["object_id"] and f["object_id"] not in live):
            out["broken_links"].append(f["id"])
        s = json.loads(f["source_ids"])
        if not s or any(x not in srcs for x in s):
            out["unsourced_facts"].append(f["id"])
        if f["predicate"] not in types:
            out["unknown_fact_types"].append(f["predicate"])
        if f["superseded_by"] and f["superseded_by"] not in fact_ids:
            out["dangling_supersession"].append(f["id"])
        if f["object_id"]:
            linked |= {f["subject_id"], f["object_id"]}
    out["dossiers_without_links"] = sorted(i for i in live if i not in linked and
                                           db.execute("SELECT status FROM entities WHERE id=?", (i,)).fetchone()[0] == "researched")
    out["ambiguity_queue"] = [r["id"] for r in db.execute("SELECT id FROM entities WHERE status='ambiguous'")]
    return out


def failures(report: dict[str, list]) -> dict[str, list]:
    """Checks that must be empty. The ambiguity queue is work for a teammate, not a failure."""
    return {k: v for k, v in report.items() if v and k != "ambiguity_queue"}
