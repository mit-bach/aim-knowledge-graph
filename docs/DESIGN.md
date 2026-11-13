# AIM knowledge graph: high-level and low-level design

**AIM Labs, fall 2026.** Amy Lin, Audrey, Dominik Bach, Rebecca. Draft 0.1, 2026-11-12. It replaces the PRD's pipeline (§6) and agent environment (§7). The PRD still holds the problem, the users, and the data rules.

**How to read it.** The same marks as the PRD:
- **[kickoff mm:ss]:** said at the 11-08 kickoff.
- **[Dominik, 11-12]:** his direction after the PRD.
- **Proposal:** new in this draft, and not agreed.

---

# Part 1. High-level design

## 1.1 What we're building

**We follow the people trail** [Dominik, 11-12].
- We start from MIT's students [Dominik, 11-12; kickoff 11:23–13:26].
- For each person, we find as much as public sources allow: who they are, who they're connected to, their background and history.
- Each connection points to someone or somewhere new: another lab, another college, a company, a fund. We follow it, and repeat.
- The graph grows outward from MIT into other institutions and companies [kickoff 15:27–17:13]. It's the trail of people, not money, and the bet is that the trail shows where talent and influence actually go.

The deliverable is still the graph, the system that builds and keeps it, and an environment an agent navigates [kickoff 20:50–21:24].

## 1.2 The core problem: the dataset is the world

"The entire dataset is like the world, how do we build that?" [Dominik, 11-12]

**Proposal:** we don't download the world. We **explore** it, and the design rests on four ideas.
1. **A frontier, not a crawl.** The graph keeps a frontier of people and organizations it has heard of but not yet looked up. Exploring means taking the best item off the frontier, looking it up, and adding what it points to.
2. **Every lookup has a reason** [Dominik, 11-12: "we need to have a reason to find the data"]. An item gets on the frontier only with a reason: who pointed to it, through which link, from what evidence. Its priority comes from that reason. No reason, no lookup.
3. **Territories.** The world is split into territories: an institution, then its schools and departments, then its labs and groups. A company or fund works the same way. Each territory has its own agent and its own frontier, so territories explore in parallel. When the trail crosses a border (an MIT student who interned at a trading firm), the territory agent hands the person to the next territory. If that territory doesn't exist yet, the handoff opens it.
4. **Build, maintain, expand** [kickoff 21:43–22:16]:
   - Build is the seed.
   - Maintain is scheduled refresh plus graph checks.
   - Expand is the frontier, and an agent's question can push something to the front of it.

## 1.3 The systems

**Proposal.** Each of these is a system, drawn as a diamond, that opens into its own frame in the drawing.

```
      ┌──────────── triggers: scheduled · the graph asks · a person asks ────────────┐
      ▼                                                                              │
 [Sources] ──► [Router] ──► [Evidence archive] ──► [People graph] ◄──► [Agent API] ◄── agent / user
      ▲                                                  ▲   │              │
      │                                    territory agents   │              │ request_lookup
      └─────────────────── frontier lookups (the trail) ──────┘◄─────────────┘
                                          ▲
                     [Control]  oversees everything: budget, source rules, health
                     [Eval]     scores the graph through the agent, with and without it
```

| System | Its job |
|---|---|
| **Sources** | The public sources we're allowed to use (PRD §5 and §2.6 below), each with its own triggers. |
| **Router** | Takes a lookup request (an entity plus a reason) and picks the sources that cover it. It enforces each source's rules and rate limits, and dispatches the lookups. |
| **Evidence archive** | Stores every fetched document raw, with its source, URL and time. Nothing in the graph exists without evidence here. |
| **People graph** | The curated graph. An entity doc per person, organization, school, fund and work, with typed links. Each fact cites its evidence. It's split into territories. |
| **Territory agents** | One per territory. Each owns its frontier, expands it within budget, and hands people across borders. |
| **Control** | Oversight: the global budget, the source rules, agent health, and the order to split or open territories. |
| **Eval** | Asks the agent hard questions with and without the graph, and scores correctness and how efficiently it navigated. |
| **Agent API** | How any frontier model reads the graph (an MCP server). The model can also ask for a lookup when it hits a gap. |

## 1.4 Triggers: why a source gets called

**Proposal.** Three triggers, and nothing else calls a source:

| Trigger | When | Example |
|---|---|---|
| **Scheduled** | A source's refresh cadence comes due for facts that are going stale. | Re-check SEC filings for a fund every quarter. |
| **The graph asks** | A territory agent takes a frontier item, or a reference shows up in new evidence. | A thesis names an advisor, so look the advisor up. |
| **A person asks** | A user, or the agent for them, asks about someone the graph doesn't hold yet. | "Who's behind Fund B?" with Fund B missing, so `request_lookup`. |

