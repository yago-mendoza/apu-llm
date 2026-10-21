"""Settings: defaults, overridden by ~/.apu.json, overridden by APU_* environment variables."""

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".apu.json"

DEFAULTS = {
    "host": "http://127.0.0.1:11434",
    "model": "qwen3.6:35b-a3b",
    # Ollama sizes the context from free GPU memory; on a 64 GB APU that is 262144 tokens,
    # whose KV cache alone takes several GB. 16k covers a long file or a few short ones.
    "ctx": 16384,
    "think": False,
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    for key in DEFAULTS:
        env = os.environ.get(f"APU_{key.upper()}")
        if env is not None:
            cfg[key] = _coerce(env, DEFAULTS[key])
    return cfg


def save(changes: dict) -> None:
    current = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    current.update(changes)
    CONFIG_PATH.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


def _coerce(value: str, like):
    if isinstance(like, bool):
        return value.lower() in ("1", "true", "yes", "on")
    if isinstance(like, int):
        return int(value)
    return value
