"""Read M1 vision outputs from the shared Docker volume."""

from __future__ import annotations

import json
from pathlib import Path


EMPTY_HEALTH = {
    "ingestion_rate_fps": 0.0,
    "dropped_frames": 0,
    "stream_uptime_seconds": 0.0,
}


def read_json(path: str | Path, fallback):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback.copy() if isinstance(fallback, dict) else list(fallback)


def read_health(path: str | Path) -> dict:
    payload = read_json(path, EMPTY_HEALTH)
    return {key: payload.get(key, value) for key, value in EMPTY_HEALTH.items()}


def read_incidents(path: str | Path) -> list:
    payload = read_json(path, [])
    return payload if isinstance(payload, list) else []