## 1.5 Territories

**Proposal.**
- **A territory path** names where an entity lives: `["1::mit", "2::mit::eecs", "3::mit::eecs::csail"]`, or `["1::jane-street"]`.
- **Levels:**
  1. institution or company;
  2. school, department or division;
  3. lab, group or team.
- **The territory network.** Territories link to their parent and children. Siblings link when the trail crosses between them often. An agent can wake any territory it links to. Anything further away goes through the chain of links in between.
- **Opening a territory.** A border item waits in a holding list until enough reasons point at the new territory (say, 10), or a person asks about it. Then Control opens the territory and starts its agent.
- **Splitting a territory.** When a territory gets too large (say, over 2,000 entities, or a frontier over 500), it splits along its next level down.

## 1.6 One turn of the trail

```
territory agent pops the highest-priority frontier item  (entity + reason)
  → Router picks sources that cover it, inside budget and source rules
  → sources return documents → Evidence archive
  → Extractor turns evidence into claims (fact + source span + confidence)
  → Resolver: is this a person we already have? (IDs first, then name + affiliation + years)
  → People graph: update the entity doc and its links
  → every new link that points somewhere new → a new frontier item, with its reason
       inside this territory → this frontier
       across a border → hand it to that territory (or the holding list)
  → Analyst rescores the frontier
```

## 1.7 What we build this month

**Proposal.**
- **Territories:** three. MIT (EECS first), one more college or institution, and one finance territory (a fund or firm the trail reaches).
- **Sources:** 4–6 connectors (§2.6).
- **Agents:** one territory agent per territory, and one Extractor, Resolver and Analyst shared by all.
- **The Agent API** with all five calls (§2.7), graph checks (§2.8), and an eval A/B (§2.9).
- **Designed but not built this month:** reviewer tiers above the territory agents, and automatic territory splitting (we split by hand).

---

# Part 2. Low-level design

## 2.1 Data model

**Proposal.** All of these are stored records. Every fact points to evidence.

**Entity doc**
```
entity {
  id: str                      # stable, e.g. "person:3f9a…"
  type: person | org | school_program | fund | round | work | industry
  name: str
  desc: str                    # one or two lines, written by the Extractor
  tags: list[str]              # e.g. ["researcher", "founder"]
  territory_path: list[str]    # ["1::mit", "2::mit::eecs"]
  ids: {orcid?, openalex?, wikidata?, dblp?, github?, sec_cik?}
  attributes: { key: {value, evidence_ids, confidence, valid_from?, valid_to?} }
  status: referenced | expanded | stale
  expanded_at: datetime?
}
```

**Link**
```
link {
  from_id, to_id: str
  link_path: str               # "type::subtype::subsubtype" (2.2)
  desc: str                    # "co-authored 'X' (2024)"
  valid_from?, valid_to?: date
  evidence_ids: list[str]
  confidence: float
}
```

**Evidence and claims**
```
evidence { id, source, url, fetched_at, content_hash, blob_ref, trigger, reason_id }
claim    { id, evidence_id, span: {start, end, text}, subject_ref, predicate, object_ref | value, confidence }
```

**Frontier item and reason**
```
frontier_item {
  entity_ref                   # an entity id, or an unresolved name + hints
  territory_path
  reason { from_entity, link_path, evidence_id,
           requested_by: territory | task | person, note }
  score: float
  hops_from_seed: int
  state: queued | holding | in_progress | done | dropped
}
```

**Territory and task**
```
territory { path, parent, children, neighbors, agent_id, budget, entity_count, frontier_size, opened_at }
task      { id, question, user_id, entities_read: list, lookups_requested: list, answer?, score? }
```

## 2.2 Link types: `type::subtype::subsubtype`

**Proposal.** A first set, which the team extends:

| link_path | Between | Main sources |
|---|---|---|
| `education::degree::{bs,ms,phd,mba}` | person → school_program | Wikidata, ORCID, DSpace theses |
| `education::advised_by` | person → person | DSpace theses, OpenAlex |
| `research::member_of::lab` | person → org(lab) | lab pages, OpenAlex affiliations |
| `research::coauthor` | person ↔ person | OpenAlex, DBLP, arXiv |
| `research::authored` | person → work | OpenAlex, DBLP, arXiv |
| `employment::role::{employee,founder,partner,director,officer}` | person → org | SEC filings, company pages, Wikidata |
| `finance::raised` / `finance::invested_in` | org → round, fund → org | SEC Form D |
| `code::contributor` | person → work(repo) | GitHub (2.6) |
| `news::mentioned_with` | person ↔ person/org | GDELT |
| `derived::same_place_same_time` | person ↔ person | computed by the Analyst, never fetched |

