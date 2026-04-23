# Character models

Drop RVC v2 `.pth` files here, one folder per character. Folder names must match the keys in `../characters.json`.

```
models/
├── peter/
│   ├── peter.pth       ← required
│   └── peter.index     ← optional but recommended (better timbre match)
├── stewie/
│   ├── stewie.pth
│   └── stewie.index
└── …
```

Filenames inside a folder don't matter — Speek picks the first `.pth` and the first `.index` it finds.

## Where to get the models

- <https://voice-models.com> — search "Peter Griffin", "Stewie Griffin", etc.
- <https://weights.gg> — same deal, community uploads
- <https://huggingface.co> — search `family guy rvc`

Prefer models trained **≥ 200 epochs** with **rmvpe** pitch extraction for best quality.

## Per-character tuning

`../characters.json` controls two things per character:

- **`base_voice`** — the edge-tts voice used to generate the source audio before RVC reshapes it. Male character → pick a male voice; British character → pick a British voice.
- **`pitch`** — semitones to shift. Positive = higher. Stewie wants +5 or +6. Herbert wants −2. Leave at 0 if unsure.

No restart needed after editing characters.json — the server re-reads it on each request.
