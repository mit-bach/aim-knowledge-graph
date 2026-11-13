from aimkg.api_core import AgentAPI


def test_open_get_read(world):
    store, *_ , mit = world
    mit.run(10)
    api = AgentAPI(store)
    t = api.open_task("Who is Synthetic Person 0001 connected to?", user_id="test")
    assert t["init_entities"]
    names = api.get_entities(t["init_entities"])
    assert names
    doc = api.read_entity(t["init_entities"][0], link_verbosity="evidence",
                          reason_for_reading="find their coauthors", task_id=t["task_id"])
    assert doc["synthetic"] is True
    assert all(ln["evidence"] for ln in doc["links"])
    assert "relevance" not in doc


def test_link_filter(world):
    store, *_ , mit = world
    mit.run(10)
    api = AgentAPI(store)
    eid = api.open_task("Synthetic Person 0001", "test")["init_entities"][0]
    doc = api.read_entity(eid, link_filter=(["research"], []))
    assert all(ln["link_path"].startswith("research") for ln in doc["links"])


def test_request_lookup_puts_it_on_the_frontier(world):
    store, *_ = world
    api = AgentAPI(store)
    t = api.open_task("Synthetic Person 9999", "test")
    r = api.request_lookup("Synthetic Person 9999", reason="asked about, not in the graph", task_id=t["task_id"])
    assert r["state"] == "queued" and r["frontier_item_id"]
