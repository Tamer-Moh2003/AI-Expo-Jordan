import unittest
from pathlib import Path

import pandas as pd

from forecasting_features import FEATURE_COLUMNS, HORIZONS, build_approach_features


class ForecastingDay2Test(unittest.TestCase):
    def test_required_features_and_three_horizons(self):
        required = {
            "lag_1", "lag_2", "lag_3", "lag_4", "lag_96",
            "rolling_mean_4", "rolling_mean_16", "quarter_hour",
            "day_of_week", "is_weekend", "is_holiday", "approach",
        }
        self.assertTrue(required.issubset(FEATURE_COLUMNS))
        self.assertEqual(HORIZONS, {"15m": 1, "30m": 2, "60m": 4})

    def test_feature_table_has_no_missing_model_inputs(self):
        features = build_approach_features()
        self.assertFalse(features.empty)
        self.assertFalse(features[FEATURE_COLUMNS].isna().any().any())
        self.assertEqual(features["approach"].nunique(), 4)

    def test_models_beat_baseline_per_horizon_and_approach(self):
        results = pd.read_csv("forecast_evaluation.csv")
        self.assertEqual(len(results), 12)
        self.assertTrue((results["mape"] < results["baseline_mape"]).all())
        self.assertTrue((results["rmse"] < results["baseline_rmse"]).all())

    def test_reproducible_pipeline_references_existing_scripts(self):
        pipeline = Path("run_forecasting_pipeline.py").read_text(encoding="utf-8")
        for script in (
            "synthetic_generator.py", "feature_engineering.py",
            "baseline_model.py", "train_model.py", "feature_importance.py",
        ):
            self.assertIn(script, pipeline)
            self.assertTrue(Path(script).exists())


if __name__ == "__main__":
    unittest.main()
