# Freeze impact

Corridor measures what a freeze would interrupt on a disposable copy of the graph, then lets an operator apply it to the demo graph and records a receipt. Nothing real is frozen.

## Measurement

Code: [`api/agent/simulate.py`](../api/agent/simulate.py), queries `api/queries/sim_*.cypher`.

- **Candidates** are accounts already cited in the case. The scope adds their one-hop transfer neighbors, within 72 hours of the target's latest transfer, and is capped at 200 accounts.
- **Measures**, each counted only inside that scope: accounts reaching the target within five directed hops, direct historical inflow to the target, and cycle paths through it. Inflow is past volume, not a forecast.
- **Copies.** `GRAPH.COPY` creates a uniquely named scratch graph. It is deleted on success and on failure; a failed delete is reported as an error, never as a plan.
- **Exact cut.** On the scratch copy, every account in scope becomes `in → out` (capacity 1 for candidates, 100,000 for everyone else) and each transfer becomes `out → in`. `algo.maxFlow` runs from the reachable senders to the target, and the minimum vertex cut is read from the residual graph. Max flow equals the cut size, which proves the cut is minimal within the scope. The cut is then blocked on a second fresh copy and measured again. On FalkorDB builds without `algo.maxFlow` (4.18 and earlier), the plan says so and keeps the greedy result.
- **Greedy order.** Up to four candidates are removed in PageRank order until no sender reaches the target. Each step records the senders left and the counterparties affected outside the target's label-propagation community.
- **Fingerprint.** The plan stores a hash of the measured neighborhood so a later approval can detect that the graph changed.

The model calls this as `min_freeze_set` (greedy plus exact cut) or `simulate_freeze` (specified accounts). Its finding text is written by code and labels live-graph numbers separately from scratch-copy numbers.

## Approval

`POST /cases/{id}/approve-freeze` requires all of:

- an operator token matching `CORRIDOR_APPROVAL_TOKEN` (unset disables approval; the hosted demo leaves it unset) and an explicit confirmation flag;
- a closed `FREEZE` case and a stored plan for it;
- two independent positive evidence tools citing every account in the plan;
- an unchanged neighborhood fingerprint and unchanged measurements;
- no earlier order for the case.

It then sets `Account.frozen` and `SENT.blocked` (history is kept), measures again on the live graph and writes `(:FreezeOrder)-[:RECEIPT]->(:Measurement {before, after, matched_projection})`. If the second measurement fails, the order stays `pending_measurement` and the UI says so. The API runs one worker, which serializes approvals; this is a demo gate, not a production identity system.

## Tested outcomes

From `api/tests/test_simulate.py` against FalkorDB Cloud, on the planted fan-in ring:

| Check | Result |
|---|---|
| Greedy plan | `collector_0`: 12 → 0 senders, 4,866 → 0 USD |
| Exact cut | `collector_0`, max flow 1.0, confirmed on a fresh copy |
| Partial plan (`mule_0` only) | 11 senders still reach the collector |
| Approval | measured outcome matches the projection |
| Stale plan | rejected after the graph changed |
| Scratch graphs | none left behind |

In the cloud evaluation ([`eval/results-cloud.json`](../eval/results-cloud.json)), every `FREEZE` carried a confirmed exact cut: `cycle_4`, `collector_0`, `ajo_0`.

## Bugs found and fixed

- `open_case.cypher` used `UNION ALL`, and FalkorDB ran the second branch's `CREATE` even when its filter removed the row, so every case was created twice. It is now one branch with a regression test, and the 21 duplicate case nodes were removed from the hosted graph (backup graph `corridor_backup_20261018_dedupe`).
- A rejected simulation call was passed to the model, which described it as "no resultant effect". Rejected calls are now recorded with their reason and never interpreted.
- One model run read the copy's "after = 0" as "no inflow remains". The finding text now separates the live graph from the copy.

## Run

```bash
CORRIDOR_LIVE_TESTS=1 PYTHONPATH=api .venv/bin/python -m unittest api.tests.test_simulate -v
```

References: [GRAPH.COPY](https://docs.falkordb.com/commands/graph.copy), [algorithms](https://docs.falkordb.com/algorithms/).
