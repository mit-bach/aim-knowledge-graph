-- AIM knowledge graph, schema v0.2 (docs/DESIGN.md §2.4). One graph: dossiers are rendered from
-- entities + facts; every fact names its sources. SQLite for week 1; the same shape moves to Postgres.
CREATE TABLE IF NOT EXISTS entities (
  id            TEXT PRIMARY KEY,            -- "person:3f9a…"
  kind          TEXT NOT NULL,               -- person | org | work | event
  name          TEXT NOT NULL,
  ids           TEXT NOT NULL DEFAULT '{}',  -- JSON: orcid, openalex, dblp, wikidata, github, sec_cik …
  status        TEXT NOT NULL DEFAULT 'referenced', -- referenced | researched | stale | ambiguous | merged
  merged_into   TEXT,
  synthetic     INTEGER NOT NULL DEFAULT 0,
  usefulness    REAL NOT NULL DEFAULT 0,     -- learned from reads; orders lists; never shown
  researched_at TEXT
);
CREATE TABLE IF NOT EXISTS sources (           -- what was fetched, kept for provenance (not a second graph)
  id           TEXT PRIMARY KEY,
  source       TEXT NOT NULL,
  url          TEXT NOT NULL,
  fetched_at   TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload      TEXT NOT NULL,                -- raw blobs of real people live in the private store, not git
  trigger      TEXT NOT NULL,                -- trail | refresh | person
  synthetic    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS facts (             -- a fact lives in its subject's dossier; a link is a fact with an object
  id            INTEGER PRIMARY KEY,
  subject_id    TEXT NOT NULL,
  predicate     TEXT NOT NULL,               -- "type::subtype", schema/fact_types.yaml
  object_id     TEXT,                        -- another dossier, or NULL for a value
  value         TEXT,                        -- JSON value, or NULL for a link
  text          TEXT NOT NULL DEFAULT '',    -- how the fact reads in the dossier
  source_ids    TEXT NOT NULL DEFAULT '[]',
  valid_from    TEXT,
  valid_to      TEXT,
  confidence    REAL NOT NULL DEFAULT 0.5,
  superseded_by INTEGER
);
CREATE TABLE IF NOT EXISTS frontier (
  id         INTEGER PRIMARY KEY,
  person_id  TEXT NOT NULL,
  reason     TEXT NOT NULL,                  -- JSON: the fact that put them here, or who asked
  hops       INTEGER NOT NULL,
  n_reasons  INTEGER NOT NULL DEFAULT 1,
  asked      INTEGER NOT NULL DEFAULT 0,
  state      TEXT NOT NULL DEFAULT 'queued'  -- queued | claimed | done | ambiguous
);
CREATE TABLE IF NOT EXISTS groupings (         -- computed from the links, never assigned
  entity_id TEXT PRIMARY KEY,
  group_id  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, question TEXT NOT NULL, user_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reads (
  task_id TEXT NOT NULL, dossier_id TEXT NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL
);