## 2.3 The trail algorithm

**Proposal.** It's "this given algorithm, which is yet to be described" [Dominik, 11-12], written out so the team can change it.

**Seed.** MIT people from allowed seed sources: MIT-affiliated OpenAlex and DBLP authors first, then DSpace@MIT thesis authors and advisors (once MIT Libraries says yes), lab member pages, MIT News, and Wikidata's MIT alumni. Each enters the MIT territory with the reason `seed:<source>`. Students with no public footprint stay unknown. The synthetic layer (PRD §6) stands in for them in statistics.

**`expand(entity)`**, the per-person lookup:
1. **Identity.** Gather every ID we can reach from the ones we have. ORCID lists other IDs, and Wikidata holds external IDs. IDs make the next lookups exact.
2. **Plan.** Ask each connector `covers(entity)`, for example "has an ORCID" or "is named in an SEC filing". Order the hits by expected yield over cost.
3. **Fetch** through the Router: inside rate limits and the source's rules, saved to the Evidence archive.
4. **Extract** claims with source spans.
   - The attributes are education, roles, affiliations, works, and what the person states about themselves publicly.
   - **Demographics: only what the person states publicly, such as class year, hometown, school and languages. We never infer protected traits** (race, religion, health, and the like).
5. **Resolve and write** to the entity doc and its links.
6. **Emit the frontier.** Every link to an entity that isn't expanded becomes a frontier item, with the link as its reason.

**Frontier score** (rescored by the Analyst after each turn):
```
score = w_r·relevance + w_b·bridging + w_n·novelty + w_e·evidence − w_c·cost
```
- `relevance`:
  - closeness to the seed and to entities that recent tasks read;
  - × 3 when a task or a person asked for it.
- `bridging`: 1 if it leads into an unexplored territory or links two territories, else 0.
- `novelty`: the share of its known links not yet expanded.
- `evidence`: the confidence of its reasons. Several independent reasons raise it.
- `cost`: the expected API calls and time for its lookup plan.

Starting weights are all 1. The team tunes them against eval.

**Stopping and budgets:**
- Each territory has a lookup budget per day. Control sets it.
- Hops from the seed are capped at 2 inside MIT, and 1 past a border until that territory opens.
- A territory pauses when its yield (new links per lookup, over the last 50) falls below a threshold.

**Border handoff:** a message from one territory agent to another:
```
{ entity_ref, reason, evidence_ids, from_territory, hops, version }
```
It goes directly to a linked territory, or through the chain of links in between. A sleeping territory takes in its queued handoffs when it next wakes. A territory that doesn't exist yet gets the item in its holding list.

**Refresh:** each source has a cadence. An expanded entity goes `stale` when its newest evidence is older than its sources' cadence. Stale entities rejoin the frontier with the reason `refresh`.

## 2.4 Components and roles

**Proposal.** Each role is an agent or a module. In the month, roles can share one process.

| Role | In system | Does |
|---|---|---|
| Connector (one per source) | Sources | `covers(entity) -> bool`, `lookup(entity, reason) -> list[Evidence]`, `cadence`, `rules` (what may be stored) |
| Router | Router | Picks connectors, enforces rate limits, budget and rules, and dispatches |
| Format checker | Evidence archive | Flags evidence that came back broken, empty or in an unexpected format |
| Extractor | People graph | An LLM turns evidence into claims with spans |
| Resolver | People graph | Matches by ID, then blocks on (normalized name, affiliation, years), then has an LLM adjudicate. Merges go to a human review queue, and a teammate checks them |
| Edge builder | People graph | Writes links with the right `link_path`, and derives the `derived::*` links |
| Classifier | People graph | Keeps tags and link types tidy, and proposes new ones |
| Territory agent | Territories | Pops its frontier, runs `expand`, and sends and receives handoffs |
| Cartographer | Territories | Owns the territory scheme: opening, splitting and naming |
| Analyst | People graph | Frontier scores, talent flows, bridges between territories |
| Checker | People graph | The graph checks (2.8) |
| Control | Control | Budget, source rules, agent health. Approves opening and splitting territories |
| Eval designer and runner | Eval | The question set, A/B runs, scoring |

**File layout note (proposal):** the Evidence archive is laid out by source and date, not by territory. A person moves territories, and their evidence shouldn't have to move with them.

## 2.5 Storage

