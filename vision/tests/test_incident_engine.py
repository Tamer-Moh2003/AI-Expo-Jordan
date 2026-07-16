import copy
import json
import unittest
from pathlib import Path

from incident_engine import analyse, api_events


class IncidentRuleTests(unittest.TestCase):
    def test_all_four_rules_emit(self):
        config = json.loads(Path("day2_config.json").read_text(encoding="utf-8"))
        config.update(
            {
                "stalled_duration_seconds": 2,
                "queue_context_vehicle_count": 999,
                "spillback_vehicle_threshold": 3,
                "spillback_duration_seconds": 2,
                "congestion_window_seconds": 20,
                "congestion_drop_percent": 40,
                "wrong_way_min_displacement_px": 5,
                "event_cooldown_seconds": 999,
            }
        )
        zones = {
            "approaches": {
                "test": {
                    "lanes": [[[0, 0], [100, 0], [100, 100], [0, 100]]],
                    "spillback_zone": [[75, 0], [100, 0], [100, 100], [75, 100]],
                    "expected_direction": [[0, 50], [100, 50]],
                }
            }
        }
        rows = []
        for timestamp in range(31):
            moving_speed = 30.0 if timestamp < 15 else 5.0
            rows.append(self.row(timestamp, 1, 20, 20, 0.0))  # stalled
            rows.append(self.row(timestamp, 2, 60 - timestamp, 50, 10.0))  # wrong way
            rows.append(self.row(timestamp, 3, 40 + timestamp, 40, moving_speed))
            for track_id, y in ((10, 20), (11, 50), (12, 80)):
                rows.append(self.row(timestamp, track_id, 90, y, 0.0))

        events, summaries = analyse(copy.deepcopy(rows), zones, config)
        event_types = {event["type"] for event in events}
        self.assertIn("stalled_vehicle", event_types)
        self.assertIn("queue_spillback", event_types)
        self.assertIn("sudden_congestion", event_types)
        self.assertIn("wrong_way_or_abnormal_trajectory", event_types)
        self.assertTrue(summaries)

        contracted = api_events(events, "2026-07-15T12:00:00Z")
        required = {
            "timestamp", "event_type", "approach", "confidence",
            "queue_estimate", "snapshot_path", "clip_path",
        }
        self.assertTrue(all(set(event) == required for event in contracted))

    @staticmethod
    def row(timestamp, track_id, x, y, speed):
        return {
            "frame": timestamp + 1,
            "timestamp": float(timestamp),
            "track_id": track_id,
            "class": "car",
            "bbox_x1": x - 2,
            "bbox_y1": y - 2,
            "bbox_x2": x + 2,
            "bbox_y2": y + 2,
            "centroid_x": float(x),
            "centroid_y": float(y),
            "approach": "test",
            "speed_px_s": speed,
            "speed_valid": True,
            "vx_px_s": 0.0,
            "vy_px_s": 0.0,
        }


if __name__ == "__main__":
    unittest.main()
