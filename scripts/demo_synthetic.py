"""Run the people trail on a synthetic world and print what it found. Fake people only."""
from aimkg.checks import failures, run_checks
from aimkg.connectors import SyntheticConnector
from aimkg.control import Control
from aimkg.models import EntityRef
from aimkg.router import Router
from aimkg.store import Store
from aimkg.territory import TerritoryAgent

store = Store(":memory:")
control = Control.from_config(store)
control.open_threshold = 3
router = Router(store, control, [SyntheticConnector()])
agents = {"1::mit": TerritoryAgent("1::mit", store, control, router)}
for i in range(1, 6):
    agents["1::mit"].seed(EntityRef("person", f"Synthetic Person {i:04d}", ["1::mit"]), "seed:synthetic", True)

for round_ in range(5):
    for t in store.territories():
        agents.setdefault(t, TerritoryAgent(t, store, control, router)).run(10)

print("territories:", store.territories())
print("entities:", store.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
      "expanded:", store.db.execute("SELECT COUNT(*) FROM entities WHERE status='expanded'").fetchone()[0])
print("links:", store.db.execute("SELECT COUNT(*) FROM links").fetchone()[0])
print("frontier:", store.frontier_counts())
print("check failures:", failures(run_checks(store)) or "none")
