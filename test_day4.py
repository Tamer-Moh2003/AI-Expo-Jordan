import unittest

import api
from validate_recommendations import SCENARIOS, validate_payload


class Day4RecommendationValidationTest(unittest.TestCase):
    def test_recommendations_are_sane_across_demo_scenarios(self):
        for scenario, timestamp in SCENARIOS.items():
            with self.subTest(scenario=scenario):
                payload = api.live_recommendation(timestamp)
                self.assertEqual(validate_payload(payload), [])


if __name__ == "__main__":
    unittest.main()
