# Engineering measures and review boundaries

Corridor is a working investigation prototype, demonstrated with realistic synthetic
payment scenarios. It records decisions and assignments; it does not control real
funds, contact customers, or create external tickets.

## Measures implemented

- **Constrained database access.** The model selects fixed tools. Cypher is held in
  versioned query files and values are parameterized. The browser cannot submit
  arbitrary queries. MCP exposes the twelve read tools, not case writers.
- **Evidence checks.** A FREEZE recommendation needs two distinct positive tools
  citing the same included account. Repeating one tool does not add corroboration.
  Invalid citations and model/tool errors trigger review behavior. This checks
  structural support; it does not establish that every interpretation is correct.
- **Connection protection.** TLS verifies certificates and hostnames when enabled.
  Database connections have timeouts and configuration errors omit credentials.
  API credentials stay on the server, outside browser bundles.
- **Bounded work.** Investigations have an analytical step cap. The API limits
  concurrent runs to four and rejects a duplicate active account investigation.
  These controls operate within the documented single-worker deployment.
- **Recoverable review.** Findings and case membership persist in FalkorDB.
  The interface deduplicates stream events and labels recovered snapshots.
- **Controlled reset.** Reset requires a server-side admin token and the exact
  configured graph name; it is disabled without that token. There is no reset UI.
- **Proven intervention bound.** Freeze plans copy the graph, compute an exact minimum vertex cut with FalkorDB `algo.maxFlow`, and re-measure that cut on a second disposable copy before a human can approve a modeled block.
- **Negative controls.** A synthetic eval runs four planted rings and eight decoys (shared family devices, legitimate pools, one-way business flow). Ground truth is not given to the model. Results are in `eval/results.json`.
- **Reviewable interface.** Text accompanies status colors. Keyboard controls,
  reduced motion, mobile layouts, and the accessible graph list have browser tests.

## Evidence, not blanket assurances

Historical release verification recorded 58 passing backend tests against remote
FalkorDB (see `m9-backend-tests.log`). The current interface revision passed five
unit tests, six browser workflows, TypeScript checking, and a production build.
Ten targeted backend checks also passed for connection configuration, guardrails,
and model-adapter behavior. The video verification report records the actual hosted run and media checks.
Automated tests are not an independent security audit or evidence of participant
manual review. No production accuracy, throughput, or regulatory certification
is claimed. Public-demo access is unauthenticated; institution isolation and
production identity/access controls are outside this prototype.

## Contribution record

The participant supplied the product direction, detailed milestone requirements,
design choices, deployment settings, and iterative review feedback. AI assistance
in this repository includes implementation, tests, debugging, documentation, and
video production. Specific claims about personally written code or personally
reviewed queries should be added only after the participant confirms them.
