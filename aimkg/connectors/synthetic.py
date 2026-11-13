"""Three synthetic sources that chain, the way real ones do (docs/DESIGN.md §2.1):
a directory gives a scholar ID, the scholar source gives co-authors and sometimes a filer ID,
and the filings source gives fund and firm roles. Every person and organization is made up,
every record is flagged synthetic, and nothing touches the network."""
from __future__ import annotations

import hashlib
import random
from typing import Any

from ..models import Reason, Record, Trigger
from .base import Connector, SourceRules

RULES = SourceRules(terms_url="(none: synthetic)", rate_per_sec=1e6, daily_limit=10**6,
                    may_store=["*"], notes="Fake people only. Never mixed with real records.")


def _rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.sha1("|".join(parts).encode()).hexdigest()[:8], 16))


def _person(rng: random.Random) -> dict[str, Any]:
    return {"kind": "person", "name": f"Synthetic Person {rng.randrange(400):04d}"}


def _subject(p: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "person", "name": p["name"], "ids": p["ids"]}


class _Synthetic(Connector):
    rules = RULES

    def _is_synthetic(self, p: dict[str, Any]) -> bool:
        return bool(p.get("synthetic")) or p["name"].startswith("Synthetic ")

    def _record(self, p: dict[str, Any], trigger: Trigger, payload: dict[str, Any]) -> list[Record]:
        return [Record(self.name, f"synthetic://{self.name}/{p['id']}", payload, trigger, synthetic=True)]


class SyntheticDirectory(_Synthetic):
    """Who is this: an affiliation, a degree, what they say about themselves, and a scholar ID."""
    name = "synthetic-directory"

    def __init__(self, ambiguous_share: float = 0.05) -> None:
        self.ambiguous_share = ambiguous_share

    def covers(self, p):  # anyone synthetic we haven't identified yet
        return self._is_synthetic(p) and "synth_scholar" not in p["ids"]

    def lookup(self, p, reason, trigger):
        rng = _rng("dir", p["name"])
        match = 0.5 if rng.random() < self.ambiguous_share else 0.95
        lab = {"kind": "org", "name": f"Synthetic Lab {rng.randrange(12)}"}
        school = {"kind": "org", "name": "MIT"}
        facts = [
            {"subject": _subject(p), "predicate": "research::member_of", "object": lab, "text": f"member of {lab['name']}"},
            {"subject": {"kind": "org", "name": lab["name"]}, "predicate": "org::part_of", "object": school,
             "text": f"{lab['name']} is part of MIT"},
            {"subject": _subject(p), "predicate": "education::degree::phd", "object": school,
             "text": "PhD, MIT", "valid_from": str(2015 + rng.randrange(10))},
            {"subject": _subject(p), "predicate": "self::class_year", "value": 2015 + rng.randrange(12),
             "text": "states their class year"},
        ]
        return self._record(p, trigger, {"match": match, "ids": {"synth_scholar": f"S{rng.randrange(10**6)}"},
                                         "facts": facts})


class SyntheticScholar(_Synthetic):
    """Connections: co-authors and an advisor. Sometimes reveals a filer ID (a role at a fund)."""
    name = "synthetic-scholar"

    def covers(self, p):
        return self._is_synthetic(p) and "synth_scholar" in p["ids"]

    def lookup(self, p, reason, trigger):
        rng = _rng("sch", p["ids"]["synth_scholar"])
        facts = []
        for _ in range(rng.randrange(1, 4)):
            c = _person(rng)
            facts.append({"subject": _subject(p), "predicate": "research::coauthor", "object": c,
                          "text": f"co-authored a synthetic paper with {c['name']}"})
        adv = _person(rng)
        facts.append({"subject": _subject(p), "predicate": "education::advised_by", "object": adv,
                      "text": f"advised by {adv['name']}"})
        ids = {"synth_cik": f"C{rng.randrange(10**6)}"} if rng.random() < 0.3 else {}
        return self._record(p, trigger, {"match": 0.95, "ids": ids, "facts": facts})


class SyntheticFilings(_Synthetic):
    """History in finance: dated roles at funds and firms, and who else sits there."""
    name = "synthetic-filings"

    def covers(self, p):
        return self._is_synthetic(p) and "synth_cik" in p["ids"]

    def lookup(self, p, reason, trigger):
        rng = _rng("fil", p["ids"]["synth_cik"])
        fund = {"kind": "org", "name": f"Synthetic Fund {rng.randrange(5)}"}
        firm = {"kind": "org", "name": f"Synthetic Firm {rng.randrange(8)}"}
        start = 2018 + rng.randrange(6)
        facts = [
            {"subject": _subject(p), "predicate": "employment::current", "object": firm,
             "text": f"worked at {firm['name']}", "valid_from": str(start - 3)},
            {"subject": _subject(p), "predicate": "employment::current", "object": fund,
             "text": f"partner at {fund['name']} since {start}", "valid_from": str(start)},
            {"subject": _subject(p), "predicate": "employment::partner", "object": fund,
             "text": f"partner at {fund['name']}", "valid_from": str(start)},
            {"subject": {"kind": "org", "name": fund["name"]}, "predicate": "finance::invested_in", "object": firm,
             "text": f"{fund['name']} invested in {firm['name']}"},
        ]
        co = _person(rng)
        facts.append({"subject": _subject(p), "predicate": "news::mentioned_with", "object": co,
                      "text": f"named alongside {co['name']} in a synthetic filing"})
        return self._record(p, trigger, {"match": 0.95, "ids": {}, "facts": facts})


def synthetic_sources(ambiguous_share: float = 0.05) -> list[Connector]:
    return [SyntheticDirectory(ambiguous_share), SyntheticScholar(), SyntheticFilings()]
