"""The people trail on a synthetic world: it grows, every fact has a source, and it crosses borders."""
from aimkg.checks import failures, run_checks
from aimkg.territory import TerritoryAgent


def test_trail_grows_with_reasons(world):
    store, control, router, mit = world
    turns = mit.run(30)
    assert turns, "the MIT territory should take turns"
    expanded = store.db.execute("SELECT COUNT(*) FROM entities WHERE status='expanded'").fetchone()[0]
    links = store.db.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    assert expanded >= 3 and links > expanded
    # every frontier item carries a reason
    for r in store.db.execute("SELECT reason FROM frontier"):
        assert '"requested_by"' in r["reason"]


def test_every_fact_is_sourced(world):
    store, *_ , mit = world
    mit.run(30)
    assert failures(run_checks(store)) == {}


def test_border_crossing_opens_a_territory(world):
    store, control, router, mit = world
    control.open_threshold = 2
    mit.run(60)
    opened = [t for t in store.territories() if t != "1::mit"]
    assert opened, "enough reasons pointing past MIT's border should open a territory"
    for t in opened:
        agent = TerritoryAgent(t, store, control, router)
        agent.run(5)
    assert failures(run_checks(store)) == {}


def test_hop_limit_holds(world):
    store, control, *_ , mit = world
    mit.run(200)
    max_inside = store.db.execute("SELECT MAX(hops) FROM frontier WHERE territory='1::mit'").fetchone()[0]
    assert max_inside <= control.max_hops_inside
