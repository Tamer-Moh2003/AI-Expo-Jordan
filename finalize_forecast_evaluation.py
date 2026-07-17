"""Create the final Day 4 forecast evaluation summary from per-approach results."""

import pandas as pd


def main():
    results = pd.read_csv("forecast_evaluation.csv")
    required = {"horizon", "approach", "mape", "baseline_mape", "rmse", "baseline_rmse"}
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing evaluation columns: {', '.join(sorted(missing))}")
    summary = (
        results.groupby("horizon", as_index=False, sort=False)[
            ["mape", "baseline_mape", "rmse", "baseline_rmse"]
        ]
        .mean()
        .rename(columns={
            "mape": "lightgbm_mape",
            "rmse": "lightgbm_rmse",
        })
    )
    summary["mape_improvement_percent"] = (
        100 * (summary["baseline_mape"] - summary["lightgbm_mape"])
        / summary["baseline_mape"]
    )
    summary["rmse_improvement_percent"] = (
        100 * (summary["baseline_rmse"] - summary["lightgbm_rmse"])
        / summary["baseline_rmse"]
    )
    numeric = summary.select_dtypes("number").columns
    summary[numeric] = summary[numeric].round(3)
    summary.to_csv("forecast_evaluation_summary.csv", index=False)
    print(summary.to_string(index=False))
    if not (
        (summary["lightgbm_mape"] < summary["baseline_mape"]).all()
        and (summary["lightgbm_rmse"] < summary["baseline_rmse"]).all()
    ):
        raise SystemExit("LightGBM did not beat the baseline at every horizon")


if __name__ == "__main__":
    main()
