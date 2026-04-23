"""Speek — personal TTS studio with optional RVC character voices.

edge-tts handles the base synthesis. If rvc-python is installed and a `.pth`
is present under `models/<id>/`, the `/generate` endpoint can post-process
that audio through an RVC model to imitate a specific character. The pipeline
is: edge-tts MP3 -> ffmpeg WAV -> RVC -> ffmpeg MP3.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import Lock
from typing import Optional

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------- Paths ----------
ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
MODELS_DIR = ROOT / "models"
CHARACTERS_JSON = ROOT / "characters.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)s  %(message)s")
logger = logging.getLogger("speek")

app = FastAPI(
    title="Speek",
    description="Personal text-to-speech studio with optional RVC characters.",
)


# ---------- Request schema ----------
class GenerateRequest(BaseModel):
    # `voice` is either an edge-tts ShortName (e.g. "en-US-AriaNeural")
    # or "rvc:<character_id>" (e.g. "rvc:peter").
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(..., min_length=1)


# ---------- edge-tts helpers ----------
def _display_name(short_name: str) -> str:
    tail = short_name.split("-")[-1]
    for suffix in ("Neural", "Multilingual"):
        if tail.endswith(suffix):
            tail = tail[: -len(suffix)]
    return tail


# ---------- Characters / RVC ----------
_rvc_instance = None
_rvc_current_pth: Optional[str] = None
_rvc_lock = Lock()


def _load_characters_config() -> dict:
    if not CHARACTERS_JSON.exists():
        return {}
    try:
        return json.loads(CHARACTERS_JSON.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse characters.json")
        return {}


def _find_file(character_id: str, suffix: str) -> Optional[Path]:
    folder = MODELS_DIR / character_id
    if not folder.is_dir():
        return None
    matches = sorted(folder.glob(f"*{suffix}"))
    return matches[0] if matches else None


def _available_characters() -> list[dict]:
    cfg = _load_characters_config()
    out: list[dict] = []
    for cid, meta in cfg.items():
        pth = _find_file(cid, ".pth")
        if not pth:
            continue
        out.append(
            {
                "id": cid,
                "name": meta.get("name", cid.title()),
                "base_voice": meta.get("base_voice", "en-US-GuyNeural"),
                "pitch": int(meta.get("pitch", 0)),
                "note": meta.get("note", ""),
            }
        )
    out.sort(key=lambda c: c["name"])
    return out


def _rvc_importable() -> bool:
    try:
        import rvc_python.infer  # noqa: F401
    except Exception:
        return False
    return True


def _detect_device() -> str:
    forced = os.environ.get("SPEEK_RVC_DEVICE")
    if forced:
        return forced
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda:0"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _get_rvc():
    """Lazily construct a single RVCInference. Importing rvc-python pulls in
    torch, so we pay that cost only when a character is actually requested."""
    global _rvc_instance
    if _rvc_instance is not None:
        return _rvc_instance
    try:
        from rvc_python.infer import RVCInference
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "rvc-python is not installed. Run `pip install -r "
                "requirements-rvc.txt` to enable character voices. "
                f"Import error: {e!r}"
            ),
        )
    device = _detect_device()
    logger.info("Initializing RVCInference on device=%s", device)
    _rvc_instance = RVCInference(device=device)
    return _rvc_instance


def _load_rvc_for(character_id: str, pitch: int):
    global _rvc_current_pth
    pth = _find_file(character_id, ".pth")
    if not pth:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No .pth found for '{character_id}'. "
                f"Drop a RVC .pth (and optional .index) into models/{character_id}/."
            ),
        )

    rvc = _get_rvc()

    if _rvc_current_pth != str(pth):
        logger.info("Loading RVC model: %s", pth)
        rvc.load_model(str(pth))
        _rvc_current_pth = str(pth)

    idx = _find_file(character_id, ".index")
    params = {
        "f0method": "rmvpe",
        "f0up_key": pitch,
        "index_rate": 0.75 if idx else 0.0,
        "filter_radius": 3,
        "rms_mix_rate": 0.25,
        "protect": 0.33,
    }
    # rvc-python exposes a couple of optional setters; be permissive.
    if idx and hasattr(rvc, "set_index"):
        try:
            rvc.set_index(str(idx))
        except Exception:
            logger.exception("set_index failed (continuing without index)")
    if hasattr(rvc, "set_params"):
        try:
            rvc.set_params(**params)
        except TypeError:
            # Older rvc-python accepts fewer keys
            minimal = {"f0method": params["f0method"], "f0up_key": params["f0up_key"]}
            try:
                rvc.set_params(**minimal)
            except Exception:
                logger.exception("set_params failed (continuing with defaults)")
        except Exception:
            logger.exception("set_params failed (continuing with defaults)")
    return rvc


# ---------- ffmpeg ----------
def _ffmpeg_bin() -> str:
    env = os.environ.get("FFMPEG")
    if env:
        return env
    which = shutil.which("ffmpeg")
    if which:
        return which
    raise HTTPException(
        status_code=500,
        detail=(
            "ffmpeg not found. Install it first: "
            "macOS `brew install ffmpeg`, Windows `winget install ffmpeg`."
        ),
    )


def _ffmpeg_run(*args: str) -> None:
    try:
        subprocess.run(
            [_ffmpeg_bin(), "-y", "-loglevel", "error", *args],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ffmpeg failed: {e}")


# ---------- Generation ----------
async def _edge_tts_to_file(text: str, voice: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    try:
        await communicate.save(str(out_path))
    except edge_tts.exceptions.NoAudioReceived as exc:
        raise HTTPException(status_code=502, detail="No audio returned from edge-tts.") from exc


async def _generate_character_mp3(text: str, character_id: str) -> Path:
    """Returns a path to a finished MP3 under a fresh tempdir; caller cleans up."""
    chars = {c["id"]: c for c in _available_characters()}
    meta = chars.get(character_id)
    if not meta:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Character '{character_id}' is not installed. "
                f"Drop models/{character_id}/{character_id}.pth and ensure "
                "characters.json has an entry for it."
            ),
        )

    tmpdir = Path(tempfile.mkdtemp(prefix="speek-"))
    mp3_src = tmpdir / "src.mp3"
    wav_src = tmpdir / "src.wav"
    wav_out = tmpdir / "out.wav"
    mp3_out = tmpdir / "out.mp3"

    # 1. edge-tts -> mp3
    await _edge_tts_to_file(text, meta["base_voice"], mp3_src)

    # 2. mp3 -> wav (44.1k mono, RVC-friendly)
    _ffmpeg_run("-i", str(mp3_src), "-ar", "44100", "-ac", "1", str(wav_src))

    # 3. RVC (serialized — rvc-python holds single-model state)
    with _rvc_lock:
        rvc = _load_rvc_for(character_id, meta["pitch"])
        try:
            rvc.infer_file(str(wav_src), str(wav_out))
        except Exception as e:
            logger.exception("RVC inference failed")
            raise HTTPException(status_code=500, detail=f"RVC inference failed: {e}")

    # 4. wav -> mp3
    _ffmpeg_run("-i", str(wav_out), "-c:a", "libmp3lame", "-b:a", "160k", str(mp3_out))

    return mp3_out


# ---------- Endpoints ----------
@app.get("/voices")
async def list_voices():
    raw = await edge_tts.list_voices()
    voices = [
        {
            "id": v["ShortName"],
            "name": _display_name(v["ShortName"]),
            "locale": v["Locale"],
            "gender": v.get("Gender", ""),
        }
        for v in raw
    ]
    voices.sort(key=lambda v: (v["locale"], v["name"]))
    return voices


@app.get("/characters")
async def list_characters():
    """Characters with a .pth present under models/<id>/. The full catalogue
    (including not-yet-installed ones) lives in characters.json so the user
    knows what folders to drop files into."""
    return {
        "rvc_available": _rvc_importable(),
        "characters": _available_characters(),
        "catalogue": _load_characters_config(),
    }


@app.post("/generate")
async def generate(req: GenerateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    # -------- RVC character path --------
    if req.voice.startswith("rvc:"):
        character_id = req.voice[len("rvc:") :]
        mp3_path = await _generate_character_mp3(text, character_id)

        def iter_mp3():
            try:
                with open(mp3_path, "rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        yield chunk
            finally:
                try:
                    tmp = mp3_path.parent
                    mp3_path.unlink(missing_ok=True)
                    for leftover in tmp.iterdir():
                        try:
                            leftover.unlink()
                        except Exception:
                            pass
                    tmp.rmdir()
                except Exception:
                    pass

        return StreamingResponse(
            iter_mp3(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'inline; filename="speek.mp3"'},
        )

    # -------- edge-tts streaming path --------
    communicate = edge_tts.Communicate(text, req.voice)

    async def audio_stream():
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except edge_tts.exceptions.NoAudioReceived as exc:
            raise HTTPException(status_code=502, detail="No audio returned from edge-tts.") from exc

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="speek.mp3"'},
    )


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