**Proposal.**
- **Postgres** holds entities, links, claims, the frontier, territories and tasks. JSONB holds the attributes, and recursive queries handle paths.
- Raw evidence blobs go in one private store.
- NetworkX handles analysis.
- Week 1 can start on SQLite with the same schema.
- **The raw data stays out of the repo** (PRD §5). The repo holds code, the schema, and synthetic fixtures.

## 2.6 Which source moves the trail

The PRD's §5 lists what each source allows. This section is about the trail: **which allowed source turns a node into its next hops.** It was checked on 2026-11-12 against each source's own terms, robots.txt and API docs. Nothing was fetched about anyone. The verdicts are proposals.

**Ranked by how many reliable edges each gives:**

| Hop | Sources, best first | Notes |
|---|---|---|
| **person → person** | DBLP co-authorship (computer science, IDs already matched up, CC0 dump) · OpenAlex and ORCID · arXiv and Crossref co-authors (names only, unless there's an ORCID) · DSpace@MIT advisor → student · GitHub co-contributors | Co-authorship is the backbone of the trail inside MIT. GitHub identities are noisy. |
| **person → org** | DSpace@MIT department · OpenAlex and ORCID affiliations over time · Crossref affiliations (sparse) · GitHub public org membership · MIT News mentions | MIT News needs entity extraction, and we keep the fact plus a link, not the article. |
| **org → person** | Lab rosters (for example CSAIL `/people`) · OpenCourseWare course → instructor · SEC EDGAR filings (officers, directors, fund owners) · company team pages | Fetch single pages only when the frontier asks, obeying each site's robots.txt. |
| **identity** (makes the next hop exact) | ORCID (lists other IDs) · Wikidata (external IDs) · OpenAlex · DBLP | These come first in `expand()`, step 1. |

**Connectors this month (proposal):** OpenAlex, DBLP (the dump, queried locally), ORCID, Wikidata, SEC EDGAR (bulk files) and DSpace@MIT (OAI-PMH, slowly, once MIT Libraries has said yes in writing). Lab rosters come as a single-page fetcher. Synthetic data stands in for LinkedIn and Crunchbase.

**Finding pages about one person** (a search step inside `expand()`):
- **Tavily**, with care. It's the least restrictive of the live search APIs, and free for students.
- **Brave**, only in the moment. Its terms ban building a database from search results.
- Either way, a search result only points at a page. What we store comes from that page, under that page's terms.

**Don't use:**
- **Google Scholar:** no API, and its terms ban scraping.
- **Exa:** its terms ban reusing results without written permission.
- **Google Custom Search** (closed to new users) and the **Bing Search API** (retired).
- **Common Crawl, for people:** its terms ban harvesting personal data. It's still fine for finding organizations' URLs.
- **Engage:** student organizations, behind MIT sign-in. Club membership is synthetic.
- **People Data Labs:** not all from public sources.
- **Proxycurl:** shut down after LinkedIn sued it.

**Rules the sources impose on the design:**
- **GitHub:** only repo- and org-level edges. No commit emails. Honour removal requests. Its policies allow research on public, non-personal information, with open-access publications.
- **DSpace@MIT:** its user agreement bars compiling a database without MIT Libraries' written permission. Ask before harvesting (§2.13).
- **Firecrawl:** its terms ban background-check use. Don't use it for the due-diligence use. Our own fetcher, which obeys robots.txt, is enough.
- **MIT directory and FERPA:** students can suppress their directory information. **Treat a suppression as an opt-out:** never fill in a suppressed student's details from other sources.
- **No inferred protected traits** (race, religion, health, politics). The FTC has acted against selling such inferences. If the team wants demographics, they come from synthetic aggregates or from what people state themselves.

**How much of "all MIT students" this reaches:** the allowed sources reach researchers, graduate students with theses or papers, and anyone with a public professional footprint. Most undergraduates have none in these sources, and Engage and the directory are off-limits for bulk use. **So the trail will be dense for MIT's research community and thin for undergraduates.** The synthetic layer stands in for undergraduates in statistics.

## 2.7 Agent API (MCP)

**Proposal.** A frontier model navigates the graph only through these five calls:

```
open_task(question: str, user_id: str, task_id: str | None = None)
  -> init_entities: list[entity_id], required_entities: list[entity_id],
     task_id: str, default_territory_filter: (include: list[str], exclude: list[str])
  "Opens a task and returns two sets of entities to read first, and the territory filter
   every later call uses unless told otherwise."

get_entities(entity_ids: list[str], default_territory: bool = True)
  -> { name: (desc, { link_path: count }, territory_path) }
  "Names, territory paths and link-type counts for a list of entities: what to read next."

read_entity(entity_id: str, default_territory: bool = True,
            territory_filter: (include, exclude), link_filter: (include, exclude),
            tag_filter: (include, exclude),
            link_verbosity: "none" | "description" | "evidence" | "full",
            reason_for_reading: str)
  -> { name, desc, tags, territory_path, attributes,
       links: [ { to: {name, desc, tags, territory_path},
                  link_path, link_desc, evidence: {source, url, span} } ] }

continue_task(question: str, task_id: str) -> same as open_task

request_lookup(name_or_id: str, reason: str) -> { frontier_item_id, eta }
  "The graph doesn't hold it: put it on the frontier with this reason."
```

- **Relevance order is implicit.** Lists and links come back in order of how useful they've been to past tasks. The order is never shown as a number.
- Every call logs `reason_for_reading`, which feeds relevance order and eval.

## 2.8 Graph checks

**Proposal.** The Checker runs these after each batch, and nightly:
- **Broken links:** a link to a missing entity. Find the cause and send it back to the step that made it.
- **Duplicates:** two people who are likely the same in one territory, sent to the Resolver.
- **Unsourced facts:** every attribute and link must cite evidence.
- **Unused tags and link types,** and **empty territories.**
- **Connectivity:** links within and between territories, and by link type.
- **Staleness:** the share of expanded entities past refresh.
- **Spans:** evidence spans inside their length limits.
- **LLM spot-check:** sample a territory's relevance order and ask whether it makes sense.

## 2.9 Eval

**Proposal.**
- **The question set:** 20–40 hard questions across the uses (PRD §2), each with a checked answer. Users' real questions get added over time.
- **A/B:** the same model and questions, with the Agent API versus with web search only. This shows what the graph adds.
- **Metrics:**
  - Did it get the checkable answer right?
  - For open answers, a side-by-side grade.
  - Navigation efficiency: calls, entities read, tokens, and wasted reads.
- **No regressions:** a change to the graph or the algorithm has to keep the score from dropping.

## 2.10 Repo layout

**Proposal.**
```
aim-knowledge-graph/
  docs/        PRD.md, DESIGN.md, decisions/
  schema/      sql/, link_types.yaml, territories.yaml
  connectors/  one module per source, with its rules and cadence
  router/      evidence/   extract/   resolve/   graph/
  territory/   agent loop, handoffs, cartographer
  analyst/     scoring, flows        checks/    graph checks
  api/         MCP server (five calls)
  eval/        questions/, runner, A/B
  synthetic/   generator, fixtures (synthetic only)
  tests/
```

## 2.11 Build order (weeks from the PRD, redone from Thursday 11-12)

**Proposal.**

| Week | Build | Done when |
|---|---|---|
| **1** (to 11-15) | Agree this design. Make the repo. Schema v0, link types v0, the connector interface, and 2 connectors. | A seed of about 50 MIT people is in the Evidence archive, with reasons. |
| **2** (11-16 to 11-22) | Extractor, Resolver, graph store, one territory agent (MIT EECS), frontier scoring | The trail runs 2 hops from the seed, and every fact has a source. 20 checked questions. |
| **3** (11-23 to 11-29, Thanksgiving) | Agent API (five calls), border handoff, the holding list, Control's budget, graph checks | A second territory opens through the trail. A model answers questions through the API. |
| **4** (11-30 to 12-06) | Third territory (finance), eval A/B, demo | A/B scores, the demo, and the drawing of what got built |

## 2.12 Who might take what

**Suggestions only. Each person decides.**
- **Dominik:** the territory agents and handoffs, the Agent API, and the trail algorithm.
- **Rebecca:** the finance connectors (SEC), the finance territory, and the use cases.
- **Audrey:** the Analyst (frontier scoring, flows), and the synthetic layer.
- **Amy:** the Extractor and Resolver prompts, and eval.
- **Everyone:** one connector each in week 1.

## 2.13 Open questions

1. **The seed:** which MIT sources. Allowed sources reach the research community well and undergraduates thinly (§2.6). Is that the right start?
2. **Permissions, later.** Two come up when we start fetching real data:
   - MIT Libraries' written OK to harvest DSpace@MIT (until then, the trail seeds from OpenAlex and DBLP);
   - whether COUHES (MIT's committee on research with people) needs to see the project.

   Not a blocker now: we deal with them when we get there.
3. **The scoring weights,** and whether the budget is per territory or global.
4. **The thresholds** for opening and splitting a territory.
5. **Storage:** Postgres for everyone from week 1, or SQLite first?
6. **Which second and third territories:** chosen by the trail, or picked by the team?
7. **Demographics:** the list of self-stated attributes we keep.
