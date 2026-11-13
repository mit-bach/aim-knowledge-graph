"""Extractor (DESIGN.md §2.4): evidence -> claims, each with the span it came from."""
from __future__ import annotations

import json
from typing import Any

from .models import Claim, EntityRef


def _ref(d: dict[str, Any]) -> EntityRef:
    return EntityRef(d["kind"], d["name"], d.get("territory_path", []), d.get("ids", {}))


class StructuredExtractor:
    """For sources that return structured records (APIs, the synthetic source)."""

    def extract(self, evidence_row: dict[str, Any]) -> list[Claim]:
        p = json.loads(evidence_row["payload"])
        subject = _ref(p["subject"])
        claims = [Claim(subject, f"attr:{k}", v, 0.9, {"field": k}) for k, v in p.get("attributes", {}).items()]
        for ln in p.get("links", []):
            obj = _ref(ln["object"])
            s, o = (obj, subject) if ln.get("reverse") else (subject, obj)
            claims.append(Claim(s, ln["link_path"], o, ln.get("confidence", 0.5),
                                {"desc": ln.get("desc", "")}))
        return claims


class LLMExtractor:
    """For text (proxy bios, theses, news, personal pages). Week 2.

    Contract: given the evidence text, return claims whose predicate is a link_path from
    schema/link_types.yaml or "attr:<key>", each with the exact span (start, end, text).
    Demographics: only what the person states about themselves. Never infer protected traits.
    """

    def extract(self, evidence_row: dict[str, Any]) -> list[Claim]:
        raise NotImplementedError("LLM extraction is week 2 (docs/DESIGN.md §2.11)")
