# Corridor

**A graph-native compliance agent for cross-border payments.**

Corridor investigates flagged money transfers on US ↔ Nigeria remittance corridors. It walks the transaction graph to find mule rings, applies the company's own policies, routes the case to the person who owns that corridor, and shows the exact path of nodes and edges behind every decision.

> Built for **Graph Hacks: Context for AI Agents** (WeMakeDevs × FalkorDB, Oct 14–18, 2026)
> **Tracks entered:** Track 01: Agents That Act on Connected Data · Agent Memory and Coordination · Track 03: Company Brain

---

[Live app](https://corridor-eosin.vercel.app/) · [Demo video](https://github.com/Timeless-Dave/corridor/releases/tag/submission-demo-v3) · [API](https://corridor-api.onrender.com/flags)

## Status

All nine milestones (M1–M9) are built, deployed, and submitted. Evidence is in [docs/](docs/).

**What a returning judge can check in this repo**

| Rubric | Where it lives |
|---|---|
| FalkorDB is the system of record | Transactions, company knowledge, and case memory are one graph. Removing it removes detection, routing, and recall. |
| The model cannot write Cypher | Fixed files in [`api/queries/`](api/queries/). The agent only picks a tool name and parameters. |
| Memory survives the chat | `prior_cases` walks `Account ← INVOLVES — Case` in FalkorDB. A second account retrieves the earlier case on step one. |
| Company knowledge is graph data | Policy, source document, current precedent (superseded decisions excluded), and corridor owner. |
| A freeze is measured before it is applied | `GRAPH.COPY`, then FalkorDB `algo.maxFlow` for an exact minimum vertex cut, re-measured on a second copy. A person approves; the receipt records whether the outcome matches the projection. |
| You can see why a FREEZE stood | The decision panel's **Freeze rule check** recomputes the guardrail from stored findings: which account two independent positive tools cite, the structural algorithm results, and the scratch plan. The model sees the same corroboration status before every tool choice. |
| Negative controls exist | [`eval/results-repeat.json`](eval/results-repeat.json): 8/8 ring runs alerted, 0/16 decoy runs, FREEZE on 6/8 ring runs (`gpt-4.1-mini`, 2 repeats). Rule baselines on the same flags: [`eval/baselines.json`](eval/baselines.json). Synthetic smoke test, not a production accuracy claim. |

Live app, video, and API are linked above. Wake the free Render instance via `/flags` before opening the app.

**What the live product already proves**

- The model selects the next fixed tool. Application code accepts or downgrades the verdict. A freeze still needs two independent positive evidence tools, recorded PageRank or community results, and a completed scratch plan.
- `algo.maxFlow` returns an exact minimum vertex cut inside the 72-hour neighborhood. A second disposable copy blocks that cut and checks that zero senders still reach the collector. The impact panel prints that line on a closed case.
- A rejected scratch-graph call is recorded as “Tool call rejected” and does not, by itself, cancel a freeze that the evidence rules already support.
- Case memory, policy, precedent, and the corridor owner are graph reads. The workspace replays each finding with its parameters, raw result, and fixed Cypher.
- Per-transfer rules miss these rings. On the same 12 flags, a $500 threshold alerts on 0/4 rings (and 2/8 decoys); all three common rules combined reach 4/4 only with 2 false alerts. The agent: 4/4 rings, 0/8 decoys; over two repeats 8/8 and 0/16 ([baselines](#rule-baselines-on-the-same-flags)).
- It scales past the demo. At 50× (103,100 accounts, 1,021,450 transfers) the anchored evidence tools answer in under 1 ms and every planted ring is still found and cut ([scale benchmark](#scale-benchmark-50-the-demo-graph)).
- The seeded graph is synthetic. The decoy eval is a smoke test, not a production accuracy claim. Corridor's claim is a closed loop a judge can click: investigate, inspect the path, measure the cut, approve, read the receipt.

Approved spec corrections: the circular ring contains five distinct accounts;
ajo transfers carry pool/round/purpose metadata. Thresholds are fictional demo rules.
The seed creates 2,000 background accounts plus 30 planted accounts, 20,000 background
transfers plus planted/pool transfers, 30 legitimate pools and one abusive pool.
Ground truth remains in a local JSON file, outside the graph.

## Table of contents

1. [The problem](#the-problem)
2. [What Corridor does](#what-corridor-does)
3. [Why a graph](#why-a-graph)
4. [Architecture](#architecture)
5. [Graph data model](#graph-data-model)
6. [Synthetic data](#synthetic-data)
7. [Agent tools: Cypher and algorithms](#agent-tools-cypher-and-algorithms)
8. [Agent loop](#agent-loop)
9. [Traceability](#traceability)
10. [API](#api)
11. [Frontend](#frontend)
12. [Setup](#setup)
13. [Repository structure](#repository-structure)
14. [Demo script](#demo-script)
15. [Hackathon compliance](#hackathon-compliance)
16. [AI assistance disclosure](#ai-assistance-disclosure)
17. [Limitations](#limitations)
18. [Build plan](#build-plan)

---

## The problem

Fraud on remittance corridors rarely shows up in a single transaction. It lives in the connections between them: ten "unrelated" senders who share two phones, money that leaves an account and comes back four hops later, an ajo (rotating savings) pool where one member collects every round.

Compliance analysts piece this together by hand across spreadsheets, transaction logs, and internal docs. Even after they spot a ring, they still have to find out which policy applies, who owns the corridor, and whether the team has made a ruling on a similar case before. That knowledge lives in people's heads and scattered documents.

## What Corridor does

1. **Investigates.** Given a flagged transfer, the agent explores the transaction graph hop by hop, choosing which query or algorithm to run next based on what the previous one returned.
2. **Detects.** It identifies four ring patterns: circular layering, fan-in mule collection, shared-device clusters, and ajo-pool abuse.
3. **Decides.** It issues a verdict of `FREEZE`, `MONITOR`, or `CLEAR`, with a risk score.
4. **Grounds the decision in the company.** It finds the policy that applies, the precedent case it resembles, and the person who owns the corridor.
5. **Acts.** It writes the case, findings, and verdict back to the graph and routes the case to its owner.
6. **Remembers.** When an account returns in a later session, the agent finds the earlier case before doing anything else.
7. **Explains.** Every claim cites the nodes and edges it came from, and the UI highlights that subgraph.

## Why a graph

Every question Corridor answers is a question about connections:

| Question | Graph operation |
|---|---|
| Who else uses this device or phone? | 2-hop pattern match |
| Does money come back to where it started? | Variable-length cycle `[:SENT*2..5]` |
| Which account collects from the ring? | PageRank over `SENT` |
| Which accounts form a cluster? | WCC / label propagation |
| Who owns this corridor, and who decided the last similar case? | Traversal across the company layer |
| Have we seen this account before? | Memory lookup via `(:Case)-[:INVOLVES]->(:Account)` |

**Removal test (Rule 3):** without FalkorDB, Corridor cannot find rings, cannot score collectors, cannot route cases, and cannot recall past cases. Nothing in the product works without the graph.

---

## Architecture

```
┌──────────────────────────┐        ┌───────────────────────────────┐
│  Next.js 16 (web/)       │  HTTP  │  FastAPI (api/)               │
│  - Flagged queue         │◄──────►│  - /cases, /investigate       │
│  - Case view + verdict   │  SSE   │  - streams agent steps        │
│  - Graph panel (path     │        │                               │
│    highlighting)         │        │  Agent loop (agent/)          │
└──────────────────────────┘        │  - OpenAI API tool use        │
                                    │  - tools = fixed Cypher       │
                                    │    queries + algorithms       │
                                    └──────────────┬────────────────┘
                                                   │ falkordb-py
                                    ┌──────────────▼────────────────┐
                                    │  FalkorDB                     │
                                    │  graph: corridor              │
                                    │  - transaction layer          │
                                    │  - company layer              │
                                    │  - memory layer               │
                                    └───────────────────────────────┘
                                    ┌───────────────────────────────┐
                                    │  MCP server (mcp/)            │
                                    │  same tools, exposed over MCP │
                                    │  for Claude Desktop / others  │
                                    └───────────────────────────────┘
```

| Layer | Choice |
|---|---|
| Graph database | FalkorDB (Docker locally, FalkorDB Cloud in production) |
| Graph client | `falkordb` (Python) |
| API | FastAPI, Server-Sent Events for streaming agent steps |
| Agent | OpenAI Responses API with tool use |
| Tool protocol | MCP server (`mcp` Python SDK, FastMCP) wrapping the same tool functions |
| Frontend | Next.js 16.4.2 (App Router), React 19.3.1, TypeScript, Tailwind, Three.js |
| Graph visualization | `react-force-graph-2d` |
| Data generation | Python + Faker, seeded for reproducibility |
| Deploy | Vercel (web), Railway or Render (API), FalkorDB Cloud (graph) |

**Design decision: fixed queries, not text-to-Cypher.** The agent chooses between hand-written, parameterized, tested Cypher tools. It never writes Cypher itself. This keeps every query safe, reviewable, and explainable, and it means the reasoning trail always maps to a known query.

---

## Graph data model

One graph named `corridor` with three layers.

### Transaction layer (Track 01)

```
(:Person   {id, name, country})
(:Account  {id, country, type, opened_at, kyc_tier, flagged})
(:Device   {fingerprint, os})
(:Phone    {number, country})
(:Merchant {id, name, category})

(:Person)-[:OWNS]->(:Account)
(:Account)-[:SENT {id, amount, currency, ts, corridor, pool_id, round, purpose}]->(:Account)
(:Account)-[:PAID {amount, ts}]->(:Merchant)
(:Account)-[:USED {first_seen, last_seen}]->(:Device)
(:Account)-[:REGISTERED]->(:Phone)
(:Account)-[:MEMBER_OF {round_position}]->(:AjoPool {id, name, contribution, cycle_days})
```

`corridor` is a string such as `US-NG` or `NG-US`. `ts` is a Unix epoch integer. Ajo transfers additionally carry `pool_id`, zero-based `round`, and `purpose: "ajo_payout"`; these distinguish consecutive payouts from ordinary transfers. Domestic pool transfers use `NG-NG`; company ownership covers the two cross-border corridors.

### Company layer (Track 03)

```
(:Employee {id, name, role})
(:Team     {id, name})
(:Corridor {code})                    // e.g. 'US-NG'
(:Policy   {id, title, rule, threshold})
(:Doc      {id, title, source, updated_at})
(:Decision {id, summary, date, outcome})

(:Employee)-[:MEMBER_OF]->(:Team)
(:Team)-[:OWNS]->(:Corridor)
(:Employee)-[:LEADS]->(:Corridor)
(:Doc)-[:DEFINES]->(:Policy)
(:Policy)-[:APPLIES_TO]->(:Corridor)
(:Decision)-[:MADE_BY]->(:Employee)
(:Decision)-[:BASED_ON]->(:Policy)
(:Decision)-[:SUPERSEDES]->(:Decision)
```

### Memory layer (agent writes here)

```
(:Case    {id, status, verdict, risk, opened_at, closed_at, pattern})
(:Finding {id, step, text, tool, query_name, params, created_at})

(:Case)-[:INVOLVES {role}]->(:Account)        // role: 'flagged' | 'collector' | 'member'
(:Case)-[:HAS_FINDING]->(:Finding)
(:Finding)-[:CITES]->(:Account|:Device|:Phone|:Policy|:Decision)
(:Case)-[:ASSIGNED_TO]->(:Employee)
(:Case)-[:PRECEDENT]->(:Decision)
(:Case)-[:APPLIED]->(:Policy)
```

### Indexes

```cypher
CREATE INDEX FOR (a:Account) ON (a.id)
CREATE INDEX FOR (d:Device) ON (d.fingerprint)
CREATE INDEX FOR (p:Phone) ON (p.number)
CREATE INDEX FOR (c:Case) ON (c.id)
CREATE INDEX FOR (c:Corridor) ON (c.code)
CREATE INDEX FOR (p:Policy) ON (p.id)
```

---

## Synthetic data

All data is synthetic and generated by `data/generate.py` with a fixed seed (Rule 6). No real people, accounts, or companies are used.

**Background population:** about 2,000 accounts across US and Nigeria, about 20,000 transfers with realistic amount distributions, shared devices at a low natural rate (families), and about 30 legitimate ajo pools.

**Planted patterns** (known ground truth, recorded in `data/ground_truth.json`):

| # | Pattern | Shape |
|---|---|---|
| 1 | Circular layering | 5 accounts; money flows A→B→C→D→E→A within 72h, with small amounts skimmed at each hop |
| 2 | Fan-in mule | 12 low-KYC senders → 1 collector within 48h, each under the reporting threshold |
| 3 | Shared-device cluster | 9 accounts, 4 people, 2 devices, 3 phones |
| 4 | Ajo-pool abuse | Pool where the same member is paid out in consecutive rounds, and contributors share devices with that member |

Patterns 1 and 3 overlap on two accounts, so the agent has to connect findings across tools.

**Company layer:** 3 teams, 12 employees, 2 corridors (`US-NG`, `NG-US`), 6 policies, 6 docs, and 8 past decisions. One decision is superseded by a newer one, to test that the agent picks the current ruling.

**Seed history:** one past `Case` already involves an account from ring #2, so the memory demo works on first load.

---

## Agent tools: Cypher and algorithms

The agent dispatches fixed tools on `agent.tools.CorridorTools`: twelve investigation reads, two scratch-graph measurements (`simulate_freeze`, `min_freeze_set`), and three case writers. All query
text lives in `api/queries/` and is loaded by `tools.py`. The model-facing dispatch
allowlist excludes raw query helpers and ingestion. OpenAI exposure is implemented in M3; MCP exposes the twelve read tools; raw case writers stay internal to preserve verdict guardrails.

See [M2 tool contracts and Browser review](docs/M2.md) for signatures, parameters,
return values, live compatibility findings, and test commands. Executable sources:

- [`shared_identifiers`](api/queries/shared_identifiers.cypher)
- [`circular_flows`](api/queries/circular_flows.cypher)
- [`fan_in`](api/queries/fan_in.cypher)
- [`ajo_payout_pattern`](api/queries/ajo_payout_pattern.cypher)
- [`ring_communities`](api/queries/ring_communities.cypher)
- [`connected_cluster`](api/queries/connected_cluster.cypher)
- [`collector_rank`](api/queries/collector_rank.cypher)
- [`link_to_known_bad`](api/queries/link_to_known_bad.cypher)
- [`corridor_context`](api/queries/corridor_context.cypher)
- [`precedents`](api/queries/precedents.cypher)
- [`who_knows`](api/queries/who_knows.cypher)
- [`prior_cases`](api/queries/prior_cases.cypher)
- [`open_case`](api/queries/open_case.cypher)
- [`record_finding`](api/queries/record_finding.cypher)
- [`close_case`](api/queries/close_case.cypher)

`open_case` supplies the fifteenth tool required by the agent loop. Read tools return
JSON-compatible records; writes return receipts. Empty findings use a separate fixed
[query](api/queries/record_empty_finding.cypher) under the same `record_finding` tool.

**Validated corrections to the initial draft:** circular flows use static 2–5-hop
branches with explicit ordered aliases and honor `max_hops`; fan-in uses a bounded
48-hour window; ajo uses pool/round/purpose metadata; known-bad links use bidirectional
`algo.SPpaths` because this server rejects undirected `shortestPath`. Company results
include stable IDs, memory can exclude the current case, and finding parameters are
JSON strings. PageRank, WCC, and label propagation all run on FalkorDB.

M2 validates persistence and reference integrity. M3 implements verdict guardrails,
validates model citation IDs against actual tool results, and handles unknown-account closure.
Live OpenAI verification completed for all four planted patterns; actual outcomes are recorded in docs/M3.md.

---

## Agent loop

`agent/loop.py`

1. **Open a case.** Create a `Case` node linked to the flagged account (`role: 'flagged'`).
2. **Check memory.** Always call `prior_cases` first. If a prior `FREEZE` exists, say so and raise the starting risk.
3. **Investigate.** The OpenAI model chooses tools in a loop (max 12 steps). After each tool result, the loop calls `record_finding` with the model's one-sentence interpretation and the IDs it cites.
4. **Ground in the company.** Before deciding, the agent must call `corridor_context` and `precedents`.
5. **Decide.** The model returns structured output:
   ```json
   {
     "verdict": "FREEZE | MONITOR | CLEAR",
     "risk": 0.0,
     "pattern": "circular_layering | fan_in_mule | shared_device | ajo_abuse | none",
     "members": ["acct_..."],
     "policy_id": "POL-AML-4",
     "precedent_decision_id": "DEC-112",
     "assignee_employee_id": "emp_...",
     "rationale": "..."
   }
   ```
6. **Act.** Call `close_case` to write the verdict and route the case to the assignee.
7. **Emit events.** M3 emits JSON events and supports a callback; M5 delivers these over SSE.

### Guardrails

- **Hard rules in code, not in the model.** A `FREEZE` requires at least two independent findings from different tools that cite the same account. If the model returns `FREEZE` without that, the loop downgrades it to `MONITOR` and records why. The README and UI say clearly which parts the code decides and which parts the model decides.
- **Empty results** are recorded with raw results and interpretation source as findings ("No shared devices found") so the absence of evidence is visible.
- **Unknown account ID:** after the mandatory memory lookup, the case closes as `CLEAR` with an error finding and `error=unknown_account`; this is not a compliance clearance.
- **Step cap:** after 12 steps the agent must decide with what it has, and the UI shows that the cap was reached.
- **Ingested doc text** is treated as data. Policy text is passed inside delimited blocks and the system prompt tells the model not to follow instructions in it.

---

## Traceability

Every `Finding` is linked by `CITES` edges to the exact nodes it relied on. In the case view:

- the reasoning trail lists each step: tool name, parameters, result summary, interpretation
- clicking a step highlights the cited nodes and edges in the graph panel
- the verdict card shows the applied policy (with its source doc), the precedent decision (and who made it), and the assignee

Query to reconstruct any case's evidence:
```cypher
MATCH (c:Case {id: $case_id})-[:HAS_FINDING]->(f:Finding)
OPTIONAL MATCH (f)-[:CITES]->(n)
RETURN f.step, f.tool, f.text, collect(coalesce(n.id, n.fingerprint, n.number)) AS cited
ORDER BY f.step
```

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/flags` | Seed-flagged accounts, latest transfer, and prior-case status |
| `POST` | `/investigate/{account_id}` | Start an investigation; returns `case_id` |
| `GET` | `/cases/{case_id}/stream` | SSE stream of agent steps |
| `GET` | `/cases/{case_id}` | Case, findings, verdict, cited subgraph |
| `GET` | `/cases/{case_id}/subgraph` | Nodes and edges for the graph panel |
| `GET` | `/accounts/{account_id}/history` | Prior cases for an account |
| `POST` | `/admin/reset` | Explicit token-protected reset of the confirmed configured graph |

---

## Frontend

Three screens:

1. **Queue:** flagged transfers with amount, corridor, and a "returning account" badge when prior cases exist.
2. **Investigation:** live reasoning trail on the left, graph panel on the right, with nodes appearing as the agent touches them.
3. **Verdict:** verdict, risk, ring members, applied policy, precedent, assignee, and a "Why?" button that replays the cited path.

No graph or Cypher knowledge is required to use it. Each step is written in plain language, with the query available in an expandable panel for technical viewers.

---

## Setup

### Requirements

- Docker
- Python 3.11+
- Node.js 20+
- An OpenAI API key

### 1. Install dependencies (from the repository root)

Python 3.14 and Node 24 were used for verification. Install exact recorded dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.lock.txt
npm ci --prefix web
test -f .env || cp .env.example .env
```

Do not overwrite an existing `.env`. Add your own FalkorDB Cloud connection and
OpenAI settings there. Cloud TLS uses certificate and hostname verification.
For optional local FalkorDB, `docker compose up -d` starts **only the database and
Browser**; set `FALKORDB_HOST=127.0.0.1`, `FALKORDB_PORT=6379`, and
`FALKORDB_TLS=false`, with empty username/password. Browser is on port 3000.

### 2. Generate and load a new graph

```bash
cd api
../.venv/bin/python -m data.generate --seed 42
../.venv/bin/python -m data.load
cd ..
```

Skip loading if the demo graph is already populated. Loading refuses to overwrite
existing data; `--reset` is an explicit destructive option, never part of startup.

### 3. Run the local demo

From the repository root:

```bash
./scripts/run-local.sh
```

Open http://localhost:3001. The launcher starts one FastAPI worker on port 8000
and Next.js on port 3001; Ctrl+C stops both. Set `API_PORT`/`WEB_PORT` to override.
For separate terminals, run the commands in [M6 setup](docs/M6.md).

For a production frontend, run `npm run build --prefix web`, then
`npm start --prefix web`, with the API running separately. `CORRIDOR_API_URL` is a
**server-only** frontend setting; there is no `NEXT_PUBLIC_API_URL`. Neither API
credentials nor the admin reset token should appear in browser configuration.

### 4. Optional MCP access

```bash
cd api
../.venv/bin/python -m mcp_server
```

See [M8 client setup](docs/M8.md) for the twelve read tools. Case writes remain
behind the guarded investigation loop. [M9 release notes](docs/M9.md) track
hosting, demo recording, and remaining participant-owned submission work.

---

## Repository structure

```
corridor/
├── api/
│   ├── main.py              # FastAPI app
│   ├── db.py                # FalkorDB connection
│   ├── agent/
│   │   ├── loop.py          # investigation loop
│   │   ├── tools.py         # Cypher-backed tool functions
│   │   ├── schemas.py       # tool definitions + verdict schema
│   │   ├── guardrails.py    # deterministic verdict rules
│   │   └── prompts.py       # system prompt
│   ├── mcp_server/
│   │   └── __main__.py      # FastMCP server wrapping tools.py
│   ├── data/
│   │   ├── generate.py      # synthetic data + planted rings
│   │   ├── load.py          # bulk load into FalkorDB
│   │   └── ground_truth.json
│   ├── queries/             # every Cypher query as a .cypher file
│   └── tests/
│       ├── test_queries.py  # each query against the seeded graph
│       └── test_rings.py    # agent finds all 4 planted rings
├── web/                     # Next.js App Router app
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Demo script

The 3-minute film ([scripts/film](scripts/film/README.md)) follows one real case end to end:

1. Review queue → investigate `ajo_0`, the payout account of a rotating savings pool (ajo).
2. Live `gpt-4.1-mini` run: earlier cases from graph memory, shared device, PageRank,
   payout pattern, then a scratch-graph freeze measurement. Code lets FREEZE stand because
   two independent evidence tools cite `ajo_0`.
3. Freeze impact: `GRAPH.COPY`, block in the copy, re-measure (4 → 0 senders, $200 → $0
   historical inflow, 0 outside-community counterparties). Exact minimum cut via `algo.maxFlow`, verified on a fresh copy.
4. Human approval with an operator token and explicit confirmation → modeled block applied →
   re-measured receipt that matches the projection.
5. Traceability: cited accounts light up in the graph; technical details show the fixed Cypher
   and raw result; policy, source document, precedent and corridor lead.
6. Guardrails and the synthetic evaluation, with their limits.

The film was recorded against a disposable copy of the demo graph so the approval does not
change the hosted demo. The case, receipt and every live attempt are in
[docs/demo/film-manifest.json](docs/demo/film-manifest.json).

---

## Hackathon compliance

| Rule | How Corridor meets it |
|---|---|
| 2: FalkorDB primary | FalkorDB is the only database |
| 3: Graph does real work | Detection, routing, memory, and traceability all run on the graph |
| 5: Tracks named | Track 01 and Track 03 |
| 6: Permitted data | Fully synthetic, generated by `data/generate.py` |
| 8: Built during event | First commit after Oct 14, 2026, 1:31 PM CDT |
| 10: Deliverables | Public repo, this README, Cypher in `api/queries/`, demo video, deployment link |
| 11: AI disclosure | See below |

---

## Project direction and engineering

Timeless-Dave led the product direction, supplied the milestone specifications and
design requirements, configured deployment services, and reviewed the evolving
workspace and demo. The project was developed with substantial AI assistance;
automated verification is recorded separately from participant manual review.
See [implemented engineering measures and review boundaries](docs/ENGINEERING.md).

## AI assistance disclosure

Timeless-Dave supplied the product direction, milestone requirements and design feedback,
configured the deployment services, and reviewed the evolving product and demo.
OpenAI Codex generated substantial implementation, Cypher, deterministic guardrails,
frontend components, tests, documentation and recording/editing scripts under that direction.
Codex also ran automated checks and investigated their failures. These automated checks
are not a claim that the participant manually reviewed every file or query.
Anthropic Claude Code (October 18) fixed tool-error handling in the agent loop, built the
Puppeteer + Remotion demo-film pipeline in `scripts/film/`, and edited this README.

OpenAI speech generation produced the demo narration. At runtime, Corridor uses the
OpenAI Responses API (`OPENAI_MODEL`, default `gpt-4.1-mini`) to select fixed tools and
interpret their results. Application code enforces verdict requirements; the model
cannot execute arbitrary Cypher or approve an intervention.

The participant is responsible for understanding and explaining the submitted work.
Manual Browser review and participant understanding are not certified by automated tests.

## Build timeline

Corridor was built locally after kickoff (October 14, 2026, 1:31 PM CDT) and first
committed once M1–M9 were working, so the first public commit is large. Git history
has not been rewritten or backdated. Local evidence (macOS file-creation times, CDT):

| When | Evidence |
|---|---|
| Oct 16, 13:27 | Project folder and `.git` created (`git init`) |
| Oct 16, 13:55–13:58 | First source files (`generate.py`, `tools.py`, `db.py`, `docker-compose.yml`), Python venv, `docs/M1.md` |
| Oct 17, 10:23 | M1 verification record (`verified_at` 15:23 UTC inside the file) |
| Oct 17, 10:32–14:50 | M2–M9 milestone docs and verification records, in order |
| Oct 17, 16:08 | First commit `5b930cb` imports the working M1–M9 build |
| Oct 17 20:18 – Oct 18 | Hosted verification, demo, freeze-impact simulator and evaluation (later commits) |

File-creation times are local metadata, not a cryptographic proof; the milestone
records under [docs/](docs/) carry their own timestamps. No code predates kickoff.

---

## Measured freeze impact

Corridor now tests candidate account blocks on a disposable FalkorDB graph copy.
The impact panel compares reachable senders, historical inflow and cycle paths,
then shows affected counterparties. Alongside the PageRank-ordered greedy plan, it computes
the **exact minimum freeze set** with FalkorDB `algo.maxFlow`: every in-scope account is split
into `in → out` (capacity 1 for cited candidates, effectively infinite otherwise), max-flow runs
from the reachable senders to the collector, and the min vertex cut is read from the residual
graph. The cut is then blocked on a second fresh copy and re-measured, so "minimum" is proven
(max-flow = cut size) and "disconnects every sender" is measured, not assumed
(`api/queries/sim_flow_*.cypher`, `sim_max_flow.cypher`). Scope stays the bounded 72-hour
neighborhood. A separate operator approval applies modeled blocks and records a before/after
receipt; no real funds are frozen.

See [scope, approval controls, evidence and review wording](docs/IMPACT.md).

### Evaluation on synthetic data

`eval/run.py` runs the real agent (`gpt-4.1-mini`) over 4 planted rings and 8 decoys
(families legitimately sharing a device, rotating savings pools paying out normally,
one-way business senders and receivers). Each case runs in an isolated graph copy; ground
truth is never passed to the model. An *alert* is FREEZE or MONITOR.

| Run | Alerts on rings | False alerts on decoys | Precision | Recall | FREEZE verdicts |
|---|---|---|---|---|---|
| [Initial](eval/results-initial.json) | 4 / 4 | 1 / 8 (`business_receiver` → MONITOR) | 0.80 | 1.00 | `cycle_0` |
| [Final code](eval/results.json) | 4 / 4 | 0 / 8 | 1.00 | 1.00 | `ajo_0` |
| [Corroboration status, 2 repeats](eval/results-repeat.json) | **8 / 8** | **0 / 16** (every decoy CLEAR) | **1.00** | **1.00** | **6 / 8 ring runs**: `cycle_0`, `collector_0`, `ajo_0` both times |

The latest change shows the model the same evidence bookkeeping the FREEZE guardrail uses
(which account which positive tools cite, what is still missing) plus a plain verdict guide
(no positive evidence → CLEAR). FREEZE on ring runs went from 1 / 4 to 6 / 8 with no false
alerts. `shared_0` stays MONITOR in both runs by design: device and phone sharing is its only
evidence type, so the two-independent-tools rule cannot be met. The repeat run used an embedded
FalkorDB (`--embedded`; no `algo.maxFlow` there, so the greedy scratch plan satisfies the rule).
A first attempt at this change said "otherwise MONITOR" and produced two false MONITORs on family
decoys; that wording was replaced and the run above is the rerun.

Between runs the code changed (old case narratives removed from model input, simulator
scope aligned); no prompt or rule names a specific decoy account. Twelve hand-designed synthetic
fixtures are not a benchmark: the decoy definitions and rings were written by the same
team, and verdicts vary between runs (most ring cases stay at MONITOR because the
FREEZE guardrails are strict). Treat these as a smoke test, not real-world accuracy.

### Rule baselines on the same flags

`eval/baselines.py` scores three common per-account monitoring rules on the identical 12 flags.
Thresholds were fixed before running and not tuned to the flags; results are in
[`eval/baselines.json`](eval/baselines.json).

| Method | Rings alerted | Decoys alerted | Precision | Recall |
|---|---|---|---|---|
| Per-transfer amount ≥ $500 (the demo policy threshold) | 0 / 4 | 2 / 8 | 0.00 | 0.00 |
| Incoming velocity ≥ 10 transfers in 48 h | 1 / 4 | 0 / 8 | 1.00 | 0.25 |
| Shared device or phone with ≥ 3 accounts | 3 / 4 | 0 / 8 | 1.00 | 0.75 |
| Any of the three | 4 / 4 | 2 / 8 | 0.67 | 1.00 |
| **Corridor agent** ([results.json](eval/results.json)) | **4 / 4** | **0 / 8** | **1.00** | **1.00** |

Honest reading: the shared-device rule scores well partly because the family decoys have exactly
three members, just under its cutoff. The circular ring is caught only by following transfers
back to their start, which no single-account rule does. The rules and the fixtures were written
by the same team.

### Scale benchmark (50× the demo graph)

`eval/scale.py` merges 50 independently seeded worlds (ids prefixed per world) into one graph on
an embedded FalkorDB (`falkordblite`, one laptop process) and times the agent's real tools on
one world's planted rings. Raw output: [`eval/scale.json`](eval/scale.json).

| Graph | Accounts | Transfers | Nodes |
|---|---|---|---|
| 50 worlds | 103,100 | 1,021,450 | 409,550 |

| Tool (median) | Time |
|---|---|
| `fan_in` (finds all 12 mule senders) | 0.3 ms |
| `circular_flows` (finds the 5-account cycle) | 0.5 ms |
| `shared_identifiers` | 0.2 ms |
| `collector_rank` (global PageRank) | 54 ms |
| `ring_communities` (global label propagation) | 1.09 s |
| Full freeze plan: `GRAPH.COPY` + greedy cut + re-measure | 6.0 s |

The greedy plan still cuts the fan-in ring (12 → 0 senders). The embedded build is FalkorDB
4.18, which has no `algo.maxFlow`; the exact cut reports that explicitly instead of failing
(FalkorDB Cloud 4.22 runs it, see the live API). What does not scale for free: label propagation
and `GRAPH.COPY` are whole-graph operations, so production would copy a projected neighborhood
and precompute communities. Five unindexed labels (Person, AjoPool, …) needed range indexes at
this size; the benchmark creates them.

## Limitations

- **Synthetic data.** Ring patterns are planted, so detection quality on real data is unproven.
- **Global algorithms.** PageRank and label propagation run over the whole graph and are filtered afterwards. Measured at 1M transfers: PageRank 54 ms, label propagation 1.1 s, full-graph `GRAPH.COPY` dominates a 6 s freeze plan. Production would project the neighborhood first.
- **No real integrations.** Routing to an assignee is recorded in the graph; no email or ticketing system is connected.
- **Single tenant.** Per-institution isolation would use FalkorDB's multi-graph support (one graph per institution), which is not implemented.
- **The model can misread results.** Guardrails catch unsupported `FREEZE` verdicts but not every misinterpretation.

---

## Build plan

Ordered for the hackathon window. Each milestone must be working before the next starts.

- [x] **M1: Graph up.** FalkorDB running, schema and indexes created, `generate.py` and `load.py` produce the full graph, all 4 rings visible in the FalkorDB Browser.
- [x] **M2: Queries.** Every query in `api/queries/` runs against the seeded graph; `test_queries.py` passes; each planted ring is found by at least one transaction tool.
- [x] **M3: Agent.** `loop.py` runs end to end from the command line for each ring and writes `Case`, `Finding`, and `CITES` correctly; guardrail downgrade is tested.
- [x] **M4: Company layer.** Corridor context, precedents, and routing work; the superseded decision is never used.
- [x] **M5: API + SSE.** All endpoints work; steps stream.
- [x] **M6: Frontend.** Queue, live investigation view with graph panel, verdict card, "Why?" replay.
- [x] **M7: Memory demo.** Second flag in the same ring hits the earlier case on step one.
- [x] **M8: MCP server.** Tools callable from an MCP client.
- [x] **M9: Ship.** FalkorDB Cloud + Render API + Vercel, narrated demo, README and AI disclosure. Submitted to Graph Hacks.

**Cut line:** if time runs short, drop M8 first, then M4 (submit for Track 01 only).

---

## License

MIT