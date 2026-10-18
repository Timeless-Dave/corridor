# Freeze-impact review

Corridor can measure a proposed account block on a disposable FalkorDB copy before an operator applies it to the demonstration graph. It does not freeze real funds.

## What is implemented

- Fixed `sim_*.cypher` queries are loaded through `agent/tools.py`.
- `Graph.copy()` issues FalkorDB `GRAPH.COPY`. A unique scratch name prevents different requests sharing state. Cleanup runs on success and measurement failure; failed cleanup is an error, not a successful plan.
- The model can call `simulate_freeze` for specified candidates or `min_freeze_set` for a **PageRank-ordered greedy heuristic**. The greedy order is a heuristic. Every plan also carries `min_cut`: an exact minimum vertex cut from FalkorDB `algo.maxFlow` on a node-split flow network in the scratch copy (candidate capacity 1, others 100,000), read from the residual graph and re-verified by blocking it on a second fresh copy. Minimum cardinality is proven by max-flow = cut size within the bounded scope; minimum disruption is not claimed.
- Candidates must be accounts already cited in that case. The measurement neighborhood adds their one-hop transfer neighbors and refuses scopes larger than 200 accounts.
- Measurements cover up to five directed hops, within 72 hours ending at the target account's latest transfer. All transfer paths counted must remain inside that neighborhood.
- Before/after measurements report accounts reaching the target, direct historical inflow to the target, and cycle paths through it. Inflow is not a forecast or a savings estimate. A cycle target is not necessarily a cash-out account.
- Label propagation supplies a structural community. Collateral reports affected counterparties outside that community and outside the candidate set. It does not establish that those people are innocent or completely disconnected.
- A FREEZE verdict requires two independent positive evidence tools citing the same account, recorded structural algorithm results, and a completed nonempty scratch plan. Algorithms and simulation results do not themselves count as suspicious evidence.

## Human approval

The new impact panel supports measurement on closed cases. Only a closed FREEZE case can be approved. Approval requires an operator token and an explicit confirmation for the stored plan ID. The token is entered manually, kept out of source, and forwarded only to the approval endpoint; an unset `CORRIDOR_APPROVAL_TOKEN` disables approval.

Before approval, the API checks the stored snapshot fingerprint and current measurements. Every selected account must have two positive evidence tools citing it. The single-worker demo serializes interventions. An approved order sets `Account.frozen=true` and `SENT.blocked=true`, preserving historical edges and findings. It then re-queries the active modeled routes and writes a `FreezeOrder → RECEIPT → Measurement` record linked to the case. A measurement failure leaves a visible `pending_measurement` order; it must not be described as a verified success. Repeated approvals are rejected.

This is a local/demo operator gate, not a production identity system. It is not transactional against writes from another process; the deployment uses one API worker. Future payment ingestion, blocking newly arriving transfers, rollback workflows and real payment-provider integration are outside this feature.

## Observed test outcomes

On the planted fan-in fixture, the real remote FalkorDB test measured **12 → 0** reachable senders and **4,866 → 0 USD** historical inflow when blocking `collector_0`. Applying the modeled block produced the same measurements. Blocking `mule_0` alone left **11** senders reachable. A competing plan was rejected after the underlying graph changed. These are real database tests with synthetic data and scripted case setup, not a claim of model reasoning or production effectiveness.

The initial full regression run found two failures: an obsolete expected seed-node count after adding decoys, and loss of the flagged membership role in aggregate case output. Both were corrected. The full backend suite (69 tests, live FalkorDB included) then passed.

October 18 fixes found while recording the demo:

- `open_case.cypher` used `UNION ALL`; FalkorDB executed the second branch's `CREATE` even when its filter removed the row, so every case was created twice (21 duplicated case IDs in the demo graph). The query is now a single branch with a regression test. Existing duplicates in the shared demo graph were left in place.
- A rejected simulation call (for example, no transfers in scope) was handed to the model for interpretation, which described it as "no resultant effect." Rejected calls now record the rejection reason deterministically.
- The simulation finding now separates *observed* exposure (live graph) from the *hypothetical* copy. One model run had read "after = 0" as "no inflow remains."

Real-model results: [eval/results.json](../eval/results.json) (4/4 rings alerted, 0/8 decoys; one FREEZE) and the earlier [eval/results-initial.json](../eval/results-initial.json) (1/8 decoys alerted). The demo film's case and receipt are listed in `scripts/film/public/capture/manifest.json` after a capture run.

## Review wording

Suggested panel title: **What would a freeze interrupt?**

Suggested narration: “A flag is only the start. Corridor tests a proposed freeze on a copy of the graph, measures which historical routes it would block, and shows affected counterparties. The greedy plan is a candidate, not a guaranteed minimum. After an operator approves, Corridor applies the modeled block and records whether the measured result matches the projection. This demonstration uses synthetic data; no real funds are frozen.”

Avoid claiming “smallest set,” “all money stops,” “innocent families protected,” or “money saved.” Those outcomes are not established by these measurements.

## Run and inspect

```bash
CORRIDOR_LIVE_TESTS=1 PYTHONPATH=api .venv/bin/python -m unittest api.tests.test_simulate -v
PYTHONPATH=api .venv/bin/python -m agent.loop cycle_0
PYTHONPATH=api .venv/bin/python eval/run.py
```

The tests and evaluation create disposable graphs. The investigation command creates a durable case in the configured graph but never approves its plan. `eval/run.py` evaluates four planted flags and eight decoys in isolated copies and saves raw traces plus alert precision/recall. Ground truth is not passed to the model. Named, hand-designed fixtures are not a blinded or held-out benchmark.

Endpoints: `GET /cases/{id}/freeze-impact`, `POST /cases/{id}/simulate-freeze`, and `POST /cases/{id}/approve-freeze`. There is no arbitrary-query endpoint and the existing read-only MCP server does not expose these write-bearing simulation tools.

References: [FalkorDB GRAPH.COPY](https://docs.falkordb.com/commands/graph.copy), [known Cypher limitations](https://docs.falkordb.com/cypher/known-limitations).
