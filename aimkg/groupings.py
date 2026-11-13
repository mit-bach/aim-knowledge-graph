"""Groupings computed from the links, never assigned (docs/DESIGN.md §2.4).

Label propagation over the current links, recomputed as the graph grows. Hubs (a university that
everyone links to) would pull everything into one group, so their links don't vote; a hub keeps a
group of its own. Agents may start from a grouping; facts never go anywhere because of one."""
from __future__ import annotations

import random
from collections import Counter, defaultdict

from .store import Store


def compute(store: Store, rounds: int = 20, hub_share: float = 0.05, seed: int = 0) -> dict[str, list[str]]:
    ids = [r["id"] for r in store.db.execute("SELECT id FROM entities WHERE status!='merged' ORDER BY id")]
    adj: dict[str, set[str]] = defaultdict(set)
    for r in store.db.execute("SELECT subject_id, object_id FROM facts WHERE object_id IS NOT NULL AND superseded_by IS NULL"):
        adj[r["subject_id"]].add(r["object_id"])
        adj[r["object_id"]].add(r["subject_id"])
    degrees = sorted((len(adj[i]) for i in ids), reverse=True)
    cut = max(10, degrees[max(0, int(len(degrees) * hub_share) - 1)] if degrees else 10)
    hubs = {i for i in ids if len(adj[i]) > cut}
    label = {i: i for i in ids}
    rng = random.Random(seed)
    order = [i for i in ids if i not in hubs]
    for _ in range(rounds):
        rng.shuffle(order)
        changed = False
        for i in order:
            votes = Counter(label[n] for n in adj[i] if n in label and n not in hubs)
            if not votes:
                continue
            top = max(votes.values())
            best = min(lab for lab, c in votes.items() if c == top)
            if best != label[i]:
                label[i], changed = best, True
        if not changed:
            break
    store.db.execute("DELETE FROM groupings")
    store.db.executemany("INSERT INTO groupings(entity_id, group_id) VALUES (?,?)", label.items())
    groups: dict[str, list[str]] = defaultdict(list)
    for i, g in label.items():
        groups[g].append(i)
    return dict(groups)
