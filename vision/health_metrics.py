"""Runtime health metrics matching the frozen GET /health API contract."""

from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path


class HealthMonitor:
    def __init__(self, output_path: str | Path, window_seconds: float = 5.0, clock=None):
        self.output_path = Path(output_path)
        self.window_seconds = window_seconds
        self.clock = clock or time.monotonic
        self.started_at = self.clock()
        self.frame_times: deque[float] = deque()
        self.dropped_frames = 0
        self.connected = False
        self.connected_since: float | None = None
        self.connected_total = 0.0
        self.reconnect_attempts = 0

    def set_connected(self, connected: bool) -> None:
        now = self.clock()
        if connected and not self.connected:
            self.connected_since = now
        elif not connected and self.connected and self.connected_since is not None:
            self.connected_total += now - self.connected_since
            self.connected_since = None
        self.connected = connected

    def record_frame(self) -> None:
        now = self.clock()
        self.frame_times.append(now)
        self._trim(now)

    def record_dropped(self, count: int = 1) -> None:
        self.dropped_frames += max(0, int(count))

    def record_reconnect(self) -> None:
        self.reconnect_attempts += 1

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self.frame_times and self.frame_times[0] < cutoff:
            self.frame_times.popleft()

    def snapshot(self) -> dict:
        now = self.clock()
        self._trim(now)
        if len(self.frame_times) >= 2:
            duration = self.frame_times[-1] - self.frame_times[0]
            ingestion_rate = (len(self.frame_times) - 1) / duration if duration > 0 else 0.0
        else:
            ingestion_rate = 0.0
        uptime = self.connected_total
        if self.connected and self.connected_since is not None:
            uptime += now - self.connected_since
        return {
            "ingestion_rate_fps": round(ingestion_rate if self.connected else 0.0, 3),
            "dropped_frames": self.dropped_frames,
            "stream_uptime_seconds": round(uptime, 3),
        }

    def write(self) -> dict:
        payload = self.snapshot()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output_path.with_suffix(self.output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        for attempt in range(5):
            try:
                os.replace(temporary, self.output_path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
        return payload
