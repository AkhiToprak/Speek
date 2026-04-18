# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (first run)
pip install -r requirements.txt

# Dev server (auto-reload) — open http://127.0.0.1:8000
uvicorn main:app --reload

# Production-ish run
uvicorn main:app --host 0.0.0.0 --port 8000
```

There is no test suite, linter, or build step configured.

## Architecture

Speek is a single-user TTS web app. Two files carry the whole product:

- **`main.py`** — FastAPI app with three surfaces:
  - `GET /voices` wraps `edge_tts.list_voices()` and returns a trimmed, sorted list `{id, name, locale, gender}`. `name` is derived from `ShortName` by stripping the `Neural`/`Multilingual` suffix (see `_display_name`).
  - `POST /generate` streams MP3 bytes from `edge_tts.Communicate(text, voice).stream()` as a `StreamingResponse` — nothing is buffered to disk or to memory as a whole blob server-side.
  - `GET /` returns `static/index.html`; `/static/*` is mounted via `StaticFiles`. Root is served explicitly (not via StaticFiles) so the page lives at `/` while assets live at `/static/`.

- **`static/index.html`** — single-file frontend (inline CSS + JS, no framework, no build). On load it fetches `/voices`, groups options into `<optgroup>`s by language using `Intl.DisplayNames`, and defaults to `en-US-AriaNeural` (falling back through `en-US` → any `en-` → first voice). The Listen and Export buttons share one `generate()` call that posts to `/generate` and receives the audio as a `Blob`; Listen wires it to an `<audio>` element via `URL.createObjectURL`, Export triggers a download `<a>` with a filename slugified from the first ~48 chars of the input text. `Cmd/Ctrl+Enter` in the textarea triggers Listen.

Because edge-tts is the entire engine, there is no model, database, auth, or job queue — requests are 1:1 with MSFT edge-tts calls and failures propagate as HTTP 4xx/5xx with `detail` messages that the frontend surfaces in the status line.

## Design system (frontend)

The UI commits to a warm-paper editorial aesthetic; changes should stay inside this vocabulary rather than drift toward generic SaaS:

- **Typography**: `Instrument Serif` italic for display (title, textarea body), `Geist` sans for UI, `Geist Mono` for metadata/labels. All loaded from Google Fonts.
- **Palette** (CSS custom properties on `:root`): `--bg` warm ivory, `--paper`/`--paper-hi` surfaces, `--ink` near-black, `--accent` terracotta `#C44A28` reserved for the primary CTA hover, numbered section markers, and the waveform. Do not introduce a second accent.
- **Section pattern**: each form block uses a monospace `block-head` of `[num] [label] [meta]` where `num` is `01`/`02`/`03` in accent color. New blocks should follow this rhythm.
- **Motion**: single `rise` keyframe for staggered entrance, a `wave` keyframe for the 5-bar loading indicator. Both are disabled under `prefers-reduced-motion`.
