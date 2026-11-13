"""Records (docs/DESIGN.md §2.4)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal

Trigger = Literal["trail", "refresh", "person"]


def entity_id(kind: str, name: str) -> str:
    return f"{kind}:{hashlib.sha1(f'{kind}|{name.lower().strip()}'.encode()).hexdigest()[:10]}"


@dataclass
class Ref:
    """Someone or something a source names, before we know which dossier it is."""
    kind: str
    name: str
    ids: dict[str, str] = field(default_factory=dict)


@dataclass
class Reason:
    """Why a person is on the frontier. No reason, no research."""
    why: str                         # "co-author of Person B", "seed:openalex", "asked by a user"
    from_id: str | None = None
    predicate: str | None = None
    fact_id: int | None = None


@dataclass
class Record:
    """What one source returned about one person (kept for provenance)."""
    source: str
    url: str
    payload: dict[str, Any]
    trigger: Trigger
    synthetic: bool = False


@dataclass
class FactDraft:
    """A fact as extracted, before it's written to a dossier."""
    subject: Ref
    predicate: str
    object: Ref | None = None
    value: Any = None
    text: str = ""
    valid_from: str | None = None
    confidence: float = 0.8
