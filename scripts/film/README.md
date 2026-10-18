# Demo film (Puppeteer + Remotion)

The v3 submission film is built from real browser recordings of the app, with camera
moves, cursor, and click ripples driven by a log of what the script actually did.

1. **Isolated graph.** Approval writes `frozen`/`blocked` flags, so the film runs against a
   disposable copy (`GRAPH.COPY corridor → corridor_film`) served by a local API
   (`GRAPH_NAME=corridor_film`, port 8010) and a production web build on port 3010.
   `CORRIDOR_APPROVAL_TOKEN` must be set in the repository `.env`. The hosted demo graph is never touched.
2. **Narration.** `../../.venv/bin/python narrate.py`: OpenAI TTS per scene from
   `storyboard.json` (cached by text) and `public/timeline.json` with measured durations.
3. **Capture.** `node capture.mjs`: Puppeteer drives Chrome at 1920×1080 and records CDP
   screencast frames to H.264. Every cursor move, click, and focus region is logged with
   timestamps to `public/capture/*.json`. The live scene is a real `gpt-4.1-mini` run.
4. **Data.** `node build-data.mjs`: merges timing, logs, and the case's measured plan into
   `src/film.json`. Each recording plays at one uniform rate per scene (shown on screen as
   "N× SPEED" when above 1.1×).
5. **Render.** `npx remotion render src/index.ts Corridor out/corridor-v3.mp4 --codec h264 --crf 18`.

Zooms are editorial emphasis on logged regions; nothing in the app footage is altered.
Explainer cards (scratch-graph method, guardrails, evaluation) are drawn in Remotion and
use the case's real measurements and the committed evaluation results. The narration
voice is AI-generated (OpenAI `gpt-4o-mini-tts`). The recorded case and receipt are
listed in [docs/demo/film-manifest.json](../../docs/demo/film-manifest.json).
