"""A synthetic source for tests and demos. Every person and organization it makes up is fake,
and every record it returns is flagged synthetic. It never touches the network.

It gives the trail something to follow before the real connectors are built: people with
coauthors, advisors and employers, some of them across a territory border.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any

from ..models import Evidence, Reason, Trigger
from .base import Connector, SourceRules

FIRMS = ["synthetic-firm-a", "synthetic-firm-b"]
COLLEGES = ["synthetic-college-a"]


def _rng(name: str) -> random.Random:
    return random.Random(int(hashlib.sha1(name.encode()).hexdigest()[:8], 16))


def _person(rng: random.Random, territory: str) -> dict[str, Any]:
    return {"kind": "person", "name": f"Synthetic Person {rng.randrange(10_000):04d}",
            "territory_path": [territory]}


class SyntheticConnector(Connector):
    name = "synthetic"
    rules = SourceRules(terms_url="(none: synthetic)", rate_per_sec=1000, daily_limit=10_000,
                        cadence_days=3650, may_store=["*"], notes="Fake people only. Never mixed with real records.")

    def __init__(self, border_rate: float = 0.35) -> None:
        self.border_rate = border_rate

    def covers(self, entity: dict[str, Any]) -> bool:
        return bool(entity.get("synthetic")) or entity["name"].startswith("Synthetic ")

    def lookup(self, entity: dict[str, Any], reason: Reason, trigger: Trigger) -> list[Evidence]:
        rng = _rng(entity["name"])
        territory = entity["territory_path"][0] if entity["territory_path"] else "1::mit"
        subject = {"kind": entity["type"], "name": entity["name"], "territory_path": entity["territory_path"]}
        links: list[dict[str, Any]] = []
        attrs: dict[str, Any] = {}
        if entity["type"] == "person":
            attrs = {"desc": f"synthetic researcher in {territory}", "class_year": 2020 + rng.randrange(8)}
            for _ in range(rng.randrange(1, 4)):
                links.append({"link_path": "research::coauthor", "object": _person(rng, territory),
                              "desc": "co-authored a synthetic paper", "confidence": 0.8})
            links.append({"link_path": "education::advised_by", "object": _person(rng, territory),
                          "desc": "synthetic thesis advisor", "confidence": 0.9})
            if rng.random() < self.border_rate:
                other = rng.choice(FIRMS + COLLEGES)
                kind = "org"
                path = "employment::role::employee" if other in FIRMS else "education::degree::ms"
                links.append({"link_path": path,
                              "object": {"kind": kind, "name": other.replace("-", " ").title(),
                                         "territory_path": [f"1::{other}"]},
                              "desc": "synthetic border crossing", "confidence": 0.7})
        else:
            attrs = {"desc": f"synthetic organization {entity['name']}"}
            for _ in range(rng.randrange(2, 5)):
                links.append({"link_path": "employment::role::employee", "object": _person(rng, territory),
                              "desc": "listed on a synthetic team page", "confidence": 0.7, "reverse": True})
        payload = {"subject": subject, "attributes": attrs, "links": links}
        return [Evidence(source=self.name, url=f"synthetic://{entity['id']}", payload=payload,
                         trigger=trigger, synthetic=True)]
