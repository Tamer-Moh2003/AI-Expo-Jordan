"""Train leakage-safe, approach-level traffic forecasts for 15/30/60 minutes."""

import json
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")
from forecasting_features import build_approach_features, FEATURE_COLUMNS, HORIZONS
TEST_DAYS = 14


def mape(actual, predicted):
    """MAPE for positive traffic counts (the generator never emits zero)."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return 100 * np.mean(np.abs(actual - predicted) / np.maximum(actual, 1.0))


def main():
    df = build_approach_features()
    grouped = df.groupby("approach", observed=True)["vehicle_count"]
    for label, steps in HORIZONS.items():
        df[f"target_{label}"] = grouped.shift(-steps)
        df[f"baseline_{label}"] = grouped.shift(672 - steps)
    df = df.dropna().reset_index(drop=True)
    split_date = df["timestamp"].max() - pd.Timedelta(days=TEST_DAYS)
    train = df[df["timestamp"] <= split_date].copy()
    test = df[df["timestamp"] > split_date].copy()

    features = FEATURE_COLUMNS

    print(f"Time split: train <= {split_date}, test = final {TEST_DAYS} days")
    results = []

    for label in HORIZONS:
        target = f"target_{label}"
        model = lgb.LGBMRegressor(
            objective="poisson",
            n_estimators=700,
            learning_rate=0.035,
            num_leaves=63,
            min_child_samples=30,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        )
        model.fit(
            train[features], train[target], categorical_feature=["approach"]
        )

        predictions = np.maximum(model.predict(test[features]), 0)
        actual = test[target].to_numpy()
        baseline = test[f"baseline_{label}"].to_numpy()
        model_mape = mape(actual, predictions)
        baseline_mape = mape(actual, baseline)
        model_rmse = mean_squared_error(actual, predictions) ** 0.5
        baseline_rmse = mean_squared_error(actual, baseline) ** 0.5
        residuals = actual - predictions
        residual_lower, residual_upper = np.quantile(residuals, [0.05, 0.95])

        print(f"\nForecast horizon: {label}")
        print(f"  LightGBM MAPE: {model_mape:.2f}%")
        print(f"  Naive MAPE:    {baseline_mape:.2f}%")
        print(f"  Improvement:   {(baseline_mape-model_mape)/baseline_mape*100:.1f}%")
        print(f"  RMSE:          {model_rmse:.2f} (naive: {baseline_rmse:.2f})")
        print(f"  MAE:           {mean_absolute_error(actual, predictions):.2f}")

        model.booster_.save_model(f"model_{label}.txt")
        with open(f"model_{label}_metadata.json", "w", encoding="utf-8") as file:
            json.dump({
                "features": features,
                "split_date": str(split_date),
                "confidence_level": 0.90,
                "residual_quantiles": {
                    "lower": float(residual_lower), "upper": float(residual_upper)
                },
            }, file, indent=2)

        for approach, rows in test.assign(prediction=predictions).groupby("approach", observed=True):
            results.append({
                "horizon": label,
                "approach": str(approach),
                "mape": round(mape(rows[target], rows["prediction"]), 3),
                "baseline_mape": round(mape(rows[target], rows[f"baseline_{label}"]), 3),
                "rmse": round(mean_squared_error(rows[target], rows["prediction"]) ** 0.5, 3),
                "baseline_rmse": round(mean_squared_error(rows[target], rows[f"baseline_{label}"]) ** 0.5, 3),
            })

    pd.DataFrame(results).to_csv("forecast_evaluation.csv", index=False)
    print("\nSaved per-approach results to forecast_evaluation.csv")


if __name__ == "__main__":
    main()
