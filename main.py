from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Speek", description="Personal text-to-speech studio.")


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(..., min_length=1)


def _display_name(short_name: str) -> str:
    tail = short_name.split("-")[-1]
    for suffix in ("Neural", "Multilingual"):
        if tail.endswith(suffix):
            tail = tail[: -len(suffix)]
    return tail


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


@app.post("/generate")
async def generate(req: GenerateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    communicate = edge_tts.Communicate(text, req.voice)

    async def audio_stream():
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except edge_tts.exceptions.NoAudioReceived:
            raise HTTPException(status_code=502, detail="No audio returned from edge-tts.")

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="speek.mp3"'},
    )


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
