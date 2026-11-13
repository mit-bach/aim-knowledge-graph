from aimkg import frontier


def test_closer_scores_higher():
    near = frontier.score(hops=0, requested_by="territory", bridging=False, novelty=0.5, evidence=0.8, cost=0.1)
    far = frontier.score(hops=2, requested_by="territory", bridging=False, novelty=0.5, evidence=0.8, cost=0.1)
    assert near > far


def test_asked_for_beats_found():
    found = frontier.score(hops=1, requested_by="territory", bridging=False, novelty=0.5, evidence=0.8, cost=0.1)
    asked = frontier.score(hops=1, requested_by="task", bridging=False, novelty=0.5, evidence=0.8, cost=0.1)
    assert asked > found


def test_bridging_adds():
    a = frontier.score(hops=1, requested_by="territory", bridging=False, novelty=0.5, evidence=0.8, cost=0.1)
    b = frontier.score(hops=1, requested_by="territory", bridging=True, novelty=0.5, evidence=0.8, cost=0.1)
    assert b > a
