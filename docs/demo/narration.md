# Corridor submission narration

AI-generated voice: OpenAI `gpt-4o-mini-tts`, built-in `cedar` voice.
The live section is condensed; saved case scenes are labeled. All data is synthetic.

## CORRIDOR / GRAPH HACKS

A payment can look ordinary on its own. The pattern appears in the relationships. Corridor follows those connections, turning a synthetic payment flag into an investigation you can inspect, explain, and revisit.

## 01 / THE GRAPH MODEL

FalkorDB connects three layers: transactions and shared identifiers; company policies, documents, and owners; and memory from past cases. The graph does the retrieval and preserves the evidence. Remove it, and Corridor loses both its reasoning context and its memory.

## 02 / HOSTED WORKSPACE

Here is the deployed workspace, running on Vercel with a Render API. These four flags come from seeded, fully synthetic data. An analyst can inspect account history, then start an investigation. Each run gets its own case and evidence trail.

## 03 / LIVE INVESTIGATION · EDITED FOR TIME

This is a new investigation on the hosted app. Findings arrive as server sent events. The first tool checks prior cases. The agent then chooses from fixed graph tools, while the application records results and citations. The model never writes Cypher.

## 04 / SAVED EVIDENCE · INTERACTIVE GRAPH

The graph is an inspection surface. Select a finding to highlight its cited nodes. Orbit, zoom, or switch to a flat view. Exact transfer edges are highlighted only when the raw result identifies them; other connections remain context. Shared devices alone do not establish fraud.

## 05 / DETERMINISTIC GUARDRAILS

The model proposes a verdict. Deterministic code checks it. Freeze requires two distinct positive evidence tools corroborating the same account. Repeating one tool is not enough. Unsupported proposals and model failures require review. The actual outcome can be Monitor, even for a planted pattern.

## 06 / COMPANY CONTEXT · SAVED CASE

The decision stays connected to company context: an applicable policy and its source document, a current precedent and its author, and the employee responsible for this corridor. Superseded precedents are excluded. These are fictional demonstration policies, not regulatory advice.

## 07 / STEP-BY-STEP REPLAY

Why this decision opens the saved trail, step by step. Technical details reveal the parameters, raw results, and allowlisted query. A reviewer can inspect what the tool returned instead of relying only on the model's explanation.

## 08 / CROSS-ACCOUNT MEMORY · SAVED CASE

Now a different account: mule zero. Its first lookup retrieves the earlier collector case, through the graph's case membership relationships. The exact earlier case identifier appears in the raw result. This was verified across separate investigations. Memory survives the conversation because it lives in FalkorDB.

## CORRIDOR / BUILT TO BE EXPLAINED

Corridor also exposes twelve read tools over MCP. It brings connected-data investigation, agent memory, and company context into one workspace. All data is synthetic; no real funds are frozen. Explore the deployed app and public source. This narration uses an AI-generated OpenAI voice.
