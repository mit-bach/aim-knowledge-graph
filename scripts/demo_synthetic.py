"""Run the trail on a made-up world and show what it found. Fake people only."""
import random

from aimkg import groupings
from aimkg.api_core import AgentAPI
from aimkg.checks import failures, run_checks
from aimkg.config import trail_settings
from aimkg.connectors import synthetic_sources
from aimkg.models import Ref
from aimkg.store import Store
from aimkg.trail import Trail

store = Store(":memory:")
trail = Trail(store, synthetic_sources(), trail_settings(), random.Random(0))
for i in range(1, 6):
    trail.seed(Ref("person", f"Synthetic Person {i:04d}"), "seed: synthetic MIT", synthetic=True)

steps = trail.run(150)
groups = groupings.compute(store)
print("researched this run:", len(steps), "| chained into filings:", sum("synthetic-filings" in s.sources_used for s in steps))
print("graph:", store.counts())
print("groupings (computed):", len(groups), "| largest:", max(len(v) for v in groups.values()))
print("check failures:", failures(run_checks(store)) or "none")
api = AgentAPI(store, trail)
t = api.open_task("Who is Synthetic Person 0001 connected to?", "demo")
print()
print(api.read_dossier(t["starting_dossiers"][0]["id"], "demo: what does the graph know", t["task_id"])["markdown"])
