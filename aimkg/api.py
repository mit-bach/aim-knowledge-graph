"""The agent's way in, as an MCP server (docs/DESIGN.md §2.6).
Run: pip install -e ".[api]" && python -m aimkg.api --db path/to/graph.sqlite"""
from __future__ import annotations

import argparse

from .api_core import AgentAPI
from .connectors import synthetic_sources
from .store import Store
from .trail import Trail


def build(db_path: str):
    from mcp.server.fastmcp import FastMCP

    store = Store(db_path)
    api = AgentAPI(store, Trail(store, synthetic_sources()))   # swap in the real connectors
    mcp = FastMCP("aim-knowledge-graph")

    @mcp.tool()
    def open_task(question: str, user_id: str, task_id: str | None = None) -> dict:
        """Starting dossiers for this question. Never the answer: explore from here."""
        return api.open_task(question, user_id, task_id)

    @mcp.tool()
    def read_dossier(dossier_id: str, reason: str, task_id: str | None = None, links: str = "facts") -> dict:
        """One dossier: its facts, each with sources, and its links out and in. Say why you're reading it."""
        return api.read_dossier(dossier_id, reason, task_id, links)

    @mcp.tool()
    def next_degree(dossier_ids: list[str], task_id: str | None = None, link_types: list[str] | None = None) -> dict:
        """The dossiers one link away, each with the fact that links it."""
        return api.next_degree(dossier_ids, task_id, link_types)

    @mcp.tool()
    def follow_person(name: str, reason: str, task_id: str | None = None) -> dict:
        """The graph doesn't hold this person: the trail will follow them."""
        return api.follow_person(name, reason, task_id)

    @mcp.tool()
    def continue_task(question: str, task_id: str) -> dict:
        """A follow-up question in the same task."""
        return api.continue_task(question, task_id)

    return mcp


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    build(p.parse_args().db).run()
