"""write(G, facts) and its upkeep, in one step (docs/DESIGN.md §2.4, §2.5).

A fact lives in its subject's dossier; a link is a fact with an object. The same fact from a
second source adds that source. A newer fact on a single-valued type supersedes the older one,
which stays as history."""
from __future__ import annotations

import json

from .config import fact_types
from .models import FactDraft
from .store import Store

TYPES = fact_types()


def write(store: Store, drafts: list[tuple[FactDraft, str]], synthetic: bool) -> list[tuple[str, int]]:
    """Write facts. Returns (person dossier, fact id) for every person the facts name, for the frontier."""
    named: list[tuple[str, int]] = []
    for d, sid in drafts:
        subj = store.resolve(d.subject, synthetic)
        obj = store.resolve(d.object, synthetic) if d.object else None
        fid = _upsert(store, subj, d, obj, sid)
        for eid in (subj, obj):
            if eid and store.entity(eid)["kind"] == "person":
                named.append((store.entity(eid)["id"], fid))
    return named


def _upsert(store: Store, subj: str, d: FactDraft, obj: str | None, sid: str) -> int:
    value = json.dumps(d.value) if d.value is not None else None
    row = store.db.execute(
        "SELECT id, source_ids, confidence FROM facts WHERE subject_id=? AND predicate=? "
        "AND object_id IS ? AND value IS ? AND superseded_by IS NULL", (subj, d.predicate, obj, value)).fetchone()
    if row:
        srcs = sorted(set(json.loads(row["source_ids"])) | {sid})
        store.db.execute("UPDATE facts SET source_ids=?, confidence=? WHERE id=?",
                         (json.dumps(srcs), max(row["confidence"], d.confidence), row["id"]))
        return row["id"]
    fid = store.db.execute(
        "INSERT INTO facts(subject_id, predicate, object_id, value, text, source_ids, valid_from, confidence)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (subj, d.predicate, obj, value, d.text, json.dumps([sid]), d.valid_from, d.confidence)).lastrowid
    if TYPES.get(d.predicate, {}).get("single"):
        _supersede(store, subj, d.predicate, fid, d.valid_from)
    return fid


def _supersede(store: Store, subj: str, predicate: str, new_id: int, new_from: str | None) -> None:
    for old in store.db.execute("SELECT id, valid_from FROM facts WHERE subject_id=? AND predicate=? "
                                "AND id!=? AND superseded_by IS NULL", (subj, predicate, new_id)).fetchall():
        if (old["valid_from"] or "") <= (new_from or ""):
            store.db.execute("UPDATE facts SET superseded_by=? WHERE id=?", (new_id, old["id"]))
        else:   # the new fact is older news: it goes straight to history
            store.db.execute("UPDATE facts SET superseded_by=? WHERE id=?", (old["id"], new_id))
            return
