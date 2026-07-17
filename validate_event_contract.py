"""Validate emitted incident events against the frozen API contract example."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--events", required=True)
    args = parser.parse_args()

    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    example = contract["endpoints"]["GET /incidents"][0]
    expected_keys = set(example)
    events = json.loads(Path(args.events).read_text(encoding="utf-8"))

    errors = []
    for index, event in enumerate(events):
        if set(event) != expected_keys:
            errors.append(
                f"event {index}: expected keys {sorted(expected_keys)}, got {sorted(event)}"
            )
            continue
        try:
            datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        except (TypeError, ValueError):
            errors.append(f"event {index}: timestamp is not ISO UTC")
        if not isinstance(event["confidence"], (int, float)) or not 0 <= event["confidence"] <= 1:
            errors.append(f"event {index}: confidence must be between 0 and 1")
        if not isinstance(event["queue_estimate"], int) or event["queue_estimate"] < 0:
            errors.append(f"event {index}: queue_estimate must be a non-negative integer")
        for field in ("event_type", "approach", "snapshot_path", "clip_path"):
            if not isinstance(event[field], str):
                errors.append(f"event {index}: {field} must be a string")

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {len(events)} event(s) match GET /incidents")


if __name__ == "__main__":
    main()
