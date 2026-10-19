# Corridor

**A compliance agent for cross-border payments that follows the money through a graph, tests a freeze before anyone applies it, and shows the path behind every decision.**

Built on FalkorDB for **Graph Hacks: Context for AI Agents** (WeMakeDevs × FalkorDB, October 2026).
Tracks: **Track 01: Agents That Act on Connected Data** · Agent Memory and Coordination · Track 03: Company Brain.

[Live app](https://corridor-eosin.vercel.app/) · [Demo video](https://github.com/Timeless-Dave/corridor/releases/tag/submission-demo-v3) · [60-second update](https://github.com/Timeless-Dave/corridor/releases/tag/update-v4) · [Promo](https://github.com/Timeless-Dave/corridor/releases/tag/promo-v1) · [API](https://corridor-api.onrender.com/flags)

The API runs on Render's free tier. If the app is slow to load, open the API link once to wake it.

---

## The problem

Mule rings on remittance corridors hide in the connections between transfers. Twelve $50 contributions into a savings pool look harmless one at a time. They stop looking harmless when the four contributors share one phone with the account that collects every round.

Spotting that is half the job. The other half is deciding what to freeze: freeze too little and the money keeps moving, freeze too much and you lock out people who did nothing wrong. Analysts do both by hand, across spreadsheets, policy documents and old case notes.

## What Corridor does

1. **Investigates.** An agent walks the transaction graph, choosing the next fixed query or graph algorithm from what the last one returned.
2. **Decides.** It proposes `FREEZE`, `MONITOR` or `CLEAR`. Code checks the proposal: a freeze needs two independent evidence tools citing the same account, a structural algorithm result, and a measured freeze plan.
3. **Tests the freeze.** It copies the graph (`GRAPH.COPY`), blocks candidate accounts in the copy and measures who can still reach the ring's collector. FalkorDB `algo.maxFlow` returns the exact minimum set of accounts to freeze.
4. **Waits for a person.** An operator approves the plan. Corridor applies the block to the demo graph, measures again and writes a receipt.
5. **Grounds and routes.** It attaches the applicable policy, its source document, the current precedent and the corridor owner.
6. **Remembers.** A later investigation of any account in the same ring finds the earlier case on step one.
7. **Shows its work.** Every finding cites graph nodes. The UI highlights them, replays the investigation, and shows the fixed Cypher and raw result for each step.

## Check it in five minutes

| Claim | Where to see it |
|---|---|
| FalkorDB does the work | Detection, memory, company context and freeze simulation are graph queries in [`api/queries/`](api/queries/). Remove FalkorDB and nothing works. |
| The model never writes Cypher | It picks a tool name and parameters; every query is a fixed `.cypher` file. |
| A freeze is measured before it is applied | Open a closed case in the [live app](https://corridor-eosin.vercel.app/), scroll to **What would a freeze interrupt?**, click **Re-run simulation**. The panel prints the exact max-flow cut and confirms it on a fresh copy. |
| You can see why a FREEZE stood | The **Freeze rule check** in the decision panel lists which tools cite which account, the algorithm results and the scratch plan. |
| Memory lives in the graph | `prior_cases` walks `Account ← INVOLVES ← Case`. Start `POST /investigate/ajo_1` after an `ajo_0` case exists: step one returns that case. |
| It beats per-transfer rules | [Results](#results): rule baselines on the same flags. |
| It scales past the demo | [Results](#results): 1,021,450 transfers in one graph; 100 institutions as 100 isolated graphs on one server. |

---

## Results

All numbers come from files in [`eval/`](eval/), on the synthetic dataset.

### Agent evaluation

[`eval/run.py`](eval/run.py) runs the real agent (`gpt-4.1-mini`) on 4 planted rings and 8 decoys: families sharing a device, rotating savings pools paying out normally, and one-way business senders and receivers. Each case runs on its own graph copy, and ground truth never reaches the model. An alert is `FREEZE` or `MONITOR`.

| Run | Rings alerted | Decoys alerted | FREEZE on rings |
|---|---|---|---|
| [Initial](eval/results-initial.json) | 4 / 4 | 1 / 8 | 1 / 4 |
| [After removing old case narratives from model input](eval/results.json) | 4 / 4 | 0 / 8 | 1 / 4 |
| [Corroboration status shown to the model, 2 repeats, embedded FalkorDB](eval/results-repeat.json) | 8 / 8 | 0 / 16 | 6 / 8 |
| [Same, on FalkorDB Cloud with a 12-read budget, 2 repeats](eval/results-cloud.json) | **8 / 8** | **0 / 16** | **6 / 8** |

On FalkorDB Cloud, every decoy closed `CLEAR`. The cycle, fan-in and pool rings reached `FREEZE` in both runs, each with an exact max-flow cut confirmed on a fresh copy (`cycle_4`, `collector_0`, `ajo_0`). The shared-device ring stays `MONITOR`: device sharing is its only evidence type, so the two-tool rule can't be met.

The change behind the jump: before each tool choice, the model now sees the same bookkeeping the guardrail uses: which positive tools cite which account, and what is still missing. One intermediate wording ("otherwise MONITOR") caused two false MONITORs on family decoys; it was replaced and the run repeated. No prompt or rule names a specific account.

### Rule baselines on the same flags

[`eval/baselines.py`](eval/baselines.py) scores three common per-account rules, with thresholds fixed in advance ([`baselines.json`](eval/baselines.json)).

| Method | Rings | Decoys |
|---|---|---|
| Per-transfer amount ≥ $500 (the demo policy threshold) | 0 / 4 | 2 / 8 |
| Incoming velocity ≥ 10 transfers in 48 h | 1 / 4 | 0 / 8 |
| Shared device or phone with ≥ 3 accounts | 3 / 4 | 0 / 8 |
| Any of the three | 4 / 4 | 2 / 8 |
| **Corridor agent** | **4 / 4** | **0 / 8** |

The device rule does well partly because the family decoys sit one account under its cutoff. No single-account rule catches the circular ring; that takes following the transfers back to where they started.

### Scale

[`eval/scale.py`](eval/scale.py) merges 50 independently seeded worlds into one graph on an embedded FalkorDB and times the agent's tools on one world's rings ([`scale.json`](eval/scale.json)).

**103,100 accounts · 1,021,450 transfers · 409,550 nodes**, one laptop process.

| Tool | Median |
|---|---|
| `fan_in` (finds all 12 mule senders) | 0.3 ms |
| `circular_flows` (finds the 5-account cycle) | 0.5 ms |
| `shared_identifiers` | 0.2 ms |
| `collector_rank` (PageRank over the whole graph) | 54 ms |
| `ring_communities` (label propagation over the whole graph) | 1.09 s |
| Freeze plan: `GRAPH.COPY`, cut, re-measure | 6.0 s |

The fan-in ring is still found and cut (12 → 0 senders). Whole-graph label propagation and `GRAPH.COPY` dominate; production would copy only the investigated neighborhood. The embedded build is FalkorDB 4.18 without `algo.maxFlow`, so the exact cut reports itself unavailable there instead of failing.

### One graph per institution

Each institution gets its own FalkorDB graph (`corridor_<tenant>`); the API picks it from the `X-Tenant` header, checked against `CORRIDOR_TENANTS`. [`eval/tenants.py`](eval/tenants.py) loads 100 independently seeded institutions onto one embedded FalkorDB ([`tenants.json`](eval/tenants.json)):

| Measure | Result |
|---|---|
| Graphs on one server | 100 (≈2,060 accounts and 20,400 transfers each) |
| Memory | 824 MB total, 8.2 MB per institution |
| `fan_in` / `circular_flows` / `shared_identifiers`, median across 20 sampled tenants | 0.28 / 0.44 / 0.28 ms |
| Case opened in tenant A, history read through the API as tenant B | not visible |
| Unknown tenant | 404 |

```bash
.venv/bin/pip install falkordblite                       # embedded FalkorDB, benchmarks only
PYTHONPATH=api .venv/bin/python eval/tenants.py 100
PYTHONPATH=api .venv/bin/python eval/scale.py 50
PYTHONPATH=api .venv/bin/python eval/baselines.py
.venv/bin/python eval/run.py --repeat 2                  # add --embedded to skip the cloud
```

---

## How it decides

### Agent loop ([`api/agent/loop.py`](api/agent/loop.py))

1. Open a `Case` linked to the flagged account.
2. Call `prior_cases`. A prior `FREEZE` raises the starting risk to 0.7.
3. Up to 12 evidence reads. Before each one, the model sees the account metadata, the findings so far and the corroboration status. After each read, the loop records a `Finding` with the model's one-sentence interpretation and the IDs it cites; citations that aren't in the result are rejected.
4. Two reserved reads: `corridor_context` and `precedents`.
5. The model returns a structured verdict. Code applies the guardrails, then `close_case` writes the verdict, members, policy, precedent and assignee.

Interpretations of the memory lookup, PageRank, label propagation and freeze simulation are generated by code, not the model, so they can't overstate what those tools show.

### Guardrails ([`api/agent/guardrails.py`](api/agent/guardrails.py))

- `FREEZE` needs one account cited by two different positive evidence tools (`circular_flows`, `fan_in`, `shared_identifiers`, `ajo_payout_pattern`, `link_to_known_bad`), a completed `collector_rank` or `ring_communities`, and a completed `min_freeze_set`. Otherwise it becomes `MONITOR` and the reason is stored on the case.
- Algorithms, simulations, prior cases and policy text never count as evidence of wrongdoing.
- A rejected tool call is recorded as rejected, never interpreted by the model.
- An unknown account closes `CLEAR` with `error=unknown_account`, which the UI shows as an input error, not a clearance.
- Document and policy text is passed as delimited data; the system prompt tells the model not to follow instructions in it.

### Freeze simulation ([`api/agent/simulate.py`](api/agent/simulate.py))

1. Scope: the accounts cited in the case plus their one-hop transfer neighbors, within 72 hours of the collector's latest transfer; at most 200 accounts.
2. `GRAPH.COPY` to a disposable graph. Measure senders reaching the collector (≤ 5 hops), historical inflow and cycle paths.
3. **Exact cut.** Split each account into `in → out` (capacity 1 for cited candidates, effectively unlimited for everyone else), run `algo.maxFlow` from the reachable senders to the collector, and read the minimum vertex cut from the residual graph. Block it on a second fresh copy and measure again.
4. **Greedy order.** Remove up to four candidates in PageRank order, stopping once no sender reaches the collector, recording each step and the counterparties affected outside the ring's community.
5. Delete the copies. Save the plan with a fingerprint of the measured neighborhood.

Approval (`POST /cases/{id}/approve-freeze`) needs an operator token, an explicit confirmation, a closed `FREEZE` case, two independent tools behind every frozen account, and an unchanged fingerprint. It sets `Account.frozen` and `SENT.blocked`, measures again and writes `(:FreezeOrder)-[:RECEIPT]->(:Measurement)`. The hosted demo leaves the token unset, so approval is off there. No real funds are involved. Details: [`docs/IMPACT.md`](docs/IMPACT.md).

---

## Graph data model

One FalkorDB graph, three layers.

**Transactions**

```
(:Person)-[:OWNS]->(:Account {id, country, type, kyc_tier, flagged, frozen})
(:Account)-[:SENT {id, amount, currency, ts, corridor, pool_id, round, purpose, blocked}]->(:Account)
(:Account)-[:USED]->(:Device {fingerprint})
(:Account)-[:REGISTERED]->(:Phone {number})
(:Account)-[:MEMBER_OF {round_position}]->(:AjoPool {id})
(:Account)-[:PAID]->(:Merchant)
```

**Company**

```
(:Employee)-[:MEMBER_OF]->(:Team)-[:OWNS]->(:Corridor {code})
(:Employee)-[:LEADS]->(:Corridor)
(:Doc)-[:DEFINES]->(:Policy {id, rule, threshold})-[:APPLIES_TO]->(:Corridor)
(:Decision {outcome})-[:BASED_ON]->(:Policy)
(:Decision)-[:MADE_BY]->(:Employee)
(:Decision)-[:SUPERSEDES]->(:Decision)
```

**Memory and actions (written by the agent)**

```
(:Case {verdict, risk, pattern})-[:INVOLVES {role}]->(:Account)
(:Case)-[:HAS_FINDING]->(:Finding {step, tool, params, result_json, text})-[:CITES]->(any)
(:Case)-[:APPLIED]->(:Policy)  (:Case)-[:PRECEDENT]->(:Decision)  (:Case)-[:ASSIGNED_TO]->(:Employee)
(:Case)-[:HAS_FREEZE_PLAN]->(:FreezePlan)-[:APPROVED_AS]->(:FreezeOrder)-[:RECEIPT]->(:Measurement)
```

Range indexes: `Account.id`, `Device.fingerprint`, `Phone.number`, `Case.id`, `Corridor.code`, `Policy.id`.

### Tools

| Tool | What it asks the graph |
|---|---|
| [`shared_identifiers`](api/queries/shared_identifiers.cypher) | Who else uses this device or phone? |
| [`circular_flows`](api/queries/circular_flows.cypher) | Does money come back within 2–5 hops and 72 hours? |
| [`fan_in`](api/queries/fan_in.cypher) | How many small transfers reached this account in 48 hours? |
| [`ajo_payout_pattern`](api/queries/ajo_payout_pattern.cypher) | Is one member paid in consecutive rounds by contributors on its device? |
| [`link_to_known_bad`](api/queries/link_to_known_bad.cypher) | Shortest path, over transfers and shared identifiers, to an account in an earlier `FREEZE` case (`algo.SPpaths`) |
| [`collector_rank`](api/queries/collector_rank.cypher) | PageRank over `SENT` |
| [`ring_communities`](api/queries/ring_communities.cypher) | Label propagation communities |
| [`connected_cluster`](api/queries/connected_cluster.cypher) | Accounts joined through shared devices and phones (`algo.WCC`) |
| [`prior_cases`](api/queries/prior_cases.cypher) | Earlier cases involving this account |
| [`corridor_context`](api/queries/corridor_context.cypher), [`precedents`](api/queries/precedents.cypher), [`who_knows`](api/queries/who_knows.cypher) | Corridor owner and policies; current precedent (superseded decisions excluded); who decided past cases of this pattern |
| `min_freeze_set`, `simulate_freeze` | Scratch-graph measurement and exact cut ([`sim_*.cypher`](api/queries/)) |

The twelve read tools are also served over MCP: `cd api && ../.venv/bin/python -m mcp_server` ([client setup](docs/M8.md)). Case writes and approvals are not exposed over MCP.

---

## Architecture

```
Next.js 16 (web/)  ──HTTP/SSE──▶  FastAPI (api/)  ──falkordb-py──▶  FalkorDB Cloud
  queue, case view,                 agent loop, guardrails,           one graph:
  3D/flat graph panel,              freeze simulation,                transactions,
  replay, freeze panel              MCP server (read tools)           company, memory
```

| Part | Choice |
|---|---|
| Graph | FalkorDB Cloud (hosted demo), one graph per institution; Docker or `falkordblite` locally |
| API | FastAPI, Server-Sent Events, one worker |
| Model | OpenAI Responses API with function calling (`OPENAI_MODEL`, default `gpt-4.1-mini`) |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind, Three.js via `@react-three/fiber` |
| Hosting | Vercel (web), Render (API) |

### API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/flags` | Flagged accounts with latest transfer and case history |
| `POST` | `/investigate/{account_id}` | Start an investigation; returns `case_id` |
| `GET` | `/cases/{case_id}/stream` | Live steps over SSE |
| `GET` | `/cases/{case_id}` | Case, findings, cited evidence, grounding, rule check |
| `GET` | `/cases/{case_id}/subgraph` | Nodes and edges for the graph panel |
| `GET` | `/accounts/{account_id}/history` | Earlier cases for an account |
| `GET` | `/cases/{case_id}/freeze-impact` | Stored freeze plan and receipts |
| `POST` | `/cases/{case_id}/simulate-freeze` | Re-run the scratch-graph measurement |
| `POST` | `/cases/{case_id}/approve-freeze` | Apply a plan (operator token required) |
| `POST` | `/admin/reset` | Token-protected reload of the configured graph |

Every route except reset accepts an optional `X-Tenant` header that selects that institution's graph.

---

## Synthetic data

Generated by [`api/data/generate.py`](api/data/generate.py) with seed 42. No real people or accounts.

- About 2,000 background accounts and 20,000 transfers between the US and Nigeria, 30 legitimate savings pools, and families that share devices.
- Four planted rings: circular layering (5 accounts, skimming at each hop), fan-in mules (12 senders → 1 collector in 48 h, each under the threshold), a shared-device cluster (9 accounts, 2 devices, 3 phones), and ajo-pool abuse (one member paid in consecutive rounds by contributors on its device).
- Eight decoys that look suspicious to simple rules (see [Results](#results)).
- A company layer: 3 teams, 12 employees, 2 corridors, 6 policies with source documents, and 8 past decisions, one superseded.

Ground truth lives in [`api/data/ground_truth.json`](api/data/ground_truth.json), outside the graph.

---

## Run it locally

Requirements: Python 3.11+, Node 20+, an OpenAI API key, and FalkorDB (Cloud, or `docker compose up -d` for a local server and Browser).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.lock.txt
npm ci --prefix web
test -f .env || cp .env.example .env      # add FalkorDB and OpenAI settings

cd api && ../.venv/bin/python -m data.generate --seed 42 && ../.venv/bin/python -m data.load && cd ..
./scripts/run-local.sh                    # API on :8000, web on http://localhost:3001
```

For a local Docker FalkorDB set `FALKORDB_HOST=127.0.0.1`, `FALKORDB_PORT=6379`, `FALKORDB_TLS=false`. `data.load` refuses to overwrite a populated graph unless given `--reset`. To enable approval locally, set `CORRIDOR_APPROVAL_TOKEN`. To serve several institutions, load each into `corridor_<name>` (`GRAPH_NAME=corridor_acme ../.venv/bin/python -m data.load`) and set `CORRIDOR_TENANTS=acme,…`.

Tests: `cd api && CORRIDOR_LIVE_TESTS=1 ../.venv/bin/python -m unittest discover -s tests` (72 tests, live FalkorDB), plus `npm test --prefix web` and `npm run typecheck --prefix web`.

```
api/
  agent/        loop.py, guardrails.py, simulate.py, tools.py, model.py, prompts.py, schemas.py
  queries/      every Cypher query as a .cypher file
  data/         generate.py, load.py, ground_truth.json
  mcp_server/   MCP server for the read tools
  tests/
web/            Next.js app
eval/           agent eval, rule baselines, scale benchmark, results
scripts/        local launcher, demo-film pipelines
docs/           build records, freeze-impact notes, demo assets
```

---

## Limitations

- **Synthetic data.** Rings and decoys were written by the same team; the 12-case evaluation is a smoke test, not real-world accuracy.
- **Verdicts vary between runs.** The model may spend its budget before finding a second independent tool; the case then closes `MONITOR` and the rule check shows why.
- **Whole-graph algorithms.** PageRank, label propagation and `GRAPH.COPY` run on the full graph. Production would project the neighborhood first.
- **Demo-grade approval.** One shared operator token, a single API worker, and no real payment-system integration.

---

## Hackathon compliance

| Rule | How Corridor meets it |
|---|---|
| 2 · FalkorDB is the primary database | It is the only database. |
| 3 · The graph does real work | Detection, memory, routing and freeze simulation are graph queries and algorithms. |
| 5 · Tracks named | See the top of this file. |
| 6 · Permitted data | Synthetic, generated from a fixed seed. |
| 8 · Built during the event | See [Build timeline](#build-timeline). |
| 10 · Deliverables | Public repo, setup, data model, Cypher in `api/queries/`, demo video, live deployment. |
| 11 · AI disclosure | Below. |

### AI assistance

Timeless-Dave designed Corridor: the problem, the three-layer graph model, the tool set, the planted rings and decoys, the freeze rules and the milestone plan, then deployed, tested and reviewed every stage. AI coding assistants (OpenAI Codex, Anthropic Claude Code) helped implement it under that direction. The demo narration uses OpenAI text-to-speech.

### Build timeline

Corridor was built locally after kickoff (October 14, 1:31 PM CDT) and first committed once the core was working, so the first commit is large. History has not been rewritten. Local file-creation times (CDT):

| When | Evidence |
|---|---|
| Oct 16, 13:27 | Project folder and `.git` created |
| Oct 16, 13:55 | First source files: `generate.py`, `tools.py`, `db.py`, `docker-compose.yml` |
| Oct 17, 10:23 – 14:50 | Milestone records `docs/m1…m9-verification.json`, in order, each with its own timestamp |
| Oct 17, 16:08 | First commit `5b930cb` |
| Oct 17 – 18 | Hosting, demo, freeze simulation and evaluation in later commits |

File-creation times are local metadata, not proof; the milestone records in [`docs/`](docs/) carry their own timestamps.

---

## License

MIT
