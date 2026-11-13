# Knowledge graph of professional networks: rough PRD

**AIM Labs, fall 2026.** Amy Lin, Audrey, Dominik Bach, Rebecca. Draft 0.1, 2026-11-08, for Thursday's meeting (2026-11-12).

Drafted from the kickoff recording, as Amy suggested [25:45–25:53]. It's rough on purpose: everything here is open to change.

**Update, 2026-11-12:** `DESIGN.md` (the high-level and low-level design) replaces §6 (the pipeline), §7 (the agent's environment) and §8–9 (the plan and the roles). This PRD still holds the problem, the users, the graph, the data sources and the open questions.

**How to read it.** Each section has two parts:
- **From the kickoff:** what someone said on the call. Times like [11:23] are minutes:seconds into the recording, which started at 4:30 PM on Sunday 2026-11-08.
- **Proposal:** new in this draft. Nobody has agreed to it yet.

---

## 1. In one paragraph

**From the kickoff:** We build a knowledge graph of people and their professional networks from public data, starting with MIT and then Ivy League alumni [15:27–17:13]. The graph's uses are in finance: who moves money and talent [11:23–13:26], and due diligence on the people behind a company or fund [23:56–24:26]. The deliverable is the graph, its data pipeline, and an environment an AI agent can navigate. It isn't a trained model: a frontier model does the reasoning [20:50–21:24]. We have about a month [20:29–20:47].

**Proposal:** working title "who's behind the money": an agent that answers questions about the people behind companies and funds, with every answer traced to a public source.

## 2. The problem, and who it's for

**From the kickoff:**
- **The problem.** In finance, who you know and who is moving the money matter as much as the money itself [11:23–13:26]. Researching one person, their path and what they're working on takes one person a lot of time [11:23–13:26]. If the data is already gathered and connected, a question gets answered directly, without fresh research each time [24:26–25:20].
- **Why it matters.** People go to Ivy League business schools mainly for the network [16:45–17:03]. Mapping that network, and its outcomes (which schools lead to which trading firms, and what those people do next), is the interesting part [17:03–17:13].
- **Who it's for:**
  - **A VC or investment-banking analyst.** Who works at this company, what backgrounds they come from, and where the company is heading. A check on the people who make up an organization [23:56–24:26].
  - **An industry analyst.** Where an industry's talent comes from (MIT? Harvard?), where the industry is heading, and employment trends over time [24:26–25:20].
  - **A CEO, CFO or banker** using the system as a tool [23:30–23:52].
  - **A quant** looking at which voices and news drive decisions (Amy) [19:57–20:26].
  - **A student networking.** A freshman who wants to join a lab: who to talk to [11:23–13:26]. Someone at an alumni event [15:31–16:33].
- **Program fit.** The program's options included navigating robots and financial data. The group leaned toward financial data and LLM work, because robotics is hard in a short project [5:14–5:44]. Rebecca wanted reach beyond MIT [14:39–15:22], and experience with different models and bigger datasets that's useful in business [19:13–19:36]. Amy wanted to learn things we haven't done before [18:56–19:13].

**Proposal: what this is not.**
- **Not a trained model** [20:50–21:13]. A small model could come in later, as a stretch (section 10, question 6).
- **Not face recognition, and nothing that identifies a person on sight.** Dominik raised the smart-glasses example only as an illustration, and said the project shouldn't be for that [16:07–16:33].
- **Not private data.** No logins, no private profiles, nothing a site's terms forbid (section 5).
- **Not a stock-price predictor.** Amy's market and sentiment idea comes in as a layer, if the team picks it (section 10, question 5).
- **Not called a "background check" outside the team.** In the US, that phrase can bring in consumer-reporting law (the FCRA). "Public-record due diligence" says what we do.

## 3. What we deliver

**From the kickoff:**
- The knowledge graph itself: the data that's been mined and organized [21:16–21:24].
- The data pipeline [21:28].
- An environment an agent can go into to navigate the graph [21:00–21:13].
- A way to build the graph, maintain it and expand it [21:43–22:16].

**Proposal:** two more things, so the graph gets used and we can show it works. Amy has seen a team build a knowledge graph and then not use it [22:16–22:32].
- **A question set:** 20–40 questions across the uses above, each with a checked answer, to grade the agent (section 7).
- **A demo:** the agent answering a handful of them live, with the path through the graph and its sources.

## 4. The graph: entities and relations

**From the kickoff:**
- **People:** who they are, where they work, what they do, their research and labs, their socials [11:23–13:26].
- **Schools:** MIT first, then the Ivy League [15:27–16:07].
- **Firms:** trading firms, banks, VC and investment firms [17:03–17:13, 23:56–24:05].
- **Trajectories:** where graduates went, and what they're doing now [15:31–16:07, 17:03–17:13].
- **Industries and talent flows** [24:26–25:20].
- **The voices:** news sources and Twitter, and who the big voices are [18:14–18:56].

**Proposal: the schema, version 0.**

Entities:

| Entity | What it holds | From |
|---|---|---|
| Person | name, public profile links, external IDs (Wikidata, ORCID, SEC CIK) | [11:23] |
| Organization | type: company, fund, bank, trading firm, university, lab; city | [17:03], [23:56] |
| School program | school, degree (BS, MBA, PhD) | [15:31], [16:45] |
| Fund or round | a fund, or a company's raise (Form D) | [11:23] "who is moving around that money" |
| Work | a paper or a patent | [11:23] "what research they're working on" |
| Industry | a sector label | [24:26] |
| Source | the document a fact came from: a filing, a page, an article, a post | proposal |
| Mention | a news article or post naming a person or firm, with its sentiment | [18:14] |

Relations. Each one carries when it was true (from, to), its source, and when we fetched it:

| Relation | Between |
|---|---|
| `STUDIED_AT` | Person → School program (years) |
| `WORKED_AT` | Person → Organization (title, from, to) |
| `MEMBER_OF` | Person → Lab |
| `DIRECTOR_OF`, `OFFICER_OF`, `FOUNDER_OF` | Person → Company, from filings |
| `PARTNER_AT`, `MANAGES` | Person → Fund |
| `INVESTED_IN`, `RAISED` | Fund → Company; Company → Round |
| `AUTHORED`, `INVENTED` | Person → Work |
| `IN_INDUSTRY`, `LOCATED_IN` | Organization → Industry, City |
| `MENTIONED_IN` | Person or Organization → Mention (with sentiment) |
| `CONNECTED_TO` | Person ↔ Person, **derived only**: same firm at the same time, co-authors, co-directors, same fund. The reason is stored. |

**Proposal: why connections are derived.** We can't see anyone's LinkedIn connections (section 5). So the "network" is built from overlaps that public records show, and every edge says why it exists. Talent flows (School → Industry, by year) are counts over `STUDIED_AT` and `WORKED_AT`.

## 5. Data sources, and what each allows

**From the kickoff:**
- Use what's online: LinkedIn, socials, the labs people work in [11:23–13:26], and data we have online [17:55–18:04].
- Employment trends from LinkedIn and similar [24:26–25:20].
- News sources and Twitter for sentiment [18:14–18:44].
- In a month, either scrape data, or generate reliable synthetic data based on what we can scrape (Amy) [20:29–20:47].

**Proposal: our data rules.**
- **Public data only, gathered only in ways the source allows:** its terms of use, robots.txt, official APIs, public datasets.
- **Synthetic data stands in where a source doesn't allow it,** flagged as synthetic, and never mixed with real people's records.
- **Raw data about people stays in one private store,** never in the repo, a shared doc or a slide. Demos use public-figure examples or synthetic people.
- **No sensitive attributes** (health, politics, family, home address), and we remove anyone who asks.

**What each source allows.** Checked on 2026-11-08 against each source's own terms, robots.txt, and API and pricing pages. Nothing was fetched about anyone. The verdicts are proposals.

*Money, and the people behind companies and funds*

| Source | What it gives us | What it allows | Verdict |
|---|---|---|---|
| [SEC EDGAR](https://www.sec.gov/os/accessing-edgar-data) | Form D: officers, directors and promoters of private raises. Forms 3/4/5: insiders and their trades. Proxy statements: directors' and officers' last five years of work, and their other boards. 13F: fund holdings. Form ADV: advisers' owners and officers. | Free. At most 10 requests a second, with a User-Agent that says who we are. Quarterly bulk files. | **Use.** Our core source. Prefer the bulk files. |
| [FINRA BrokerCheck](https://brokercheck.finra.org/terms) | Brokers' work history, licences and disciplinary records | Academic copying is allowed, but §6(p) bans using the data with any machine-learning or AI program. | **Use with care:** manual spot checks only, kept out of the agent's environment |
| [Crunchbase](https://about.crunchbase.com/terms-of-service/) | Founders, investors, rounds | No free API any more. The terms ban scraping and model training. | **Synthetic stand-in.** SEC Form D covers raises. |
| Company team pages | Names, titles, bios | Each site's robots.txt and terms decide. | **Use with care:** slowly, keeping only name, title, organization and URL |

*People, schools and research*

| Source | What it gives us | What it allows | Verdict |
|---|---|---|---|
| [LinkedIn](https://www.linkedin.com/legal/user-agreement) | Profiles, jobs, education, connections | The open API returns only the signed-in member's own basic profile. Members can export their own data. User Agreement §8.2 bans scraping and bots, and robots.txt bans automated access. | **Synthetic stand-in**, plus exports from volunteers who opt in |
| [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing) | Notable people's schools, employers and roles | Public domain (CC0). The query service has per-client limits and wants a User-Agent with contact details. Full dumps exist. | **Use** |
| [OpenAlex](https://help.openalex.org/access/pricing/) | Researchers, their affiliations over time, co-authors | CC0. A free key gives $1 of API use a day. A free full snapshot, every quarter. | **Use** |
| [ORCID](https://info.orcid.org/public-client-terms-of-service/) | Self-reported jobs, education and papers | Public API, free for non-commercial use: 25,000 reads a day without registering. | **Use** |
| [Semantic Scholar](https://www.semanticscholar.org/product/api/license) | Authors, papers, co-authors | Free API and datasets, with attribution | **Use**, to fill OpenAlex's gaps |
| [USPTO patents](https://data.uspto.gov/support/transition-guide/patentsview) | Inventors (already matched across patents), and who owns each patent | Bulk tables to download. The API needs a USPTO sign-in. | **Use** the bulk files |
| [MIT directory](https://web.mit.edu/directory/) | Name, email, and course and year for students (students can hide any of it) | No terms page found, and robots.txt doesn't mention it | **Use with care:** manual lookups only. Ask IS&T before automating anything. |

*News and voices*

| Source | What it gives us | What it allows | Verdict |
|---|---|---|---|
| [GDELT](https://www.gdeltproject.org/about.html) | People and firms named in the news, and the tone of the coverage | Free for any use, with a citation | **Use:** our main sentiment source |
| [Bluesky](https://bsky.social/about/support/tos) | Public posts and profiles | Its live feed (Jetstream) is free, with no login. We must honour deletions. | **Use**, for social sentiment |
| [X](https://docs.x.com/x-api/getting-started/pricing) | Posts, bios | Pay per use, about $0.005 per post read. The terms ban scraping. The developer policy bans linking an X account to a person off X without their consent. | **Use with care:** a small paid budget, sentiment about companies and topics only |
| [Reddit](https://redditinc.com/policies/data-api-terms) | Posts | API access needs approval. Research outside its Reddit for Researchers program breaks its terms. | **Don't use**, unless the team is accepted into that program |
| [NewsAPI](https://newsapi.org/pricing) | Articles | The free plan is for development only. Paid plans start at $449 a month. | **Don't use** |

**Two legal notes.**
- **Terms bind us even for public pages.** In *hiQ v. LinkedIn*, the appeals court (2022) said scraping public pages likely isn't hacking under federal law. hiQ still lost on breaking LinkedIn's User Agreement, and settled in December 2022: it stopped scraping and destroyed the data.
- **The FTC treats a report used to decide on someone's job, credit, insurance or housing as a consumer report,** under the FCRA. Disclaimers didn't exempt the people-search sites it fined in 2023. So we call this public-record due-diligence research, not for eligibility decisions.

**Not confirmed yet:** whether X still has a free tier; Semantic Scholar's dataset licence (reported as ODC-BY); the MIT directory's terms of use.

## 6. The pipeline

**From the kickoff:**
- A knowledge graph needs a way to be built, maintained and expanded [21:43–22:00].
- The build starts from an initial set of people, such as MIT alumni or Ivy League graduates [22:04–22:16].
- The data should already exist when a question comes in, so the system only has to answer it [24:26–25:20].
- Amy's warning: data pipelines eat time. Over the summer, someone on her team pulled five all-nighters on one [21:28–21:40].

**Proposal: the stages.**
1. **Seed.** A starting list of people and organizations, from sources that allow it. For example, MIT faculty and researchers (from Wikidata and OpenAlex), and the people named in SEC filings by finance firms.
2. **Collect.** One small connector per source, inside its rate limits. Each fetch is saved raw, with its time and URL.
3. **Extract.** Structured sources map straight to the schema. For text (proxy-statement bios, news), an LLM extracts typed facts and keeps the sentence each fact came from.
4. **Resolve.** Decide when two records are the same person, by external IDs first (ORCID, Wikidata, SEC CIK), then name plus affiliation plus dates. This is the hard part. Keep a list of merges a person checked.
5. **Load.** Into one graph store (section 10, question 7).
6. **Maintain.** Re-fetch on a schedule. Facts carry from/to dates, so old roles stay as history. Checks flag duplicates, contradictions and stale facts.
7. **Expand.** When the agent hits a gap (a person or firm it can't find), it files an expansion request. The pipeline fetches that entity from allowed sources, resolves it and loads it.
8. **Synthetic.** A generator makes LinkedIn-style career histories for made-up people, matched to the overall patterns in the real data (schools to industries, typical role lengths). Each record is marked synthetic.

**Proposal: keep the pipeline small.** One connector per person, with a hard limit on time per connector. A source that fights us gets dropped for synthetic data.

## 7. The agent's environment

**From the kickoff:**
- The deliverable is an environment an agent can go into to navigate the knowledge graph. We use a frontier model, not one we train [20:50–21:13].
- A user asks any question, and the system answers it from data that already exists [24:26–25:20].
- Dominik works on making very large bodies of context (billions of tokens) navigable by AI agents [8:37–9:01].
- One of the program's options Amy remembered was an RL environment for robotics [10:16–10:24].

**Proposal: the tools.** The agent works only through these tools, served as an MCP server so any frontier model can use them:

| Tool | What it does |
|---|---|
| `search(text, type)` | find people, firms, schools, funds |
| `profile(id)` | an entity's facts, each with its source and dates |
| `neighbors(id, relation, from, to)` | who or what is connected, and how, in a time window |
| `paths(a, b, max_hops)` | how two entities connect, with the evidence for each hop |
| `flows(from_type, to_type, filters)` | counts, such as MIT graduates into trading firms by year |
| `source(fact_id)` | the document behind a fact |
| `request_expansion(name, reason)` | asks the pipeline to fetch something missing |

**Proposal: the rules.** The agent reads the graph and changes it only through `request_expansion`. Every answer cites the facts it used. It declines questions about private or sensitive matters.

**Proposal: the question set makes it an environment.** 20–40 questions with checked answers, and a grader that scores correctness and citations. This is what tells us the graph is useful. Later (not in the month), the same tasks could train or post-train a model, which is Amy's area [9:03–9:29]. Example questions, with placeholder names:
- Who are Company X's officers and directors, and where did each study?
- How is Person A connected to Fund B, and through whom?
- Which schools sent the most graduates into trading firms in Boston and New York since 2015?
- Which people at Fund C co-founded or advised companies before joining?

## 8. One month, week by week

**From the kickoff:**
- About a month [20:29–20:47].
- Two short syncs a week, around 30 minutes each, instead of one long meeting (Dominik) [27:37–27:52].
- The program's usual structure is a Thursday meeting plus one meeting a week on our own (Rebecca) [27:18–27:32]. The Thursday 7–8 PM slot clashes with Rebecca's club [26:30–26:44]. Amy leads AppDev [27:09].
- Rebecca is sending a When2Meet [27:52–28:41].
- Amy may not make both syncs, and can send a short written update instead [28:15–28:28].

**Proposal:** four weeks, from Monday 11-09 to Sunday 12-06. Each week has two 30-minute syncs. **Sync A** (early in the week) picks the week's tasks. **Sync B** (late in the week) shows what runs. Anyone who can't come posts a three-line update: done, next, stuck.

| Week | Goal | Done when |
|---|---|---|
| **1** (11-09 to 11-15) | Agree, and try each source | Thursday's meeting settles this PRD's open questions. Schema v0 is agreed. Each person has a connector pulling about 20 records from one allowed source. 10 target questions are written. |
| **2** (11-16 to 11-22) | First real graph | The seed is collected, resolved and loaded. `paths` works on real data. The synthetic generator v0 runs. 20 questions have checked answers. |
| **3** (11-23 to 11-29, Thanksgiving on Thursday) | The agent, and keeping the graph alive | The MCP tools work, and a frontier model answers the questions with citations. Refresh, checks and `request_expansion` run once. Sentiment goes in now, if picked. One sync this week. |
| **4** (11-30 to 12-06) | Expand and demo | A second population (some Ivy League alumni) is added through the expansion loop. The question set is scored. Demo, short write-up and final drawing. |

## 9. Who might take what

**These are suggestions. Each person decides.**

| Who | Background, from the kickoff | Suggested piece |
|---|---|---|
| Amy | LLM engineering and post-training [9:03–9:41], two semesters of AIM Labs [20:29], has led a team that built a knowledge graph [22:16–22:32]. Time is tight this semester [25:26–25:31, 28:15–28:28]. | The question set and grader, or the sentiment layer (her idea [17:16–19:13]). Both are bounded pieces. |
| Audrey | Built a transformer model for tennis prediction [9:48–10:05], prefers financial data [5:14–5:28]. | The synthetic data generator, and the talent-flow statistics. |
| Dominik | Works on making huge bodies of context navigable by agents, and on knowledge graphs [8:26–9:01]. | The agent's environment (MCP tools), the build, maintain and expand loop, and schema v0. |
| Rebecca | AI with business and finance [5:03–5:11], wants bigger datasets and work that applies to business [19:13–19:36]. | The finance sources (SEC filings: the people behind companies and funds), the use cases, and the demo story. |
| Everyone | | One data-source connector each in week 1, and entity resolution in week 2, together. |

## 10. Open questions for the team

1. **The program's rules.** What does AIM Labs require: the deliverable, demo date, end date, and whether a people graph fits the financial-data track? Dominik missed the first session [5:44–6:12]. Amy remembered an RL environment for robotics, financial data, and maybe a third option [10:16–10:24]. Can we use Claude and coding tools? Amy hoped so [25:53–26:16].
2. **The lead use.** Due diligence on the people behind companies and funds (this draft's pick), talent flows, student networking, or sentiment [11:23–13:26, 17:16–19:13, 23:56–25:20]?
3. **The seed.** "MIT first" [15:27]: which MIT people? **Proposal:** researchers, faculty and alumni with public professional records, not students' social profiles. Then which Ivy League schools?
4. **LinkedIn.** Its terms forbid scraping (section 5). Do we accept synthetic stand-ins, plus data exports from volunteers who opt in?
5. **Sentiment.** In from week 3, or a stretch goal? News (GDELT) or social (Bluesky, X)? Amy noted there's prior work [18:44–18:56].
6. **Any model training?** Our deliverable isn't a model [20:50–21:13]. Does anyone want a small model inside it (for extraction, entity resolution or sentiment), or to post-train on the environment later [9:03–9:29, 20:29–20:47]?
7. **Tools.** A graph store (Neo4j, Postgres, or files plus NetworkX to start), Python, a GitHub repo, and one private place for raw data.
8. **Meetings.** The two sync times (Rebecca's When2Meet), and whether we keep the program's Thursday meeting [26:30–28:41].
9. **What "done" means.** Dominik asked for a clear deliverable and an "optimization function" [23:22–23:52], and for the return on the work [19:37–19:57]. **Proposal:** the agent answers at least 80% of the question set correctly, with sources.
10. **Privacy.** **Proposal:** an opt-out (we remove anyone who asks), no sensitive attributes, and only public figures or synthetic people in demos. Agreed?

## 11. Risks

**Proposal**, each tied to the kickoff where it came up:
- **The pipeline eats the month** [21:28–21:40]. Mitigation: time limits per connector, synthetic data as a fallback, and the agent working on a small graph by week 2.
- **A graph nobody uses** [22:16–22:32]. Mitigation: the question set comes first, and the graph grows to answer it.
- **Fit with the program** [13:31–13:53]. Mitigation: question 1, settled on Thursday.
- **Little time for some of us** [25:26–25:31, 28:15–28:28]. Mitigation: bounded pieces, and written updates in place of syncs.
- **Terms of use and privacy.** Mitigation: the data rules in section 5, checked once per source before we fetch anything.
