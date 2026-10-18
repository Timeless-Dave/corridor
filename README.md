# Corridor

**A graph-native compliance agent for cross-border payments.**

Corridor investigates flagged money transfers on US ↔ Nigeria remittance corridors. It walks the transaction graph to find mule rings, applies the company's own policies, routes the case to the person who owns that corridor, and shows the exact path of nodes and edges behind every decision.

> Built for **Graph Hacks: Context for AI Agents** (WeMakeDevs × FalkorDB, Oct 14–18, 2026)
> **Tracks entered:** Track 01: Agents That Act on Connected Data · Track 03: Agent Memory and Coordination · Company Brain

---

[Live app](https://corridor-eosin.vercel.app/) · [Demo video](https://github.com/Timeless-Dave/corridor/releases/tag/submission-demo-v2) · [API](https://corridor-api.onrender.com/flags)

## Implementation status — hosted demo and video ready

M1 and M2 are complete: all 26 tests passed, including live remote validation. The seeded demo graph is loaded and the fifteen fixed query tools are implemented. See [M2 evidence](docs/m2-verification.json) and [the Browser review guide](docs/M2.md). M3 is implemented and live-verified with OpenAI: all four planted patterns produced persisted cases, and all 41 regression tests passed. See [M3 setup and guardrails](docs/M3.md). M4 adds a read-only company verifier and tests both corridor routes, invalid references, and supersession changes before closure. See [M4 verification and Browser guide](docs/M4.md). M5 implements all seven API endpoints and SSE streaming; 53 tests passed and a real OpenAI investigation completed over HTTP. See [M5 API guide](docs/M5.md). M6 adds the dark Three.js investigation workspace; unit, browser, production-build, and live OpenAI verification passed. See [M6 setup and verification](docs/M6.md). M7 verifies cross-account memory: a second account retrieves the earlier case on step one. Live OpenAI, isolated graph, and browser checks passed. See [M7 memory demo](docs/M7.md). M8 exposes the twelve read tools over local stdio MCP; protocol verification against FalkorDB passed. See [M8 client setup](docs/M8.md). M9 is deployed and a hosted OpenAI investigation passed through Vercel/Render; the narrated submission video is available. Local release checks passed (58 backend tests, frontend build, and browser checks). The participant-owned AI disclosure and final submission remain open. See [release status](docs/M9.md).
The remaining architecture and setup sections describe the planned M9 product,
not functionality already shipped. Follow [the M1 runbook](docs/M1.md) for current setup,
tests, remote connection instructions, and Browser proofs. No API key is needed for M1.

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

M2 implements fifteen fixed tools as methods on `agent.tools.CorridorTools`. All query
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

**Target length: 3 minutes.** Follow [the participant narration script](docs/demo/script.md).

1. Show the four synthetic queue flags and explain the three graph layers.
2. Start an investigation or explicitly identify a saved replay. Show the first
   memory lookup and the evidence trail; the model only calls fixed tools.
3. Select evidence, inspect the graph, and explain cited transfers versus contextual links.
4. Show the actual stored verdict and guardrail interventions, then the policy,
   source document, current precedent, author, and corridor lead. Do not promise
   FREEZE: the live model has returned conservative MONITOR outcomes.
5. Click “Why this decision?” and replay the cited evidence.
6. Open the M7 second account (`mule_0`): its step-one raw memory result includes
   the earlier `collector_0` case. Use the exact paths in `docs/m7-live-verification.json`.
7. Explain the corresponding Cypher in Browser or demonstrate the MCP read tools.

The final narrated video combines a real hosted investigation with labeled saved-case replay,
original motion graphics, and AI-generated OpenAI narration. See [M9 video details](docs/M9.md).

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

AI coding assistants were used during this project. *(List the specific tools and what each was used for before submitting, for example: frontend components, boilerplate, test scaffolding.)*

The graph data model, the Cypher queries, the planted ring patterns, and the agent's decision guardrails were designed and written by the author, who can explain each one.

At runtime, Corridor uses the **OpenAI Responses API** (`OPENAI_MODEL`, default `gpt-4.1-mini`) to choose tools and write plain-language interpretations. The hard rule requiring two independent findings before a `FREEZE` is enforced in code, not by the model.

---

## Limitations

- **Synthetic data.** Ring patterns are planted, so detection quality on real data is unproven.
- **Global algorithms.** PageRank and label propagation run over the whole graph and are filtered afterwards. At production scale they would run on a precomputed schedule or a projected subgraph.
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
- [ ] **M9: Ship.** Deployed (FalkorDB Cloud + API host + Vercel), demo video recorded, README finalized with the AI disclosure filled in.

**Cut line:** if time runs short, drop M8 first, then M4 (submit for Track 01 only).

---

## License

MIT