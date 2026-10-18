# Submission video pipeline

The final film combines actual hosted browser recordings with original HTML/SVG
motion graphics. It does not fabricate application evidence or decisions.

Run from the repository root with Python/web dependencies installed. The pipeline
also needs FFmpeg (libx264, libass, drawtext), ffprobe, and Playwright Chromium.
The editing font path currently targets macOS Arial; update `edit.py` on another OS.

1. `.venv/bin/python scripts/video/narrate.py` — OpenAI TTS per scene. Cached WAVs
   prevent duplicate generation charges. Remove a scene WAV only to regenerate it.
2. `.venv/bin/python scripts/video/timeline.py` — derive scene lengths from WAV
   duration plus one second, rounded to 30 fps.
3. `node scripts/video/capture.mjs` — hosted footage; creates **one real model case**.
4. `node scripts/video/cards.mjs` — original animated graph/typography cards.
5. `.venv/bin/python scripts/video/edit.py` — editorial zooms and 0.5-second fades;
   audio has 0.3-second lead-in padding and a crossfade at chapter boundaries.
6. `.venv/bin/python scripts/video/caption.py` — timestamp transcription using
   `whisper-1`, aligned to the written script; export SRT and styled ASS captions.
7. Measure the assembled audio with FFmpeg `loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json`
   and save stderr as `docs/demo/production/loudness-analysis.log`.
8. `.venv/bin/python scripts/video/finish.py` — captioned H.264/AAC MP4, fast-start.

The checked-in storyboard and narration text describe exactly what is spoken.
Captured footage, audio, and intermediate exports are ignored; the final MP4 is a
release asset. The SRT sidecar is versioned. UI zooms and cursor rings are editorial
emphasis; conceptual cards are visibly separate from the real app.

All narration is AI-generated and disclosed in the film. No cloned human voice,
stock footage, third-party music, or invented model outcome is used. The live
investigation and recorded saved cases are traceable in `docs/m9-hosted-verification.json`.

Official API references:
- [Text to speech](https://developers.openai.com/api/docs/guides/text-to-speech)
- [Timestamped transcription](https://developers.openai.com/api/docs/guides/speech-to-text)
