"""The agent's way in (docs/DESIGN.md §2.6): starting points, never answers. The agent explores,
giving a reason for every read. Lists come back ordered by learned usefulness; the score itself
is never returned."""
from __future__ import annotations

import re
import uuid
from typing import Any

from .store import Store, now
from .trail import Trail

STOP = {"the", "a", "an", "of", "to", "is", "who", "what", "how", "and", "in", "at", "for", "with", "are", "does"}


def _words(q: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9]+", q) if w.lower() not in STOP and len(w) > 2]


class AgentAPI:
    def __init__(self, store: Store, trail: Trail) -> None:
        self.store, self.trail = store, trail

    def _card(self, eid: str) -> dict[str, Any]:
        e = self.store.entity(eid)
        facts = self.store.facts_about(e["id"])
        line = facts[0]["text"] if facts else ""
        return {"id": e["id"], "name": e["name"], "kind": e["kind"], "line": line}

    # ---- open_task / continue_task ---------------------------------------------------
    def open_task(self, question: str, user_id: str, task_id: str | None = None) -> dict[str, Any]:
        tid = task_id or uuid.uuid4().hex[:12]
        self.store.db.execute("INSERT OR IGNORE INTO tasks(id, question, user_id) VALUES (?,?,?)", (tid, question, user_id))
        starts = self.store.search(_words(question), limit=5)
        if len(starts) < 3:   # fill from the most useful dossiers in the same computed groupings
            groups = {r["group_id"] for r in self.store.db.execute(
                f"SELECT group_id FROM groupings WHERE entity_id IN ({','.join('?' * len(starts))})", starts)} if starts else set()
            if groups:
                more = self.store.db.execute(
                    f"SELECT e.id FROM entities e JOIN groupings g ON g.entity_id=e.id WHERE g.group_id IN "
                    f"({','.join('?' * len(groups))}) AND e.status='researched' ORDER BY e.usefulness DESC LIMIT 5",
                    tuple(groups)).fetchall()
                starts += [r["id"] for r in more if r["id"] not in starts]
        return {"task_id": tid, "starting_dossiers": [self._card(e) for e in starts[:5]]}

    def continue_task(self, question: str, task_id: str) -> dict[str, Any]:
        t = self.store.db.execute("SELECT user_id FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self.open_task(question, t["user_id"] if t else "unknown", task_id)

    # ---- read_dossier ------------------------------------------------------------------
    def read_dossier(self, dossier_id: str, reason: str, task_id: str | None = None,
                     links: str = "facts") -> dict[str, Any]:
        e = self.store.entity(dossier_id)
        if e is None:
            return {"error": f"no dossier {dossier_id}; use follow_person"}
        self.store.db.execute("INSERT INTO reads(task_id, dossier_id, reason, at) VALUES (?,?,?,?)",
                              (task_id or "", e["id"], reason, now()))
        self.store.bump_usefulness(e["id"], 0.5)
        facts = []
        for f in self.store.facts_about(e["id"]):
            item: dict[str, Any] = {"text": f["text"], "type": f["predicate"], "since": f["valid_from"],
                                    "sources": [self.store.source(s) for s in f["source_ids"]]}
            if f["object_id"] and links != "none":
                o = self.store.entity(f["object_id"])
                item["to"] = {"id": o["id"], "name": o["name"]} if links == "facts" else o["name"]
            if f["value"] is not None:
                item["value"] = f["value"]
            facts.append(item)
        linked_from = [{"id": self.store.entity(f["subject_id"])["id"], "name": self.store.entity(f["subject_id"])["name"],
                        "type": f["predicate"], "text": f["text"]} for f in self.store.facts_pointing_to(e["id"])]
        doc = {"id": e["id"], "name": e["name"], "kind": e["kind"], "ids": e["ids"], "status": e["status"],
               "synthetic": bool(e["synthetic"]), "facts": facts, "linked_from": linked_from}
        doc["markdown"] = render(doc)
        return doc

    # ---- next_degree: search outward one degree at a time ----------------------------------
    def next_degree(self, dossier_ids: list[str], task_id: str | None = None,
                    link_types: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for did in dossier_ids:
            rows = []
            for other, f in self.store.neighbors(did):
                if link_types and not any(f["predicate"].startswith(t) for t in link_types):
                    continue
                o = self.store.entity(other)
                rows.append((o["usefulness"], {"to": {"id": o["id"], "name": o["name"], "kind": o["kind"]},
                                               "via": f["predicate"], "fact": f["text"]}))
            out[did] = [r for _, r in sorted(rows, key=lambda x: -x[0])]
        return out

    # ---- follow_person ---------------------------------------------------------------
    def follow_person(self, name: str, reason: str, task_id: str | None = None) -> dict[str, Any]:
        return self.trail.ask(name, reason)


def render(doc: dict[str, Any]) -> str:
    """A dossier as an agent reads it."""
    lines = [f"dossier: {doc['name']}    ({doc['kind']}{', synthetic' if doc['synthetic'] else ''})"]
    if doc["ids"]:
        lines.append("  ids: " + ", ".join(f"{k} {v}" for k, v in doc["ids"].items()))
    for f in doc["facts"]:
        to = f" → [{f['to']['name'] if isinstance(f.get('to'), dict) else f['to']}]" if f.get("to") else ""
        src = ", ".join(s["source"] for s in f["sources"] if s)
        since = f" ({f['since']})" if f.get("since") else ""
        val = f": {f['value']}" if f.get("value") is not None else ""
        lines.append(f"  - {f['text']}{val}{since}{to}    source: {src}")
    if doc["linked_from"]:
        lines.append("  linked from: " + " · ".join(f"[{x['name']}] {x['type']}" for x in doc["linked_from"]))
    return "\n".join(lines)
