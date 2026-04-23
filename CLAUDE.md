# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Base install (first run)
pip install -r requirements.txt

# Optional: character voices via RVC (adds rvc-python + torch)
pip install -r requirements-rvc.txt
# macOS / Windows also need ffmpeg on PATH for the RVC path:
brew install ffmpeg          # macOS
winget install ffmpeg        # Windows

# Dev server (auto-reload) — open http://127.0.0.1:8000
uvicorn main:app --reload

# Production-ish run
uvicorn main:app --host 0.0.0.0 --port 8000
```

There is no test suite, linter, or build step configured.

## Architecture

Speek is a single-user TTS web app with two engines:

- **edge-tts** — 400+ MSFT neural voices. Cheap, streams MP3 straight through.
- **RVC (optional)** — voice conversion; reshapes an edge-tts clip to sound like a specific character (e.g. Family Guy cast). Requires `rvc-python` + `ffmpeg` + user-supplied `.pth` weights.

### Backend (`main.py`)

- `GET /voices` wraps `edge_tts.list_voices()` into `{id, name, locale, gender}`. `_display_name` strips the `Neural`/`Multilingual` suffix from `ShortName`.
- `GET /characters` returns `{rvc_available, characters, catalogue}`. `characters` only lists entries from `characters.json` whose `.pth` exists under `models/<id>/`, so the dropdown never offers a broken option. `catalogue` is the full JSON so tooling can show "not installed yet" characters.
- `POST /generate` dispatches on the `voice` field:
  - Plain edge-tts voice ID → streaming MP3 straight from `edge_tts.Communicate(...).stream()`, nothing buffered server-side.
  - `rvc:<character_id>` → runs `_generate_character_mp3`: edge-tts saves an MP3, `ffmpeg` converts to 44.1 kHz mono WAV, `RVCInference.infer_file` produces a converted WAV, `ffmpeg` re-encodes to 160 kbps MP3. Temp files are cleaned up in the streaming generator's `finally`.
- `GET /` returns `static/index.html`; `/static/*` is mounted via `StaticFiles`.

### RVC pipeline details

- **Lazy init**: `RVCInference` is constructed only on first character request (`_get_rvc`); import failure becomes a 500 with setup instructions rather than a startup crash.
- **Device**: `_detect_device` honours `$SPEEK_RVC_DEVICE`, else picks `cuda:0` → `mps` (Apple Silicon) → `cpu`.
- **Single-model state**: rvc-python's instance holds one loaded model; `_load_rvc_for` skips `load_model` when the requested `.pth` is already current, and swaps otherwise. A `Lock` serialises inference since the instance is not thread-safe.
- **Param setting is defensive**: `set_params` / `set_index` are called behind `hasattr` + try/except because rvc-python's minor versions differ on accepted kwargs.
- **`characters.json`** is hot-reloaded (no restart needed) and stores `{name, base_voice, pitch, note}` per character. `base_voice` is the edge-tts voice used as the RVC source; `pitch` is semitones of shift passed as `f0up_key`.
- **`models/<id>/`** must contain a `.pth` (required) and optionally an `.index` (improves timbre match). Filenames inside the folder are not significant — first match wins. `.gitignore` excludes `models/*/`, `models/*.pth`, `models/*.index`.

### Frontend (`static/index.html`)

Single-file, inline CSS + JS, no framework, no build. On load it fetches `/voices` and `/characters` in parallel, groups edge-tts voices into `<optgroup>`s by language via `Intl.DisplayNames`, and prepends a `Family Guy · RVC` optgroup whose option values carry an `rvc:` prefix. Default voice cascades `en-US-AriaNeural` → any `en-US` → any `en-` → first voice.

Listen and Export share one `generate()` call that POSTs to `/generate`; Listen plays the returned `Blob` via `<audio>` + `URL.createObjectURL`, Export triggers a download `<a>` with a filename slugified from the first ~48 chars of the text. Status line copy switches between "Synthesising voice…" and "Running RVC — 20–60s…" based on whether the selected voice starts with `rvc:`. `Cmd/Ctrl+Enter` in the textarea triggers Listen.

Failures propagate as HTTP 4xx/5xx with `detail` messages that the frontend surfaces verbatim in the status line.

## Design system (frontend)

The UI commits to a warm-paper editorial aesthetic; changes should stay inside this vocabulary rather than drift toward generic SaaS:

- **Typography**: `Instrument Serif` italic for display (title, textarea body), `Geist` sans for UI, `Geist Mono` for metadata/labels. All loaded from Google Fonts.
- **Palette** (CSS custom properties on `:root`): `--bg` warm ivory, `--paper`/`--paper-hi` surfaces, `--ink` near-black, `--accent` terracotta `#C44A28` reserved for the primary CTA hover, numbered section markers, and the waveform. Do not introduce a second accent.
- **Section pattern**: each form block uses a monospace `block-head` of `[num] [label] [meta]` where `num` is `01`/`02`/`03` in accent color. New blocks should follow this rhythm.
- **Motion**: single `rise` keyframe for staggered entrance, a `wave` keyframe for the 5-bar loading indicator. Both are disabled under `prefers-reduced-motion`.
