"""Resolver (DESIGN.md §2.4): is this someone we already have?

Week 1: external IDs first, then (kind, normalized name, top territory). Week 2 adds blocking
on name + affiliation + years, an LLM to adjudicate, and a review queue a teammate checks.
"""
from __future__ import annotations

from .models import EntityRef, entity_id, top_territory
from .store import Store


class Resolver:
    def __init__(self, store: Store) -> None:
        self.store = store

    def resolve(self, ref: EntityRef, synthetic: bool = False) -> str:
        if ref.ids:
            found = self.store.find_by_ids(ref.ids)
            if found:
                return found
        eid = entity_id(ref.kind, ref.name, top_territory(ref.territory_path))
        self.store.upsert_entity(eid, ref.kind, ref.name, ref.territory_path, ref.ids, synthetic)
        return eid
