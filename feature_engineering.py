"""Build the shared approach-level forecasting feature table (Task 28)."""

from forecasting_features import build_approach_features, build_detector_features


def main():
    print("Starting Feature Engineering (Task 28)...")
    detector_features = build_detector_features("counts.csv")
    detector_features.to_csv("detector_feature_table.csv", index=False)
    features = build_approach_features("counts.csv")
    features.to_csv("approach_feature_table.csv", index=False)
    # Backward-compatible name used by existing project scripts.
    features.to_csv("feature_table.csv", index=False)
    print(
        f"Saved detector_feature_table.csv ({len(detector_features):,} rows) and "
        f"approach_feature_table.csv ({len(features):,} rows, "
        f"{features['approach'].nunique()} approaches)."
    )


if __name__ == "__main__":
    main()
