"""Validate emitted health metrics against the frozen GET /health contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--health", required=True)
    args = parser.parse_args()

    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    example = contract["endpoints"]["GET /health"]
    payload = json.loads(Path(args.health).read_text(encoding="utf-8"))
    if set(payload) != set(example):
        raise SystemExit(
            f"Expected keys {sorted(example)}, got {sorted(payload)}"
        )
    if not isinstance(payload["ingestion_rate_fps"], (int, float)) or payload["ingestion_rate_fps"] < 0:
        raise SystemExit("ingestion_rate_fps must be a non-negative number")
    if not isinstance(payload["dropped_frames"], int) or payload["dropped_frames"] < 0:
        raise SystemExit("dropped_frames must be a non-negative integer")
    if not isinstance(payload["stream_uptime_seconds"], (int, float)) or payload["stream_uptime_seconds"] < 0:
        raise SystemExit("stream_uptime_seconds must be a non-negative number")
    print("PASS: health metrics match GET /health")


if __name__ == "__main__":
    main()
