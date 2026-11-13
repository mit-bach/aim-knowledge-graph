import random

import pytest

from aimkg.config import trail_settings
from aimkg.connectors import synthetic_sources
from aimkg.models import Ref
from aimkg.store import Store
from aimkg.trail import Trail


@pytest.fixture
def world():
    """A made-up world, seeded with three synthetic MIT people."""
    store = Store(":memory:")
    trail = Trail(store, synthetic_sources(ambiguous_share=0.05), trail_settings(), random.Random(7))
    for n in ("Synthetic Person 0001", "Synthetic Person 0002", "Synthetic Person 0003"):
        trail.seed(Ref("person", n), why="seed: synthetic MIT", synthetic=True)
    return store, trail
