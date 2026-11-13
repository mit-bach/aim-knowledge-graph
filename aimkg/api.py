"""The Agent API as an MCP server (DESIGN.md §2.7). Run: python -m aimkg.api --db path/to/graph.sqlite"""
from __future__ import annotations

import argparse

from .api_core import AgentAPI
from .store import Store


def build(db_path: str):
    from mcp.server.fastmcp import FastMCP  # pip install -e ".[api]"

    api = AgentAPI(Store(db_path))
    mcp = FastMCP("aim-knowledge-graph")

    @mcp.tool()
    def open_task(question: str, user_id: str, task_id: str | None = None) -> dict:
        """Open a task. Returns entities to read first, and the territory filter later calls use."""
        return api.open_task(question, user_id, task_id)

    @mcp.tool()
    def get_entities(entity_ids: list[str]) -> dict:
        """Names, territory paths and link-type counts for a list of entities: what to read next."""
        return api.get_entities(entity_ids)

    @mcp.tool()
    def read_entity(entity_id: str, reason_for_reading: str, task_id: str | None = None,
                    territory_include: list[str] | None = None, territory_exclude: list[str] | None = None,
                    link_include: list[str] | None = None, link_exclude: list[str] | None = None,
                    link_verbosity: str = "description") -> dict:
        """One entity, its attributes and its links, each traceable to a source."""
        tf = (territory_include or [], territory_exclude or []) if (territory_include or territory_exclude) else None
        lf = (link_include or [], link_exclude or []) if (link_include or link_exclude) else None
        return api.read_entity(entity_id, tf, lf, None, link_verbosity, reason_for_reading, task_id)

    @mcp.tool()
    def continue_task(question: str, task_id: str) -> dict:
        """Continue a task with a follow-up question."""
        return api.continue_task(question, task_id)

    @mcp.tool()
    def request_lookup(name_or_id: str, reason: str, task_id: str | None = None) -> dict:
        """The graph doesn't hold it: put it on the frontier, with your reason."""
        return api.request_lookup(name_or_id, reason, task_id)

    return mcp


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    build(p.parse_args().db).run()
