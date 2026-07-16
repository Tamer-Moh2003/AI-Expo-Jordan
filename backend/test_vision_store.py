import json
import tempfile
import unittest
from pathlib import Path

from vision_store import EMPTY_HEALTH, read_health, read_incidents


class VisionStoreTests(unittest.TestCase):
    def test_missing_files_return_contract_safe_defaults(self):
        self.assertEqual(read_health("missing.json"), EMPTY_HEALTH)
        self.assertEqual(read_incidents("missing.json"), [])

    def test_shared_files_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            health = {"ingestion_rate_fps": 12.5, "dropped_frames": 1, "stream_uptime_seconds": 30.0}
            incidents = [{"event_type": "Stalled Vehicle"}]
            (root / "health.json").write_text(json.dumps(health), encoding="utf-8")
            (root / "events.json").write_text(json.dumps(incidents), encoding="utf-8")
            self.assertEqual(read_health(root / "health.json"), health)
            self.assertEqual(read_incidents(root / "events.json"), incidents)


if __name__ == "__main__":
    unittest.main()
