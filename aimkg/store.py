"""The graph: entities and their facts (dossiers), the sources behind them, the frontier, and tasks.
Point it at the team's private store; raw data about real people never goes in git."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Record, Ref, entity_id

ROOT = Path(__file__).resolve().parent.parent


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((ROOT / "schema" / "schema.sql").read_text())

    # ---- entities -----------------------------------------------------------------
    def entity(self, eid: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        d["ids"] = json.loads(d["ids"])
        if d["status"] == "merged" and d["merged_into"]:
            return self.entity(d["merged_into"])
        return d

    def resolve(self, ref: Ref, synthetic: bool = False) -> str:
        """IDs first; then kind + exact name (week 1). Week 2 adds affiliation and years."""
        for key, val in ref.ids.items():
            hit = self.db.execute("SELECT id FROM entities WHERE status!='merged' AND json_extract(ids, ?)=?",
                                  (f"$.{key}", val)).fetchone()
            if hit:
                self.add_ids(hit["id"], ref.ids)
                return hit["id"]
        eid = entity_id(ref.kind, ref.name)
        existing = self.entity(eid)
        if existing:
            self.add_ids(existing["id"], ref.ids)
            return existing["id"]
        self.db.execute("INSERT INTO entities(id, kind, name, ids, synthetic) VALUES (?,?,?,?,?)",
                        (eid, ref.kind, ref.name, json.dumps(ref.ids), int(synthetic)))
        return eid

    def add_ids(self, eid: str, ids: dict[str, str]) -> list[str]:
        """Add IDs to a dossier. If another dossier already holds one of them, merge it in."""
        if not ids:
            return []
        e = self.entity(eid)
        merged = []
        for key, val in ids.items():
            for r in self.db.execute("SELECT id FROM entities WHERE id!=? AND status!='merged' AND json_extract(ids, ?)=?",
                                     (e["id"], f"$.{key}", val)).fetchall():
                self.merge(r["id"], e["id"])
                merged.append(r["id"])
        e = self.entity(eid)
        self.db.execute("UPDATE entities SET ids=? WHERE id=?", (json.dumps({**e["ids"], **ids}), e["id"]))
        return merged

    def merge(self, loser: str, winner: str) -> None:
        """Upkeep: two dossiers are one person. Move the facts, keep a pointer."""
        self.db.execute("UPDATE facts SET subject_id=? WHERE subject_id=?", (winner, loser))
        self.db.execute("UPDATE facts SET object_id=? WHERE object_id=?", (winner, loser))
        self.db.execute("UPDATE frontier SET state='done' WHERE person_id=? AND state='queued'", (loser,))
        self.db.execute("UPDATE entities SET status='merged', merged_into=? WHERE id=?", (winner, loser))

    def set_status(self, eid: str, status: str) -> None:
        extra = ", researched_at=?" if status == "researched" else ""
        args = (status, now(), eid) if extra else (status, eid)
        self.db.execute(f"UPDATE entities SET status=?{extra} WHERE id=?", args)

    def bump_usefulness(self, eid: str, by: float = 1.0) -> None:
        self.db.execute("UPDATE entities SET usefulness = usefulness + ? WHERE id=?", (by, eid))

    def search(self, words: list[str], limit: int = 5) -> list[str]:
        """Dossiers whose names match the most words, then the most useful."""
        if not words:
            return []
        clause = " OR ".join("name LIKE ?" for _ in words)
        rows = self.db.execute(f"SELECT id, name, usefulness FROM entities WHERE status!='merged' AND ({clause})",
                               [f"%{w}%" for w in words]).fetchall()
        lw = [w.lower() for w in words]
        ranked = sorted(rows, key=lambda r: (-sum(w in r["name"].lower() for w in lw), -r["usefulness"], r["name"]))
        return [r["id"] for r in ranked[:limit]]

    # ---- sources ------------------------------------------------------------------
    def add_source(self, rec: Record) -> str:
        body = json.dumps(rec.payload, sort_keys=True)
        h = hashlib.sha256(body.encode()).hexdigest()
        sid = f"src:{rec.source}:{h[:12]}"
        self.db.execute("INSERT OR IGNORE INTO sources(id, source, url, fetched_at, content_hash, payload, trigger, synthetic)"
                        " VALUES (?,?,?,?,?,?,?,?)", (sid, rec.source, rec.url, now(), h, body, rec.trigger, int(rec.synthetic)))
        return sid

    def source(self, sid: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT id, source, url, fetched_at FROM sources WHERE id=?", (sid,)).fetchone()
        return dict(r) if r else None

    # ---- facts --------------------------------------------------------------------
    def facts_about(self, eid: str, include_superseded: bool = False) -> list[dict[str, Any]]:
        q = "SELECT * FROM facts WHERE subject_id=?" + ("" if include_superseded else " AND superseded_by IS NULL")
        return [self._fact(r) for r in self.db.execute(q + " ORDER BY id", (eid,))]

    def facts_pointing_to(self, eid: str) -> list[dict[str, Any]]:
        return [self._fact(r) for r in self.db.execute(
            "SELECT * FROM facts WHERE object_id=? AND superseded_by IS NULL ORDER BY id", (eid,))]

    @staticmethod
    def _fact(r: sqlite3.Row) -> dict[str, Any]:
        d = dict(r)
        d["source_ids"] = json.loads(d["source_ids"])
        d["value"] = json.loads(d["value"]) if d["value"] is not None else None
        return d

    def neighbors(self, eid: str) -> list[tuple[str, dict[str, Any]]]:
        """(other dossier, the fact that links them), both directions, current facts only."""
        out = [(f["object_id"], f) for f in self.facts_about(eid) if f["object_id"]]
        out += [(f["subject_id"], f) for f in self.facts_pointing_to(eid)]
        return out

    # ---- frontier -----------------------------------------------------------------
    def frontier_add(self, person_id: str, reason: dict, hops: int, asked: bool = False) -> int | None:
        row = self.db.execute("SELECT id FROM frontier WHERE person_id=? AND state IN ('queued','claimed')",
                              (person_id,)).fetchone()
        if row:   # another independent reason for the same person
            self.db.execute("UPDATE frontier SET n_reasons=n_reasons+1, asked=MAX(asked, ?), hops=MIN(hops, ?) WHERE id=?",
                            (int(asked), hops, row["id"]))
            return None
        if self.entity(person_id)["status"] in ("researched", "ambiguous"):
            return None
        return self.db.execute("INSERT INTO frontier(person_id, reason, hops, asked) VALUES (?,?,?,?)",
                               (person_id, json.dumps(reason), hops, int(asked))).lastrowid

    def frontier_queued(self) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT * FROM frontier WHERE state='queued' ORDER BY id")
        return [{**dict(r), "reason": json.loads(r["reason"])} for r in rows]

    def frontier_set(self, fid: int, state: str) -> None:
        self.db.execute("UPDATE frontier SET state=? WHERE id=?", (state, fid))

    def counts(self) -> dict[str, Any]:
        q = lambda s: self.db.execute(s).fetchone()[0]  # noqa: E731
        return {"dossiers": q("SELECT COUNT(*) FROM entities WHERE status!='merged'"),
                "researched": q("SELECT COUNT(*) FROM entities WHERE status='researched'"),
                "facts": q("SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"),
                "links": q("SELECT COUNT(*) FROM facts WHERE object_id IS NOT NULL AND superseded_by IS NULL"),
                "frontier": q("SELECT COUNT(*) FROM frontier WHERE state='queued'"),
                "ambiguous": q("SELECT COUNT(*) FROM entities WHERE status='ambiguous'")}
