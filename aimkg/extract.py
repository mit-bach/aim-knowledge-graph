"""Records -> fact drafts (docs/DESIGN.md §2.3)."""
from __future__ import annotations

from typing import Any

from .models import FactDraft, Record, Ref


def _ref(d: dict[str, Any] | None) -> Ref | None:
    return Ref(d["kind"], d["name"], d.get("ids", {})) if d else None


def structured(rec: Record) -> list[FactDraft]:
    """For sources that return structured records (APIs, dumps, the synthetic sources)."""
    return [FactDraft(subject=_ref(f["subject"]), predicate=f["predicate"], object=_ref(f.get("object")),
                      value=f.get("value"), text=f.get("text", ""), valid_from=f.get("valid_from"),
                      confidence=f.get("confidence", 0.8))
            for f in rec.payload.get("facts", [])]


def from_text(rec: Record) -> list[FactDraft]:
    """For pages and filings in prose. Week 2: an LLM returns facts whose predicate is in
    schema/fact_types.yaml, each with the exact span it came from. Self-stated attributes only;
    never infer protected traits."""
    raise NotImplementedError("text extraction is week 2 (docs/DESIGN.md §2.9)")
