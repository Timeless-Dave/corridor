# Corridor — submission draft

**One sentence:** A graph-native investigation agent for synthetic cross-border
payments, with traceable evidence, company context, and persisted case memory.

**Tracks:** Agents That Act on Connected Data; Agent Memory and Coordination;
Company Brain.

**Source:** https://github.com/Timeless-Dave/corridor

**Live app:** https://corridor-eosin.vercel.app/

**Video:** https://github.com/Timeless-Dave/corridor/releases/tag/submission-demo-v1

**Run locally:** Follow the root README. The app uses remote FalkorDB with verified
TLS, one FastAPI worker, and a Next.js investigation workspace. Docker is optional
for a local database. No private or real payment records are included.

**What the graph does:** Parameterized Cypher traces transfers, shared identifiers,
rotating savings pools, prior cases, policies, document provenance, decision
supersession, and corridor ownership. Findings and case relationships persist
in FalkorDB. The agent selects fixed tools; deterministic code controls verdict
eligibility. MCP clients can call the twelve read tools directly.

**Verified behavior:** Four planted patterns have executable graph proofs. Live
OpenAI investigations have been stored and inspected. A second account retrieves
an earlier case on its first tool call. The frontend supports incremental SSE,
Three.js evidence inspection, saved-case reload, and step-by-step replay.

**Limits:** All data and policy thresholds are fictional. Model interpretations
can be wrong; structural citation checks do not prove every sentence. This is a
single-worker demonstration, not production payment enforcement. No real funds
are frozen and no external ticket/email is sent.

**Before submitting:** Review this draft and complete the original README AI
disclosure accurately. The video uses disclosed AI narration; its live section
is condensed and saved-case sections are labeled. Do not claim unverified
participant authorship or query understanding.
