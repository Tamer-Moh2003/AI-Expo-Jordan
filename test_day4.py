import unittest
import api

class Day4RecommendationValidationTest(unittest.TestCase):
    def test_recommendations_are_sane(self):
        """Task 64: Sanity check the recommendation to ensure no absurd values."""
        # Get the latest recommendation based on the current demo time
        payload = api.live_recommendation()
        
        # Check that the cycle length is clamped within safe bounds (60 to 120 seconds)
        self.assertGreaterEqual(payload["recommended_cycle_length_seconds"], 60)
        self.assertLessEqual(payload["recommended_cycle_length_seconds"], 120)
        
        # Check that green times are not negative
        for phase, green_time in payload["recommended_green_seconds"].items():
            self.assertGreaterEqual(green_time, 15, f"Phase {phase} green time is too short!")
            
        # Ensure hard guard rails are present
        self.assertTrue(payload["advisory_only"])
        self.assertTrue(payload["not_transmitted_to_controller"])

if __name__ == "__main__":
    unittest.main()