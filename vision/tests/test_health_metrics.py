import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import health_metrics
from health_metrics import HealthMonitor


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class HealthMonitorTests(unittest.TestCase):
    def test_contract_fields_and_atomic_write(self):
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            monitor = HealthMonitor(path, window_seconds=5, clock=clock)
            monitor.set_connected(True)
            for _ in range(6):
                monitor.record_frame()
                clock.value += 1
            monitor.record_dropped(2)
            payload = monitor.write()
            self.assertEqual(
                set(payload),
                {"ingestion_rate_fps", "dropped_frames", "stream_uptime_seconds"},
            )
            self.assertEqual(payload["ingestion_rate_fps"], 1.0)
            self.assertEqual(payload["dropped_frames"], 2)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            monitor.set_connected(False)
            disconnected = monitor.snapshot()
            self.assertEqual(disconnected["ingestion_rate_fps"], 0.0)
            self.assertEqual(disconnected["stream_uptime_seconds"], 6.0)

    def test_atomic_write_retries_transient_windows_file_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            monitor = HealthMonitor(path)
            real_replace = health_metrics.os.replace
            attempts = 0

            def transient_lock(source, destination):
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise PermissionError("temporarily locked")
                real_replace(source, destination)

            with patch("health_metrics.os.replace", side_effect=transient_lock), patch(
                "health_metrics.time.sleep"
            ):
                payload = monitor.write()

            self.assertEqual(attempts, 3)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)


if __name__ == "__main__":
    unittest.main()
