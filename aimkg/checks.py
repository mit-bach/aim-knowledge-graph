"""Graph checks (DESIGN.md §2.8). Run after each batch, and nightly."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .store import Store

LINK_TYPES = Path(__file__).resolve().parent.parent / "schema" / "link_types.yaml"


def run_checks(store: Store) -> dict[str, list]:
    db = store.db
    known = set(yaml.safe_load(LINK_TYPES.read_text()))
    ids = {r["id"] for r in db.execute("SELECT id FROM entities")}
    evid = {r["id"] for r in db.execute("SELECT id FROM evidence")}
    out: dict[str, list] = {"broken_links": [], "unsourced_links": [], "unsourced_attributes": [],
                            "unknown_link_types": [], "unused_link_types": [], "empty_territories": []}
    used = set()
    for r in db.execute("SELECT * FROM links"):
        used.add(r["link_path"])
        if r["from_id"] not in ids or r["to_id"] not in ids:
            out["broken_links"].append(r["id"])
        ev = json.loads(r["evidence_ids"])
        if not ev or any(e not in evid for e in ev):
            out["unsourced_links"].append(r["id"])
        if r["link_path"] not in known:
            out["unknown_link_types"].append(r["link_path"])
    for r in db.execute("SELECT id, attributes FROM entities"):
        for key, a in json.loads(r["attributes"]).items():
            if not a.get("evidence_ids") or any(e not in evid for e in a["evidence_ids"]):
                out["unsourced_attributes"].append(f"{r['id']}.{key}")
    out["unused_link_types"] = sorted(known - used)
    for t in store.territories():
        n = db.execute("SELECT COUNT(*) FROM entities WHERE territory_path LIKE ?", (f'%"{t}"%',)).fetchone()[0]
        if n == 0:
            out["empty_territories"].append(t)
    return out


def failures(report: dict[str, list]) -> dict[str, list]:
    """The checks that must be empty. Unused link types are information, not failure."""
    return {k: v for k, v in report.items() if v and k != "unused_link_types"}
