from aimkg.api_core import AgentAPI


def test_starting_points_never_answers(world):
    store, trail = world
    trail.run(25)
    api = AgentAPI(store, trail)
    t = api.open_task("Who is Synthetic Person 0001 connected to?", "test")
    assert t["starting_dossiers"] and "answer" not in t
    d = api.read_dossier(t["starting_dossiers"][0]["id"], reason="who they work with", task_id=t["task_id"])
    assert d["synthetic"] and all(f["sources"] for f in d["facts"])
    assert "usefulness" not in d and "dossier:" in d["markdown"]
    reads = store.db.execute("SELECT reason FROM reads WHERE task_id=?", (t["task_id"],)).fetchall()
    assert reads[0]["reason"] == "who they work with"


def test_next_degree_goes_out_one_link(world):
    store, trail = world
    trail.run(25)
    api = AgentAPI(store, trail)
    start = api.open_task("Synthetic Person 0001", "test")["starting_dossiers"][0]["id"]
    out = api.next_degree([start])[start]
    assert out and all(r["via"] and r["fact"] for r in out)
    only = api.next_degree([start], link_types=["research"])[start]
    assert all(r["via"].startswith("research") for r in only)


def test_follow_person_queues_them(world):
    store, trail = world
    api = AgentAPI(store, trail)
    r = api.follow_person("Synthetic Person 0399", "asked about, not in the graph")
    assert r["state"] == "queued" and r["frontier_id"]
