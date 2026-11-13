import random

from aimkg.config import trail_settings
from aimkg.connectors import synthetic_sources
from aimkg.models import Ref
from aimkg.store import Store
from aimkg.trail import Trail


def _trail(explore):
    cfg = {**trail_settings(), "explore_share": explore}
    store = Store(":memory:")
    t = Trail(store, synthetic_sources(0.0), cfg, random.Random(1))
    for n in ("Synthetic Person 0101", "Synthetic Person 0102"):
        t.seed(Ref("person", n), "seed", synthetic=True)
    return store, t


def test_asked_for_jumps_the_queue():
    store, t = _trail(0.0)
    t.run(3)
    t.ask("Synthetic Person 0333", "a user asked who they are")
    assert store.entity(t.select()["person_id"])["name"] == "Synthetic Person 0333"


def test_exploration_still_picks_from_the_frontier():
    store, t = _trail(1.0)
    t.run(5)
    e = t.select()
    assert e is not None and e["state"] == "queued"
