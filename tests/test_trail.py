"""Following people grows the graph; every fact keeps its source; the trail is bounded."""
import json

from aimkg.checks import failures, run_checks


def test_trail_grows_from_the_seed(world):
    store, trail = world
    steps = trail.run(30)
    c = store.counts()
    assert len(steps) == 30
    assert c["researched"] >= 20 and c["links"] > c["researched"]
    assert c["frontier"] > 0, "researching people should find more people"


def test_every_frontier_entry_has_a_reason(world):
    store, trail = world
    trail.run(20)
    for r in store.db.execute("SELECT reason FROM frontier"):
        assert json.loads(r["reason"])["why"]


def test_every_fact_is_sourced_and_checks_pass(world):
    store, trail = world
    trail.run(40)
    assert failures(run_checks(store)) == {}


def test_one_source_triggers_another(world):
    store, trail = world
    steps = trail.run(40)
    chained = [s for s in steps if "synthetic-filings" in s.sources_used]
    assert chained, "a filer ID found by the scholar source should make the filings source cover someone"
    for s in chained:
        assert s.sources_used.index("synthetic-scholar") < s.sources_used.index("synthetic-filings")


def test_hops_are_bounded(world):
    store, trail = world
    trail.run(200)
    picked = store.db.execute("SELECT MAX(hops) FROM frontier WHERE state IN ('done','ambiguous')").fetchone()[0]
    assert picked <= trail.cfg["max_hops"]


def test_weak_identity_writes_nothing(world):
    store, trail = world
    trail.run(120)
    for r in store.db.execute("SELECT id FROM entities WHERE status='ambiguous'"):
        assert not store.facts_about(r["id"]), "nothing is written about someone we can't identify"
