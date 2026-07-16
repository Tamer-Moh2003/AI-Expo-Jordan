"""Evaluate the same-weekday-last-week baseline on the final 14 days."""

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error


TEST_DAYS = 14
HORIZONS = {"15m": 1, "30m": 2, "60m": 4}


def mape(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return 100 * np.mean(np.abs(actual - predicted) / np.maximum(actual, 1.0))


def load_approach_counts():
    counts_path = Path("counts.csv") if Path("counts.csv").exists() else Path("feature_table.csv")
    counts = pd.read_csv(
        counts_path, usecols=["timestamp", "detector_id", "vehicle_count"]
    )
    detectors = pd.read_csv("detectors.csv", usecols=["id", "approach"])
    counts["timestamp"] = pd.to_datetime(counts["timestamp"])
    counts = counts.merge(
        detectors, left_on="detector_id", right_on="id", validate="many_to_one"
    )
    return (
        counts.groupby(["approach", "timestamp"], as_index=False)["vehicle_count"]
        .sum()
        .sort_values(["approach", "timestamp"])
        .reset_index(drop=True)
    )


def main():
    df = load_approach_counts()
    grouped = df.groupby("approach")["vehicle_count"]
    split_date = df["timestamp"].max() - pd.Timedelta(days=TEST_DAYS)
    rows = []

    print("Naive baseline: target count = the same approach/slot one week earlier")
    print(f"Evaluation period: final {TEST_DAYS} days after {split_date}\n")

    for label, steps in HORIZONS.items():
        # At forecast time t, predict t+h using the observed value at t+h-7 days.
        df["actual"] = grouped.shift(-steps)
        df["prediction"] = grouped.shift(672 - steps)
        test = df[(df["timestamp"] > split_date)].dropna(
            subset=["actual", "prediction"]
        )

        overall = mape(test["actual"], test["prediction"])
        overall_rmse = mean_squared_error(test["actual"], test["prediction"]) ** 0.5
        print(f"{label:>3} horizon: MAPE {overall:.2f}% | RMSE {overall_rmse:.2f}")

        for approach, part in test.groupby("approach"):
            rows.append({
                "horizon": label,
                "approach": approach,
                "mape": round(mape(part["actual"], part["prediction"]), 3),
                "rmse": round(mean_squared_error(part["actual"], part["prediction"]) ** 0.5, 3),
            })

    pd.DataFrame(rows).to_csv("baseline_evaluation.csv", index=False)
    print("\nSaved per-approach results to baseline_evaluation.csv")


if __name__ == "__main__":
    main()
