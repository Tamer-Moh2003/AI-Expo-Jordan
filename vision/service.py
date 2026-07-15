"""Container entrypoint that publishes M1 outputs to the shared stack volume."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from health_metrics import HealthMonitor


SHARED_DIR = Path(os.environ.get("VISION_SHARED_DIR", "/app/data/vision"))
SOURCE = os.environ.get("VISION_SOURCE", "").strip()


def initialise_shared_outputs() -> None:
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    events_path = SHARED_DIR / "events.json"
    if not events_path.exists():
        sample = Path("sample_outputs/day2_dataset1/events.json")
        if sample.exists():
            shutil.copyfile(sample, events_path)
        else:
            events_path.write_text("[]", encoding="utf-8")


def idle_health_service() -> None:
    monitor = HealthMonitor(SHARED_DIR / "health.json")
    monitor.set_connected(False)
    while True:
        monitor.write()
        time.sleep(1)


def run_tracker() -> int:
    command = [
        sys.executable,
        "main.py",
        SOURCE,
        "--output-dir", str(SHARED_DIR),
        "--health-output", str(SHARED_DIR / "health.json"),
        "--reconnect-delay", os.environ.get("VISION_RECONNECT_DELAY", "7"),
        "--imgsz", os.environ.get("VISION_IMAGE_SIZE", "320"),
    ]
    return subprocess.call(command)


if __name__ == "__main__":
    initialise_shared_outputs()
    if SOURCE:
        raise SystemExit(run_tracker())
    idle_health_service()
