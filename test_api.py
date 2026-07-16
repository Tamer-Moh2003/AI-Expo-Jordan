import unittest

import api
from signal_advisor import make_recommendation


class SignalAdvisorTest(unittest.TestCase):
    def test_recommendation_is_explainable_and_guarded(self):
        result = make_recommendation(
            {"North_Arar_St": 80, "South_Arar_St": 60, "East_Approach": 30, "West_Approach": 25},
            {"North_Arar_St": 60, "South_Arar_St": 55, "East_Approach": 28, "West_Approach": 25},
            "2026-07-14 17:15:00",
        )
        self.assertTrue(result["advisory_only"])
        self.assertTrue(result["not_transmitted_to_controller"])
        self.assertIn("delay_formula", result)
        self.assertIn("assumptions", result)
        self.assertEqual(sum(result["recommended_green_seconds"].values()) + 12, result["recommended_cycle_length_seconds"])
        self.assertGreaterEqual(result["recommended_cycle_length_seconds"], 60)
        self.assertLessEqual(result["recommended_cycle_length_seconds"], 120)

    def test_api_refreshes_at_demo_time(self):
        response = api.app.test_client().get("/recommendation?at=2026-07-13T12:00:00")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["forecast_horizon_minutes"], 30)
        self.assertTrue(payload["advisory_only"])
        self.assertIn("recommended_green_seconds", payload)
        self.assertEqual(
            payload["recommended_green_duration_seconds"],
            payload["recommended_green_seconds"][str(payload["recommended_phase"])],
        )
        self.assertEqual(
            payload["current_green_duration_seconds"],
            payload["current_green_seconds"][str(payload["recommended_phase"])],
        )
        self.assertEqual(
            payload["estimated_saving_vehicle_minutes"],
            payload["estimated_saving_vehicle_minutes_per_cycle"],
        )

    def test_forecast_has_m3_accuracy_adapter(self):
        response = api.app.test_client().get("/forecast")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["accuracy_chip"]["status"], "AI Outperforming Baseline")
        self.assertIn("ai_forecast_error_1h", payload["accuracy_chip"])
        self.assertIn("naive_baseline_error", payload["accuracy_chip"])


if __name__ == "__main__":
    unittest.main()
