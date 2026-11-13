"""Records from DESIGN.md §2.1."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal

Trigger = Literal["scheduled", "graph_asks", "person_asks"]
RequestedBy = Literal["seed", "territory", "task", "person", "refresh"]


def entity_id(kind: str, name: str, territory: str = "") -> str:
    digest = hashlib.sha1(f"{kind}|{name.lower().strip()}|{territory}".encode()).hexdigest()[:10]
    return f"{kind}:{digest}"


def top_territory(path: list[str]) -> str:
    """["1::mit", "2::mit::eecs"] -> "1::mit"."""
    return path[0] if path else ""


@dataclass
class Reason:
    """Why something is on the frontier. No reason, no lookup."""
    requested_by: RequestedBy
    note: str
    from_entity: str | None = None
    link_path: str | None = None
    evidence_id: str | None = None


@dataclass
class EntityRef:
    """An entity as a source or a claim names it, before resolution."""
    kind: str
    name: str
    territory_path: list[str] = field(default_factory=list)
    ids: dict[str, str] = field(default_factory=dict)


@dataclass
class Evidence:
    source: str
    url: str
    payload: dict[str, Any]
    trigger: Trigger
    synthetic: bool = False


@dataclass
class Claim:
    """One fact from one piece of evidence, with the span it came from."""
    subject: EntityRef
    predicate: str                     # a link_path, or "attr:<key>"
    object: EntityRef | Any
    confidence: float = 0.5
    span: dict[str, Any] = field(default_factory=dict)


@dataclass
class FrontierItem:
    id: int
    entity_id: str
    territory: str
    reason: Reason
    score: float
    hops: int
