"""Shared, leakage-safe approach feature construction for training and serving."""

from pathlib import Path
import pandas as pd


HORIZONS = {"15m": 1, "30m": 2, "60m": 4}
FEATURE_COLUMNS = [
    "approach", "vehicle_count", "lag_1", "lag_2", "lag_3", "lag_4",
    "lag_96", "lag_192", "lag_288", "lag_672", "lag_671", "lag_673",
    "lag_1344", "rolling_mean_4", "rolling_mean_8", "rolling_mean_16",
    "rolling_mean_96", "quarter_hour", "day_of_week", "is_weekend",
    "is_holiday",
]


def build_detector_features(counts_file="counts.csv"):
    """Task-28 detector table, retaining both detector and approach identifiers."""
    counts = pd.read_csv(counts_file)
    detectors = pd.read_csv("detectors.csv", usecols=["id", "approach"])
    counts["timestamp"] = pd.to_datetime(counts["timestamp"])
    df = counts.merge(detectors, left_on="detector_id", right_on="id", validate="many_to_one")
    df = df.drop(columns="id").sort_values(["detector_id", "timestamp"]).reset_index(drop=True)
    grouped = df.groupby("detector_id")["vehicle_count"]
    for lag in (1, 2, 3, 4, 96, 192, 288, 672, 1344):
        df[f"lag_{lag}"] = grouped.shift(lag)
    for window in (4, 16):
        df[f"rolling_mean_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window).mean()
        )
    df["quarter_hour"] = df["timestamp"].dt.hour * 4 + df["timestamp"].dt.minute // 15
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([4, 5]).astype("int8")
    df["is_holiday"] = 0
    return df.dropna().reset_index(drop=True)


def build_approach_features(counts_file="counts.csv"):
    path = Path(counts_file)
    if not path.exists():
        path = Path("feature_table.csv")
    counts = pd.read_csv(path, usecols=["timestamp", "detector_id", "vehicle_count"])
    detectors = pd.read_csv("detectors.csv", usecols=["id", "approach"])
    counts["timestamp"] = pd.to_datetime(counts["timestamp"])
    counts = counts.merge(detectors, left_on="detector_id", right_on="id", validate="many_to_one")
    df = (
        counts.groupby(["approach", "timestamp"], as_index=False)["vehicle_count"]
        .sum().sort_values(["approach", "timestamp"]).reset_index(drop=True)
    )
    grouped = df.groupby("approach")["vehicle_count"]
    for lag in (1, 2, 3, 4, 96, 192, 288, 672, 671, 673, 1344):
        df[f"lag_{lag}"] = grouped.shift(lag)
    for window in (4, 8, 16, 96):
        df[f"rolling_mean_{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window).mean()
        )
    df["quarter_hour"] = df["timestamp"].dt.hour * 4 + df["timestamp"].dt.minute // 15
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([4, 5]).astype("int8")
    # Synthetic data currently contains no labelled public holidays. Keep the
    # required feature explicit so real GAM data can populate it later without
    # changing the training/serving contract.
    df["is_holiday"] = 0
    df["approach"] = df["approach"].astype("category")
    return df.dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
