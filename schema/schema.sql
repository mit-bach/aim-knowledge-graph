-- AIM knowledge graph, schema v0 (DESIGN.md §2.1). SQLite for week 1; the same shape moves to Postgres.
CREATE TABLE IF NOT EXISTS entities (
  id             TEXT PRIMARY KEY,           -- "person:3f9a…"
  type           TEXT NOT NULL,              -- person | org | school_program | fund | round | work | industry
  name           TEXT NOT NULL,
  desc           TEXT NOT NULL DEFAULT '',
  tags           TEXT NOT NULL DEFAULT '[]', -- JSON list
  territory_path TEXT NOT NULL DEFAULT '[]', -- JSON list, e.g. ["1::mit","2::mit::eecs"]
  ids            TEXT NOT NULL DEFAULT '{}', -- JSON: orcid, openalex, wikidata, dblp, github, sec_cik
  attributes     TEXT NOT NULL DEFAULT '{}', -- JSON: key -> {value, evidence_ids, confidence}
  status         TEXT NOT NULL DEFAULT 'referenced', -- referenced | expanded | stale
  synthetic      INTEGER NOT NULL DEFAULT 0,
  relevance      REAL NOT NULL DEFAULT 0,    -- relevance order: never shown as a number
  expanded_at    TEXT
);
CREATE TABLE IF NOT EXISTS links (
  id           INTEGER PRIMARY KEY,
  from_id      TEXT NOT NULL,
  to_id        TEXT NOT NULL,
  link_path    TEXT NOT NULL,                -- "type::subtype::subsubtype"
  desc         TEXT NOT NULL DEFAULT '',
  valid_from   TEXT,
  valid_to     TEXT,
  evidence_ids TEXT NOT NULL DEFAULT '[]',
  confidence   REAL NOT NULL DEFAULT 0.5,
  UNIQUE (from_id, to_id, link_path)
);
CREATE TABLE IF NOT EXISTS evidence (
  id           TEXT PRIMARY KEY,
  source       TEXT NOT NULL,
  url          TEXT NOT NULL,
  fetched_at   TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  payload      TEXT NOT NULL,                -- JSON; raw blobs live outside git in the private store
  trigger      TEXT NOT NULL,                -- scheduled | graph_asks | person_asks
  reason       TEXT NOT NULL DEFAULT '{}',
  synthetic    INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS claims (
  id          INTEGER PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  span        TEXT NOT NULL DEFAULT '{}',
  subject     TEXT NOT NULL,
  predicate   TEXT NOT NULL,
  object      TEXT NOT NULL,
  confidence  REAL NOT NULL DEFAULT 0.5
);
CREATE TABLE IF NOT EXISTS frontier (
  id         INTEGER PRIMARY KEY,
  entity_id  TEXT NOT NULL,
  territory  TEXT NOT NULL,                  -- top-level territory that owns it, e.g. "1::mit"
  reason     TEXT NOT NULL,                  -- JSON: from_entity, link_path, evidence_id, requested_by, note
  score      REAL NOT NULL,
  hops       INTEGER NOT NULL,
  n_reasons  INTEGER NOT NULL DEFAULT 1,     -- independent reasons pointing at it
  state      TEXT NOT NULL DEFAULT 'queued'  -- queued | holding | in_progress | done | dropped
);
CREATE TABLE IF NOT EXISTS territories (
  path      TEXT PRIMARY KEY,
  parent    TEXT,
  budget    INTEGER NOT NULL DEFAULT 200,    -- lookups per day
  opened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  id        TEXT PRIMARY KEY,
  question  TEXT NOT NULL,
  user_id   TEXT NOT NULL,
  reads     TEXT NOT NULL DEFAULT '[]',      -- JSON list of {entity_id, reason_for_reading}
  lookups   TEXT NOT NULL DEFAULT '[]'
);
