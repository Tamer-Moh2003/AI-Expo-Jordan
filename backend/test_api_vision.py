import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api


class VisionApiTests(unittest.TestCase):
    def test_health_and_incidents_read_shared_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            health = {
                "ingestion_rate_fps": 8.5,
                "dropped_frames": 2,
                "stream_uptime_seconds": 45.0,
            }
            incidents = [
                {
                    "timestamp": "2026-07-16T09:00:00.000Z",
                    "event_type": "Stalled Vehicle",
                    "approach": "northbound",
                    "confidence": 0.9,
                    "queue_estimate": 1,
                    "snapshot_path": "/media/snapshot.jpg",
                    "clip_path": "/media/clip.mp4",
                }
            ]
            health_path = root / "health.json"
            events_path = root / "events.json"
            health_path.write_text(json.dumps(health), encoding="utf-8")
            events_path.write_text(json.dumps(incidents), encoding="utf-8")
            api.VISION_HEALTH_PATH = str(health_path)
            api.VISION_EVENTS_PATH = str(events_path)

            client = api.app.test_client()
            health_response = client.get("/health")
            incident_response = client.get("/incidents")
            self.assertEqual(health_response.status_code, 200)
            self.assertEqual(incident_response.status_code, 200)
            self.assertEqual(health_response.get_json(), health)
            self.assertEqual(incident_response.get_json(), incidents)


if __name__ == "__main__":
    unittest.main()
