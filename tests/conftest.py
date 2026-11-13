import pytest

from aimkg.connectors import SyntheticConnector
from aimkg.control import Control
from aimkg.models import EntityRef
from aimkg.router import Router
from aimkg.store import Store
from aimkg.territory import TerritoryAgent


@pytest.fixture
def world():
    """A synthetic world: the MIT territory, seeded with three made-up people."""
    store = Store(":memory:")
    control = Control.from_config(store)
    router = Router(store, control, [SyntheticConnector(border_rate=0.6)])
    mit = TerritoryAgent("1::mit", store, control, router)
    for n in ("Synthetic Person 0001", "Synthetic Person 0002", "Synthetic Person 0003"):
        mit.seed(EntityRef("person", n, ["1::mit"]), note="seed:synthetic", synthetic=True)
    return store, control, router, mit
