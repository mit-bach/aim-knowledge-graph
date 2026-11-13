"""The graph's structure is what the facts say: dossiers, links on facts, upkeep in the same step."""
from aimkg import groupings, upkeep
from aimkg.models import FactDraft, Record, Ref


def _src(store, name="unit"):
    return store.add_source(Record(name, f"test://{name}", {"n": name}, "trail", synthetic=True))


def test_links_exist_only_as_facts(world):
    store, trail = world
    trail.run(20)
    n_links = store.db.execute("SELECT COUNT(*) FROM facts WHERE object_id IS NOT NULL").fetchone()[0]
    assert n_links > 0
    tables = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {"territories", "links", "partitions"} & tables, "no structure besides facts"


def test_newer_current_role_supersedes_older(world):
    store, _ = world
    s1, s2 = _src(store, "a"), _src(store, "b")
    p = Ref("person", "Synthetic Person 9001")
    upkeep.write(store, [(FactDraft(p, "employment::current", Ref("org", "Synthetic Firm X"), valid_from="2019"), s1)], True)
    upkeep.write(store, [(FactDraft(p, "employment::current", Ref("org", "Synthetic Fund Y"), valid_from="2022"), s2)], True)
    pid = store.resolve(p)
    current = [f for f in store.facts_about(pid) if f["predicate"] == "employment::current"]
    history = [f for f in store.facts_about(pid, include_superseded=True) if f["predicate"] == "employment::current"]
    assert len(current) == 1 and store.entity(current[0]["object_id"])["name"] == "Synthetic Fund Y"
    assert len(history) == 2, "the old role stays, as history"


def test_same_fact_from_two_sources_is_one_fact(world):
    store, _ = world
    s1, s2 = _src(store, "a"), _src(store, "b")
    d = FactDraft(Ref("person", "Synthetic Person 9002"), "research::member_of", Ref("org", "Synthetic Lab 1"))
    upkeep.write(store, [(d, s1)], True)
    upkeep.write(store, [(d, s2)], True)
    facts = store.facts_about(store.resolve(d.subject))
    assert len(facts) == 1 and set(facts[0]["source_ids"]) == {s1, s2}


def test_shared_id_merges_two_dossiers(world):
    store, _ = world
    a = store.resolve(Ref("person", "Synthetic Person 9003"))
    b = store.resolve(Ref("person", "S. Person 9003"))
    store.add_ids(a, {"orcid": "0000-TEST"})
    store.add_ids(b, {"orcid": "0000-TEST"})
    assert store.entity(b)["id"] == store.entity(a)["id"]


def test_groupings_are_computed_from_links(world):
    store, trail = world
    trail.run(40)
    groups = groupings.compute(store)
    assert groups and sum(len(v) for v in groups.values()) == store.counts()["dossiers"]
