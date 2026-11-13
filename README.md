# AIM knowledge graph

AIM Labs, fall 2026: Amy Lin, Audrey, Dominik Bach, Rebecca.

A knowledge graph of people and their professional networks, built by **following the people trail**. It starts from MIT, and goes out to other institutions, companies and funds, from public data gathered only in ways each source allows. An AI agent navigates the graph through an MCP server.

- `docs/PRD.md`: what we're building, and why.
- `docs/DESIGN.md`: the high-level and low-level design. **Start here.**

## Run it (synthetic people only)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"            # add ",api" for the MCP server
pytest -q                          # the trail grows, every fact is sourced, borders open territories
python scripts/demo_synthetic.py   # one run of the trail on a made-up world
```

## What's here

| Path | What | Design |
|---|---|---|
| `schema/` | SQL schema v0, link types, territory settings | §2.1, §2.2, §1.5 |
| `aimkg/models.py` | entity refs, evidence, claims, reasons, frontier items | §2.1 |
| `aimkg/store.py` | the graph, the evidence archive and the frontier (SQLite for week 1) | §2.5 |
| `aimkg/connectors/` | the connector interface, and a synthetic source; one module per real source | §2.4, §2.6 |
| `aimkg/router.py` | picks the sources that cover an entity, inside their rules | §1.3 |
| `aimkg/control.py` | budgets, hop limits, opening territories | §1.5, §2.3 |
| `aimkg/frontier.py` | frontier scoring: why the next lookup is the next lookup | §2.3 |
| `aimkg/territory.py` | one turn of the trail, border handoffs | §1.6, §2.3 |
| `aimkg/extract.py`, `resolve.py` | evidence → claims; is this someone we have? | §2.4 |
| `aimkg/checks.py` | graph checks | §2.8 |
| `aimkg/api_core.py`, `api.py` | the five Agent API calls, and the MCP server | §2.7 |

## Rules

- **Raw data about people never goes in this repo.** Point the store at the team's private store. The repo holds code, the schema, and synthetic fixtures only.
- **Public data only, gathered only in ways each source allows.** A connector writes its source's rules into `SourceRules`, from the source's own terms page.
- **Demographics: only what a person states publicly.** Never infer protected traits.
- Every change goes in through a PR.
