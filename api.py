"""Forecast API backed by the same feature pipeline used during training."""

from flask import Flask, jsonify
import json
import lightgbm as lgb
import numpy as np
import pandas as pd

from forecasting_features import build_approach_features, FEATURE_COLUMNS, HORIZONS

app = Flask(__name__)
MODELS = {h: lgb.Booster(model_file=f"model_{h}.txt") for h in HORIZONS}
METADATA = {}
for horizon in HORIZONS:
    with open(f"model_{horizon}_metadata.json", encoding="utf-8") as file:
        METADATA[horizon] = json.load(file)


def accuracy_summary():
    try:
        results = pd.read_csv("forecast_evaluation.csv")
        return {
            h: {
                "ai_mape": round(part["mape"].mean(), 2),
                "baseline_mape": round(part["baseline_mape"].mean(), 2),
            }
            for h, part in results.groupby("horizon")
        }
    except FileNotFoundError:
        return {}


@app.route("/forecast", methods=["GET"])
def get_forecast():
    features = build_approach_features()
    latest = features.groupby("approach", observed=True).tail(1).copy()
    accuracy = accuracy_summary()
    forecasts = []

    for horizon, steps in HORIZONS.items():
        predictions = np.maximum(MODELS[horizon].predict(latest[FEATURE_COLUMNS]), 0)
        residuals = METADATA[horizon]["residual_quantiles"]
        for (_, row), prediction in zip(latest.iterrows(), predictions):
            lower = max(0, int(round(prediction + residuals["lower"])))
            upper = max(lower, int(round(prediction + residuals["upper"])))
            prediction = int(round(prediction))
            forecasts.append({
                "timestamp": (row["timestamp"] + pd.Timedelta(minutes=15 * steps)).strftime("%Y-%m-%d %H:%M:%S"),
                "horizon": horizon,
                "approach": str(row["approach"]),
                "observed_count": int(row["vehicle_count"]),
                "predicted_count": prediction,
                "lower": lower,
                "upper": upper,
                "confidence_level": 0.90,
            })

    return jsonify({"status": "success", "accuracy": accuracy, "forecasts": forecasts})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
