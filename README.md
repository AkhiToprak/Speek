# Speek

A personal text-to-speech studio. Type, pick a voice, press **Listen** or **Export MP3**. Runs locally, no account, no cloud bill.

Powered by [`edge-tts`](https://github.com/rany2/edge-tts) (Microsoft Edge's online voices), [FastAPI](https://fastapi.tiangolo.com/), and a single-file vanilla HTML/CSS/JS frontend.

---

## Features

- 400+ neural voices across dozens of languages, grouped by language in the picker
- Stream playback in the browser (`Listen`)
- Download as MP3 (`Export MP3`) with a filename derived from your text
- `Cmd/Ctrl + Enter` shortcut to generate
- Warm editorial UI, reduced-motion aware, keyboard accessible

---

## Requirements

- **Python 3.9 or newer**
- Internet connection (edge-tts talks to Microsoft's voice service)

Check your Python version:

```bash
python3 --version    # macOS / Linux
py --version         # Windows
```

---

## Setup

Clone or download the project, then open a terminal in the project folder.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks the activation script, run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Windows (Command Prompt)

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

## Run

With the virtual environment activated:

```bash
uvicorn main:app --reload
```

Open **<http://127.0.0.1:8000>** in your browser.

To stop the server: `Ctrl + C` in the terminal.

### Later sessions

You only install dependencies once. Next time, just activate the venv and run uvicorn:

| Platform | Activate | Run |
| --- | --- | --- |
| macOS / Linux | `source .venv/bin/activate` | `uvicorn main:app --reload` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` | `uvicorn main:app --reload` |
| Windows CMD | `.venv\Scripts\activate.bat` | `uvicorn main:app --reload` |

---

## Using the app

1. **Write** — type or paste text into the script box (up to 5,000 characters).
2. **Pick a voice** — voices are grouped by language; `en-US-AriaNeural` is the default.
3. **Listen** — generates the audio and plays it inline.
4. **Export MP3** — generates the audio and downloads it as an `.mp3`.

Tip: press **`Cmd + Enter`** (macOS) or **`Ctrl + Enter`** (Windows) inside the script box to trigger Listen.

---

## Character voices (optional — Family Guy via RVC)

Speek can post-process edge-tts audio through an **RVC** voice model to imitate a specific character. The pipeline is: `edge-tts → ffmpeg → RVC → ffmpeg → MP3`. No rewrites to the UI — characters show up as a `Family Guy · RVC` group at the top of the voice dropdown.

### 1. Install the RVC extras

```bash
# with the venv active
pip install -r requirements-rvc.txt
```

This adds `rvc-python` and its PyTorch stack (~2 GB). First run also downloads HuBERT + RMVPE helper models (~350 MB).

### 2. Install ffmpeg

| Platform | Command |
| --- | --- |
| macOS | `brew install ffmpeg` |
| Windows | `winget install ffmpeg` |
| Linux | `sudo apt install ffmpeg` |

### 3. Drop the `.pth` files in

Speek ships with a `characters.json` listing 11 Family Guy characters (Peter, Stewie, Brian, Lois, Chris, Meg, Quagmire, Joe, Cleveland, Herbert, Consuela). You need to supply the weights yourself:

```
models/
├── peter/
│   ├── peter.pth       ← required
│   └── peter.index     ← optional, improves quality
├── stewie/
│   └── stewie.pth
└── …
```

Folder names **must match** the keys in `characters.json`. Filenames inside the folder don't matter — the first `.pth` wins.

Model sources:

- [voice-models.com](https://voice-models.com) — search "Peter Griffin", "Stewie Griffin", etc.
- [weights.gg](https://weights.gg)
- [Hugging Face](https://huggingface.co) — search `family guy rvc`

Pick ones trained **≥ 200 epochs** with **rmvpe** for best results.

### 4. Pick the character

Restart isn't required — just refresh the page. The character appears in the voice dropdown under `Family Guy · RVC`. Generation takes ~20–60 s on CPU, much faster on an NVIDIA GPU or Apple Silicon (the backend auto-detects; override with `SPEEK_RVC_DEVICE=cpu|mps|cuda:0`).

### Tuning per character

`characters.json` controls two knobs per character:

- `base_voice` — the edge-tts voice used as the RVC source. Male character → male source; British character → British source.
- `pitch` — semitones of shift. Stewie wants ~+6. Herbert wants ~−2.

Edit the file and reload — no restart.

> Note: character voices and actors' likenesses are protected. Fine for personal tinkering; don't publish content using them.

---

## Project layout

```
Speek/
├── main.py                 # FastAPI backend (edge-tts + optional RVC pipeline)
├── static/
│   └── index.html          # Single-file frontend (HTML + CSS + JS)
├── characters.json         # Per-character config (base voice, pitch)
├── models/                 # RVC weights go here (user-supplied)
├── requirements.txt        # fastapi, uvicorn, edge-tts
├── requirements-rvc.txt    # + rvc-python for character voices
└── CLAUDE.md               # Notes for Claude Code
```

---

## Troubleshooting

- **`pip: command not found` (macOS)** — use `pip3`, or (better) activate the venv first; inside the venv plain `pip` works.
- **`uvicorn: command not found`** — the virtual environment isn't activated. Re-run the activation command for your platform.
- **Voices fail to load / `502` on generate** — edge-tts needs network access to Microsoft's servers. Check your connection, firewall, or VPN.
- **Port 8000 already in use** — run on a different port: `uvicorn main:app --reload --port 8001`.
- **Character selection returns 500 "rvc-python is not installed"** — run `pip install -r requirements-rvc.txt` inside the venv.
- **Character selection returns 500 "ffmpeg not found"** — install ffmpeg (see the character voices section).
- **RVC is painfully slow** — you're on CPU. Set `SPEEK_RVC_DEVICE=mps` on Apple Silicon or `cuda:0` on NVIDIA before starting uvicorn.
- **Character quality is off** — try a model trained more epochs, or adjust `pitch` in `characters.json` (Stewie: +5 to +7, Herbert: −2, etc.).

---

## License

See [LICENSE](LICENSE).
