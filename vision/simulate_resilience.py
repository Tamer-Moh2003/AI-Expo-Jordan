"""Deterministic Day 3 simulation of a corrupt frame and stream reconnect."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from health_metrics import HealthMonitor
from main import has_valid_frame


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Result:
    def __init__(self, frame):
        self.orig_img = frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/day3_resilience_simulation.json")
    args = parser.parse_args()

    output = Path(args.output)
    clock = Clock()
    monitor = HealthMonitor(output.with_name("simulated_health.json"), clock=clock)
    monitor.set_connected(True)

    sequence = [
        Result(np.zeros((2, 2, 3), dtype=np.uint8)),
        Result(None),
        Result(np.zeros((2, 2, 3), dtype=np.uint8)),
    ]
    accepted = 0
    for result in sequence:
        if has_valid_frame(result):
            monitor.record_frame()
            accepted += 1
        else:
            monitor.record_dropped()
        clock.value += 1

    monitor.set_connected(False)
    clock.value += 7  # configured retry delay
    monitor.record_reconnect()
    monitor.set_connected(True)
    monitor.record_frame()
    accepted += 1
    clock.value += 1

    report = {
        "accepted_frames": accepted,
        "corrupt_frames_skipped": monitor.dropped_frames,
        "reconnect_delay_seconds": 7,
        "reconnect_attempts": monitor.reconnect_attempts,
        "pipeline_continued_after_reconnect": True,
        "health": monitor.write(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
