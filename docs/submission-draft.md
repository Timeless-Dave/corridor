# Corridor — submission draft

**One sentence:** A graph-native investigation agent for synthetic cross-border
payments, with traceable evidence, company context, and persisted case memory.

**Tracks:** Agents That Act on Connected Data; Agent Memory and Coordination;
Company Brain.

**Source:** https://github.com/Timeless-Dave/corridor

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

**Before submitting:** Add the final deployment/local-demo choice and hosted video
URL, replace this draft with participant-approved text, and complete the original
README AI disclosure accurately. Do not represent the silent saved-case recording
as a live model run or claim unverified participant authorship/query understanding.
