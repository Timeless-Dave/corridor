# Engineering measures

Corridor is a prototype on synthetic payment data. It records decisions and assignments; it doesn't move money, contact customers or open external tickets.

- **Fixed queries.** The model picks a tool and parameters. All Cypher lives in versioned `.cypher` files with parameters, and the browser cannot submit queries. MCP serves the twelve read tools only.
- **Evidence rules in code.** `FREEZE` needs two different positive evidence tools citing the same account, a structural algorithm result and a measured freeze plan. Repeating a tool adds nothing. Rejected citations and failed evidence tools force review. The decision panel shows this check for every closed case.
- **Measured interventions.** Plans run on `GRAPH.COPY` scratch graphs; the exact cut comes from `algo.maxFlow` and is confirmed on a second copy. Approval needs an operator token, an explicit confirmation and an unchanged graph fingerprint, and it writes a before/after receipt.
- **Connections.** TLS verifies certificates and hostnames. Database errors never include credentials, and API secrets stay server-side.
- **Bounded work.** Twelve evidence reads per investigation plus two grounding reads, at most four concurrent investigations, and one active investigation per account.
- **Reset.** Requires a server-side admin token and the exact graph name; there is no reset button in the UI.
- **Interface.** Status colors always have text labels. Keyboard controls, reduced motion, mobile layouts and the accessible graph list have browser tests.

## Verification

- 71 backend tests against FalkorDB Cloud (`CORRIDOR_LIVE_TESTS=1`), web unit tests, TypeScript checks and browser workflows.
- Agent evaluation on FalkorDB Cloud: 8/8 ring runs alerted, 0/16 decoy runs, `FREEZE` on 6/8 ring runs ([`eval/results-cloud.json`](../eval/results-cloud.json)).
- Scale: 1,021,450 transfers on embedded FalkorDB ([`eval/scale.json`](../eval/scale.json)).

Tests aren't a security audit. The public demo has no login, and per-institution isolation isn't built.
