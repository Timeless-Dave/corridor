# Corridor: submission summary

**One line:** A compliance agent for cross-border payments that follows the money through a FalkorDB graph, tests a freeze on a copy before anyone applies it, and shows the path behind every decision.

**Tracks:** Agents That Act on Connected Data (primary) · Agent Memory and Coordination · Company Brain

**Links:** [Repository](https://github.com/Timeless-Dave/corridor) · [Live app](https://corridor-eosin.vercel.app/) · [Demo video](https://github.com/Timeless-Dave/corridor/releases/tag/submission-demo-v3) · [60-second update](https://github.com/Timeless-Dave/corridor/releases/tag/update-v4)

**Problem.** Mule rings on remittance corridors hide in the connections between transfers, and deciding what to freeze is as hard as finding them. Analysts piece both together by hand.

**What it does.** An agent picks fixed graph tools (cycles, fan-in, shared identifiers, pool payouts, PageRank, label propagation, shortest paths) based on what each result shows. Code decides whether a `FREEZE` stands: two independent evidence tools must cite the same account, plus a structural algorithm result and a measured freeze plan. Before a freeze, Corridor copies the graph, finds the exact minimum set of accounts to freeze with FalkorDB `algo.maxFlow`, and confirms it on a second copy. An operator approves; Corridor applies the block to the demo graph and writes a before/after receipt. Cases, findings and receipts live in the same graph, so the next investigation of any ring member recalls them on step one.

**Results (synthetic data).**
- FalkorDB Cloud, 2 repeats: 8/8 ring runs alerted, 0/16 decoy runs, `FREEZE` on 6/8 ring runs, each with a confirmed exact cut.
- On the same flags, a $500 per-transfer rule alerts on 0/4 rings; three common rules combined reach 4/4 only with 2/8 false alerts.
- At 1,021,450 transfers the evidence tools answer in under 1 ms.

**Graph.** Transactions (accounts, transfers, devices, phones, savings pools), company knowledge (policies, source documents, decisions with supersession, corridor owners) and memory (cases, findings, citations, freeze plans, receipts) in one FalkorDB graph. Every query is a parameterized `.cypher` file; the model never writes Cypher. The twelve read tools are also served over MCP.

**Limits.** Synthetic data and fictional policies; the 12-case evaluation is a smoke test. Approval is a demo gate with one operator token. Nothing real is frozen.

**AI assistance.** Designed, deployed and reviewed by Timeless-Dave; AI coding assistants (OpenAI Codex, Anthropic Claude Code) helped implement it.
