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

## Project layout

```
Speek/
├── main.py             # FastAPI backend (/voices, /generate, /)
├── static/
│   └── index.html      # Single-file frontend (HTML + CSS + JS)
├── requirements.txt    # fastapi, uvicorn, edge-tts
└── CLAUDE.md           # Notes for Claude Code
```

---

## Troubleshooting

- **`pip: command not found` (macOS)** — use `pip3`, or (better) activate the venv first; inside the venv plain `pip` works.
- **`uvicorn: command not found`** — the virtual environment isn't activated. Re-run the activation command for your platform.
- **Voices fail to load / `502` on generate** — edge-tts needs network access to Microsoft's servers. Check your connection, firewall, or VPN.
- **Port 8000 already in use** — run on a different port: `uvicorn main:app --reload --port 8001`.

---

## License

See [LICENSE](LICENSE).
