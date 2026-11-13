# AIM knowledge graph: high-level and low-level design

**AIM Labs, fall 2026.** Amy Lin, Audrey, Dominik Bach, Rebecca. Draft 0.2, 2026-11-13. It replaces draft 0.1 and the PRD's pipeline and agent sections (§6–§9). The PRD still holds the problem, the users, and the data sources' terms.

**How to read it:**
- **[kickoff mm:ss]:** said at the 11-08 kickoff.
- **[Dominik, date]:** his direction since then.
- **Proposal:** new in this draft, and not yet agreed by the team.

The levels follow each other: Part 1 is the high-level design, and each system in it opens into a low-level design in Part 2. §2.3 goes one level lower still.

---

# Part 1. High-level design

**Following people grows the graph. The graph is what the people trail finds, written as dossiers that agents navigate.** [Dominik, 11-12 and 11-13]

```
                 ┌──────────── a finding in one source can trigger a lookup in another ───────────┐
                 ▼                                                                                 │
 [Sources] ◄──► [The trail] ──facts──► [The graph: dossiers + links] ◄──► [The agent's way in] ◄── a person / an agent
                    ▲                         │      ▲                            │
                    │                    upkeep (same loop)                        │ "follow this person"
                    └──────────────────────────────────────────────────────────────┘
                                         [Evals] score it all against the use cases
```

| System | What it does | Opens into |
|---|---|---|
| **Sources** | One connector per allowed source, each a black box behind the same interface. A finding in one source can trigger a lookup in another. | §2.1 |
| **The trail** | The exploration algorithm, and how the graph propagates. It keeps one frontier of people, each with a reason, picks the next by expected information gain, researches them, and puts everyone they lead to on the frontier. | §2.2, §2.3 |
| **The graph** | One graph, written as the trail goes. Its unit is the **dossier**: one per person, organization, work or event. Its structure is what the facts say, never the trail's path. | §2.4 |
| **Upkeep** | Runs in the same loop as the trail: building and keeping the graph are one process. Each new fact revises the dossiers it touches. | §2.5 |
| **The agent's way in** | An MCP server. It gives starting dossiers, never answers. The agent walks links, with a reason for every read, and can ask the trail to follow someone missing. | §2.6 |
| **Evals** | Work backwards from the use cases. The graph has to beat an agent with only web search and the sources' raw dumps. | §2.7 |

**Why the trail and the structure are kept apart:** "We follow the people to explore and expand upon the graph, but the structure of the graph is not based upon that. It's based on the information that's found when following the people" [Dominik, 11-13]. The trail decides **what gets looked at**. The facts decide **what the graph looks like**. There are no partitions or territories. Any grouping used for navigation, like a research area, a deal network or an alumni cluster, is computed from the links afterwards (§2.4).

---

# Part 2. Low-level designs

## 2.1 Sources

**Each connector** answers `covers(person)`, `lookup(person, reason)` and its `rules` (what we may store, rate limits, refresh cadence), written from the source's own terms page.

**Three triggers.** Nothing else calls a source.

| Trigger | When |
|---|---|
| **The trail asks** | A person is being researched. |
| **Refresh** | A dossier's facts are older than their source's cadence. |
| **A person asks** | Someone (or their agent) asks about a person the graph doesn't hold: `follow_person`. |

**One source triggers another (proposal).** A lookup can return new IDs, and a new ID makes another source cover the person. For example, OpenAlex gives an ORCID iD, ORCID gives a past role at a fund, and that makes SEC filings cover them. Research keeps fanning out like this until no source has anything new (§2.3).

**Which sources move the trail.** Checked 2026-11-12 against each source's terms, robots.txt and API docs. Nothing was fetched about anyone. The verdicts are proposals; the PRD's §5 has each source's terms.

| Hop | Sources, best first |
|---|---|
| person → person | DBLP co-authorship (computer science, IDs already matched up, CC0 dump) · OpenAlex and ORCID · arXiv and Crossref co-authors · DSpace@MIT advisor → student · GitHub co-contributors (noisy) |
| person → organization | DSpace@MIT department · OpenAlex and ORCID affiliations · GitHub public org membership · MIT News mentions |
| organization → person | lab rosters (for example CSAIL `/people`) · OpenCourseWare instructors · SEC EDGAR (officers, directors, fund owners) · company team pages |
| identity | ORCID (lists other IDs) · Wikidata (external IDs) · OpenAlex · DBLP |

- **This month (proposal):**
  - OpenAlex, DBLP (the dump), ORCID, Wikidata and SEC EDGAR (the bulk files);
  - lab rosters, through a single-page fetcher;
  - DSpace@MIT once MIT Libraries says yes in writing.
