# AIM knowledge graph

AIM Labs, fall 2026: Amy Lin, Audrey, Dominik Bach, Rebecca.

**Following people grows the graph. The graph is what the people trail finds, written as dossiers that agents navigate.**

It starts from MIT, follows each person's connections to the next people, labs, colleges, companies and funds, and writes what public sources say into one graph of dossiers. An AI agent navigates it through an MCP server: it gets starting points, never answers.

- `docs/DESIGN.md`: the high-level and low-level design. **Start here.**
- `docs/PRD.md`: the problem, the users, and the data sources' terms.

## Run it (synthetic people only)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"            # add ",api" for the MCP server
pytest -q
python scripts/demo_synthetic.py   # the trail on a made-up world, and one dossier
```

## What's here

| Path | What | Design |
|---|---|---|
| `schema/` | SQL schema (entities, facts, sources, frontier), fact types, the trail's settings | §2.2, §2.4 |
| `aimkg/connectors/` | the connector interface, and three synthetic sources that chain like real ones | §2.1 |
| `aimkg/research.py` | `research(p)`: IDs first, fan out, stop when dry, write nothing on a weak match | §2.3 |
| `aimkg/trail.py` | the frontier, `select` (expected information gain, a little exploration), the loop | §2.2 |
| `aimkg/upkeep.py` | writing facts to dossiers: one fact for many sources, newer supersedes older, merges | §2.4, §2.5 |
| `aimkg/groupings.py` | groupings computed from the links, never assigned | §2.4 |
| `aimkg/checks.py` | checks after each batch | §2.5 |
| `aimkg/api_core.py`, `api.py` | the agent's way in: `open_task`, `read_dossier`, `next_degree`, `follow_person`, `continue_task` | §2.6 |
| `eval/` | the three arms, and the question format | §2.7 |

## Rules

- **Raw data about people never goes in this repo.** The repo holds code, the schema, and synthetic fixtures only.
- **Public data only, gathered only in ways each source allows.** Each connector writes its source's rules from that source's own terms page.
- **Demographics only as people state them publicly.** Never infer protected traits.
- Every change goes in through a PR.
