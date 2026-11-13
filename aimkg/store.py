"""The People graph, the Evidence archive and the frontier, in one SQLite file (week 1).

Raw data about real people never goes in git: point the store at the team's private store.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Evidence, FrontierItem, Reason

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA.read_text())

    # ---- territories -------------------------------------------------------
    def open_territory(self, path: str, parent: str | None = None, budget: int = 200) -> None:
        self.db.execute("INSERT OR IGNORE INTO territories(path, parent, budget, opened_at) VALUES (?,?,?,?)",
                        (path, parent, budget, _now()))

    def territory_exists(self, path: str) -> bool:
        return self.db.execute("SELECT 1 FROM territories WHERE path=?", (path,)).fetchone() is not None

    def territories(self) -> list[str]:
        return [r["path"] for r in self.db.execute("SELECT path FROM territories ORDER BY opened_at, path")]

    # ---- entities ------------------------------------------------------------
    def upsert_entity(self, eid: str, kind: str, name: str, territory_path: list[str],
                      ids: dict[str, str] | None = None, synthetic: bool = False) -> None:
        row = self.entity(eid)
        if row is None:
            self.db.execute(
                "INSERT INTO entities(id, type, name, territory_path, ids, synthetic) VALUES (?,?,?,?,?,?)",
                (eid, kind, name, json.dumps(territory_path), json.dumps(ids or {}), int(synthetic)))
        elif ids:
            merged = {**row["ids"], **ids}
            self.db.execute("UPDATE entities SET ids=? WHERE id=?", (json.dumps(merged), eid))

    def set_attribute(self, eid: str, key: str, value: Any, evidence_id: str, confidence: float) -> None:
        attrs = self.entity(eid)["attributes"]
        cur = attrs.get(key)
        if cur and cur["value"] == value:
            cur["evidence_ids"] = sorted(set(cur["evidence_ids"]) | {evidence_id})
            cur["confidence"] = max(cur["confidence"], confidence)
        else:
            attrs[key] = {"value": value, "evidence_ids": [evidence_id], "confidence": confidence}
        self.db.execute("UPDATE entities SET attributes=? WHERE id=?", (json.dumps(attrs), eid))
        if key == "desc":
            self.db.execute("UPDATE entities SET desc=? WHERE id=?", (str(value), eid))

    def mark_expanded(self, eid: str) -> None:
        self.db.execute("UPDATE entities SET status='expanded', expanded_at=? WHERE id=?", (_now(), eid))

    def bump_relevance(self, eid: str, by: float = 1.0) -> None:
        self.db.execute("UPDATE entities SET relevance = relevance + ? WHERE id=?", (by, eid))

    def entity(self, eid: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        for k in ("tags", "territory_path", "ids", "attributes"):
            d[k] = json.loads(d[k])
        return d

    def find_by_ids(self, ids: dict[str, str]) -> str | None:
        for key, value in ids.items():
            for r in self.db.execute("SELECT id, ids FROM entities"):
                if json.loads(r["ids"]).get(key) == value:
                    return r["id"]
        return None

    def search(self, words: list[str], limit: int = 5) -> list[str]:
        if not words:
            return []
        clause = " OR ".join("(name LIKE ? OR desc LIKE ?)" for _ in words)
        args: list[str] = []
        for w in words:
            args += [f"%{w}%", f"%{w}%"]
        rows = self.db.execute(f"SELECT id FROM entities WHERE {clause} ORDER BY relevance DESC, name LIMIT ?",
                               (*args, limit))
        return [r["id"] for r in rows]

    # ---- links ---------------------------------------------------------------
    def add_link(self, from_id: str, to_id: str, link_path: str, desc: str,
                 evidence_id: str, confidence: float) -> None:
        row = self.db.execute("SELECT evidence_ids, confidence FROM links WHERE from_id=? AND to_id=? AND link_path=?",
                              (from_id, to_id, link_path)).fetchone()
        if row is None:
            self.db.execute(
                "INSERT INTO links(from_id, to_id, link_path, desc, evidence_ids, confidence) VALUES (?,?,?,?,?,?)",
                (from_id, to_id, link_path, desc, json.dumps([evidence_id]), confidence))
        else:
            ev = sorted(set(json.loads(row["evidence_ids"])) | {evidence_id})
            self.db.execute("UPDATE links SET evidence_ids=?, confidence=? WHERE from_id=? AND to_id=? AND link_path=?",
                            (json.dumps(ev), max(row["confidence"], confidence), from_id, to_id, link_path))

    def links_of(self, eid: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT l.*, e.relevance AS to_rel FROM links l JOIN entities e ON e.id = "
            "CASE WHEN l.from_id=? THEN l.to_id ELSE l.from_id END "
            "WHERE l.from_id=? OR l.to_id=? ORDER BY to_rel DESC, l.id", (eid, eid, eid))
        out = []
        for r in rows:
            d = dict(r)
            d["evidence_ids"] = json.loads(d["evidence_ids"])
            d["other"] = d["to_id"] if d["from_id"] == eid else d["from_id"]
            out.append(d)
        return out

    # ---- evidence ------------------------------------------------------------
    def add_evidence(self, ev: Evidence, reason: Reason) -> str:
        body = json.dumps(ev.payload, sort_keys=True)
        h = hashlib.sha256(body.encode()).hexdigest()
        eid = f"ev:{ev.source}:{h[:12]}"
        self.db.execute(
            "INSERT OR IGNORE INTO evidence(id, source, url, fetched_at, content_hash, payload, trigger, reason, synthetic)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (eid, ev.source, ev.url, _now(), h, body, ev.trigger, json.dumps(reason.__dict__), int(ev.synthetic)))
        return eid

    def evidence(self, evid: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT * FROM evidence WHERE id=?", (evid,)).fetchone()
        return dict(r) if r else None

    # ---- frontier ------------------------------------------------------------
    def push_frontier(self, entity_id: str, territory: str, reason: Reason, score: float,
                      hops: int, state: str = "queued") -> int | None:
        dup = self.db.execute("SELECT id FROM frontier WHERE entity_id=? AND state IN ('queued','holding','in_progress')",
                              (entity_id,)).fetchone()
        if dup:
            # another independent reason for the same entity: count it, and raise its score a little
            self.db.execute("UPDATE frontier SET n_reasons = n_reasons + 1, score = score + 0.1 WHERE id=?",
                            (dup["id"],))
            return None
        cur = self.db.execute(
            "INSERT INTO frontier(entity_id, territory, reason, score, hops, state) VALUES (?,?,?,?,?,?)",
            (entity_id, territory, json.dumps(reason.__dict__), score, hops, state))
        return cur.lastrowid

    def pop_frontier(self, territory: str) -> FrontierItem | None:
        r = self.db.execute("SELECT * FROM frontier WHERE territory=? AND state='queued' ORDER BY score DESC, id LIMIT 1",
                            (territory,)).fetchone()
        if r is None:
            return None
        self.db.execute("UPDATE frontier SET state='in_progress' WHERE id=?", (r["id"],))
        return FrontierItem(r["id"], r["entity_id"], r["territory"], Reason(**json.loads(r["reason"])),
                            r["score"], r["hops"])

    def finish_frontier(self, item_id: int, state: str = "done") -> None:
        self.db.execute("UPDATE frontier SET state=? WHERE id=?", (state, item_id))

    def holding_count(self, territory: str) -> int:
        """Reasons pointing at a territory that isn't open yet (DESIGN.md §1.5)."""
        return self.db.execute("SELECT COALESCE(SUM(n_reasons), 0) FROM frontier WHERE territory=? AND state='holding'",
                               (territory,)).fetchone()[0]

    def release_holding(self, territory: str) -> int:
        return self.db.execute("UPDATE frontier SET state='queued' WHERE territory=? AND state='holding'",
                               (territory,)).rowcount

    def frontier_counts(self) -> dict[str, int]:
        return {r["state"]: r["n"] for r in self.db.execute("SELECT state, COUNT(*) n FROM frontier GROUP BY state")}

    # ---- tasks ---------------------------------------------------------------
    def task(self, tid: str) -> dict[str, Any] | None:
        r = self.db.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        d["reads"] = json.loads(d["reads"])
        d["lookups"] = json.loads(d["lookups"])
        return d

    def save_task(self, tid: str, question: str, user_id: str, reads: list, lookups: list) -> None:
        self.db.execute("INSERT OR REPLACE INTO tasks(id, question, user_id, reads, lookups) VALUES (?,?,?,?,?)",
                        (tid, question, user_id, json.dumps(reads), json.dumps(lookups)))
