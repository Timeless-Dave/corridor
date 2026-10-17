# Corridor: three-minute participant narration

This script describes real saved results. Do not promise that the model always
freezes a planted ring. Keep the synthetic-data label visible throughout.

- **0:00–0:20 — Queue.** “Corridor investigates synthetic cross-border payment
  flags using a graph. Transactions, company policies, and past investigations
  live in FalkorDB. Removing the graph removes the evidence and memory.”
- **0:20–0:55 — Investigation.** Start a fresh investigation or clearly label a
  saved replay. Show the first memory lookup, then select findings. Explain that
  each tool is fixed, parameterized Cypher; the model cannot write queries.
- **0:55–1:25 — Graph.** Orbit, fit, and switch to flat view. Select evidence and
  inspect cited nodes. Explain that teal edges indicate exact cited transfers;
  contextual links are muted. Shared identifiers alone are not proof of fraud.
- **1:25–1:55 — Decision.** Show the stored verdict and code-enforced checks.
  “FREEZE requires two distinct positive tools corroborating the same account.
  Model failures or unsupported proposals become MONITOR.” Describe the actual
  result shown. Expand company context: source document, current precedent,
  author, and corridor lead.
- **1:55–2:15 — Replay.** Click “Why this decision?”, step forward, and inspect raw
  results and the allowlisted query in Technical details.
- **2:15–2:45 — Memory.** Open the M7 collector case, then the M7 mule_0 case.
  Expand the first finding's raw result. Point to the exact collector case ID.
  “A different account recognizes the earlier case through INVOLVES on step one.
  This survives a new session because the memory is in FalkorDB.”
- **2:45–3:00 — Close.** Show the Browser query or MCP tool list. Name the three
  tracks: Agents That Act on Connected Data, Agent Memory and Coordination, and
  Company Brain. State that data and policies are fictional and decisions do not
  freeze real funds.

Use `docs/m7-live-verification.json` for the two actual case paths. Do not display
.env, hosting settings, or provider dashboards during recording. The automated
recording is a silent, saved-case walkthrough; add your own narration and query
explanation before submission. It is not footage of a newly running model.
