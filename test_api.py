import unittest

import api


class RecommendationApiTest(unittest.TestCase):
    def setUp(self):
        self.client = api.app.test_client()

    def test_recommendation_matches_contract(self):
        response = self.client.get("/recommendation")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["timestamp"], "2026-07-13T21:45:00Z")
        self.assertEqual(payload["recommended_phase"], 1)
        self.assertEqual(payload["recommended_green_duration_seconds"], 53)
        self.assertEqual(payload["estimated_saving_vehicle_minutes"], 28.87)
        self.assertTrue(payload["advisory_only"])
        self.assertTrue(payload["not_transmitted_to_controller"])


if __name__ == "__main__":
    unittest.main()