- **One web search per person,** to find their own pages: Tavily, with care (it's free for students), or Brave, used only in the moment, since its terms ban building a database from results. What we store comes from the page found, under that page's terms.
- **Don't use:** Google Scholar, Exa, Common Crawl for people, Engage, People Data Labs, Proxycurl. LinkedIn and Crunchbase get synthetic stand-ins.
- **What the sources' rules mean for us:**
  - GitHub: repo- and org-level edges only, and no commit emails.
  - A suppressed MIT directory entry is an opt-out.
  - Firecrawl's terms ban background-check use, so we don't use it for due diligence.
  - **No inferred protected traits.**
- **How far "all MIT students" reaches:** the allowed sources reach researchers and graduate students well, and undergraduates thinly. The synthetic layer stands in for undergraduates in statistics.

## 2.2 The trail

```
G = the graph (dossiers)       F = the frontier: people not yet researched (or stale), each with its reason

seed F with MIT people from allowed sources                  # MIT first [kickoff 15:27]
while budget remains:
    p     = select(F)                                        # why this person, now
    facts = research(p)                                      # §2.3
    write(G, facts)  and  upkeep(G, facts)                   # §2.4, §2.5: one step
    for q in people named in facts, not yet researched:
        F.add(q, reason = the fact that names q)
```

**`select(F)`: why this person next.** "We need to have a reason to find the data" [Dominik, 11-12]. Every frontier entry carries the fact that put it there. The score is expected information gain (proposal):

| Term | Raises the score when … |
|---|---|
| novelty | most of their neighbourhood is still unknown |
| bridging | they connect parts of the graph that are otherwise far apart ("the people trail will, I believe, show insightful outcomes" [Dominik, 11-12]) |
| relevance | they're close to the seed, or someone asked about them (`follow_person` triples it) |
| evidence | several independent facts point to them |
| cost (subtracted) | their research needs many calls |

About 1 pick in 10 is random, so the trail doesn't get stuck in one cluster.

**Bounds (proposal):**
- a daily research budget, and a cap per person;
- relevance decays with hops from the seed;
- new seeds (another college, a set of firms) are started on purpose, not drifted into;
- a researched person goes back on the frontier when they go stale.

**Running it:** several explorer agents share the one frontier. Each claims a person, so no two research the same one.

## 2.3 One person's research (lower still)

"This given algorithm, which is yet to be described" [Dominik, 11-12], written out as a proposal. Researching a person answers five questions, in order:

1. **Who is this?** Anchor the identity from what the frontier knows: the name, plus the fact that brought them. Then gather stable IDs (ORCID, OpenAlex, DBLP, Wikidata, GitHub, SEC CIK). **If the match is weak, nothing is written.** The person waits in an ambiguity queue for a teammate to check, because one wrong merge poisons everything downstream.
2. **Who are they connected with?** Co-authors, advisors and advisees, co-founders, colleagues who overlapped in time and place, co-directors, co-investors.
3. **What's their background?** Schools, degrees, fields and years.
4. **What's their history?** Dated roles: where, what, when.
5. **What do they say about themselves?** Class year, hometown, languages and the like, only as they state them publicly. Never inferred.

**How it searches:**
- **IDs first:** each ID makes the next source exact.
- **Fan out** across every source that covers the person, letting one trigger another (§2.1).
- **Stop when it's dry,** when the last few calls added nothing new.

## 2.4 The graph: dossiers

**The unit is the dossier** [Dominik, 11-13]. There's one per person, organization, work or event.
- **Self-contained:** an agent can read one dossier and know what the graph knows about its subject.
- **Every fact lives in its subject's dossier,** with its source (URL, date, the exact span).
- **Links hang on facts.** The fact "partner at Fund B since 2021" *is* the link to Fund B's dossier. A link never exists without the fact that justifies it.
- **It's a way in, not a summary.** It points to where to go next.

```
dossier: Person A                                    (person)
  ids: orcid 0000-…, openalex A…, dblp …
  - PhD, MIT EECS, 2019                    → [MIT EECS]        source: DSpace@MIT, 2019
  - co-author of "X" (2023)                → [Person C]        source: OpenAlex
  - partner since 2021                     → [Fund B]          source: Form ADV, 2024
  - says: from Boston; speaks Korean                           source: own page, 2026
  linked from: [Person C] co-author · [Lab X] member
```

**Fact types:** a fact's predicate is `type::subtype` (`education::degree::phd`, `research::coauthor`, `employment::partner`, `finance::invested_in`, `self::hometown`, …). Its object is a value or another dossier. The list lives in `schema/fact_types.yaml`, and the team extends it.

**The structure is what the facts say.** Organizations link to each other only as sources state it (a lab is part of a university, a fund invested in a company). **Groupings are computed, not assigned:** clusters over the links (research areas, deal networks, alumni clusters), recomputed as the graph grows. Agents can use them as starting points; they never shape where facts go.

**Storage (proposal):** dossiers render as Markdown for agents, from three tables: entities, facts and sources (`schema/schema.sql`). SQLite in week 1, then Postgres. Raw data about real people never goes in the repo.

## 2.5 Upkeep, in the same loop

When `write(G, facts)` lands new facts, the same step revises what they touch:
- **Merge:** a person who turns out to be someone we have (a shared ID) is merged, and their facts move to one dossier.
- **Don't duplicate:** the same fact from a second source adds that source to the fact.
- **Supersede by date:** a newer fact on a single-valued field (current role, current affiliation) supersedes the older one. The old fact stays, as history.
- **Checks**, after each batch:
  - broken links;
  - facts without a source;
  - dossiers with no links;
  - superseded facts still shown as current;
  - the ambiguity queue's size.

## 2.6 The agent's way in (MCP)

**Proposal.** Starting points, never answers. The agent explores.

```
open_task(question, user_id, task_id=None)
  -> task_id, starting_dossiers: list[{id, name, kind, one-line}]
  "Starting points for this question. Never the answer."

read_dossier(dossier_id, reason, task_id, links="facts" | "names" | "none")
  -> the dossier: facts with sources, and its links out and in
  "Every read gives its reason."

next_degree(dossier_ids, task_id, link_types=None)
  -> the dossiers one link away, each with the fact that links it
  "Search outward one degree at a time."

follow_person(name, reason, task_id)
  -> {frontier_entry, state}
  "The graph doesn't hold them: the trail will follow them."

continue_task(question, task_id) -> like open_task
```

- **Order is learned, never shown.** Lists come back ordered by how useful dossiers have proven for past tasks and their reasons. The agent never sees a score.
- **Reasons are logged.** Every read's reason is kept, for that ordering and for evals.

## 2.7 Evals

- **The questions:** 20–40, worked back from the use cases (PRD §2), each with a checked answer where one exists. Users' real questions get added over time.
- **Three arms (proposal):**
  1. an agent with only web search and the sources' raw dumps: **the bar to beat**;
  2. an agent with the graph, starting from default dossiers;
  3. an agent with the graph, starting from dossiers picked for the question.
- **Metrics:**
  - right or wrong, where an answer exists;
  - a judged side-by-side, where it doesn't;
  - navigation: calls, dossiers read, tokens, and wasted reads.
- **Every new source is evaluated when it's added:** does it raise the trail's yield (new people and facts per person researched), or the answers?
- **No regressions:** a change to the trail or the graph has to keep the scores from dropping.

## 2.8 Data rules

- Public data only, gathered only in ways each source allows (§2.1; PRD §5).
- Synthetic data stands in where a source doesn't allow it. It's flagged, and never mixed with real people's records.
- Raw data about people never goes in the repo. It lives in one private store.
- Demographics only as people state them publicly. **Never infer protected traits.**
- A suppressed directory entry is an opt-out. We remove anyone who asks.
- Permissions (MIT Libraries for DSpace@MIT, and COUHES) come up when we fetch real data. They aren't a blocker now.

## 2.9 Build plan

**Proposal.** Four weeks, 11-09 to 12-06, with two short syncs a week [kickoff 27:37].

| Week | Build | Done when |
|---|---|---|
| **1** (to 11-15) | Agree this design. The repo, the schema, the connector interface, and one real connector each. | The trail runs on synthetic people (it does today), and each connector returns real records for ~20 seed people. |
| **2** (11-16 to 11-22) | `research(p)` with IDs-first fan-out, extraction from pages, the ambiguity queue, upkeep | The trail runs 2 hops from an MIT seed on real sources, and every fact has a source. 20 checked questions. |
| **3** (11-23 to 11-29, Thanksgiving) | The agent's way in (MCP), computed groupings, refresh | An agent answers questions through the five calls. |
| **4** (11-30 to 12-06) | A second seed set (another college or a set of firms), evals in three arms, the demo | Scores against the bar, and the demo. |

**Who might take what (suggestions; each person decides):**
- **Dominik:** the trail (`select`, the frontier, explorers) and the agent's way in.
- **Rebecca:** the finance sources (SEC) and the finance use cases.
- **Audrey:** frontier scoring, computed groupings, and the synthetic layer.
- **Amy:** `research(p)`'s extraction and identity matching, and evals.
- **Everyone:** one connector each in week 1.

## 2.10 Open questions

1. **The seed:** which MIT sources? The allowed ones reach the research community well and undergraduates thinly.
2. **The scoring weights,** and the size of the daily budget.
3. **The ambiguity threshold:** how sure is sure enough to write?
4. **Groupings:** which clusterings help agents start well?
5. **The second seed set:** another college, or a set of firms?
6. **Self-stated attributes:** which ones we keep.
