"""Forecast API backed by the same feature pipeline used during training."""

from flask import Flask, jsonify
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd

from forecasting_features import build_approach_features, FEATURE_COLUMNS, HORIZONS

app = Flask(__name__)
RECOMMENDATIONS_PATH = Path("recommendations.csv")
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


def latest_recommendation():
    """Return the highest-value recommendation at the latest available time."""
    recommendations = pd.read_csv(RECOMMENDATIONS_PATH)
    required = {
        "timestamp",
        "recommended_phase",
        "recommended_green_duration",
        "reason",
        "estimated_saving_vehicle_minutes",
    }
    missing = required.difference(recommendations.columns)
    if missing:
        raise ValueError(f"Missing recommendation columns: {', '.join(sorted(missing))}")
    if recommendations.empty:
        raise ValueError("No recommendations are available")

    recommendations["timestamp"] = pd.to_datetime(
        recommendations["timestamp"], errors="coerce", utc=True
    )
    recommendations = recommendations.dropna(subset=["timestamp"])
    if recommendations.empty:
        raise ValueError("No recommendations have a valid timestamp")

    latest = recommendations[
        recommendations["timestamp"] == recommendations["timestamp"].max()
    ]
    best = latest.sort_values(
        "estimated_saving_vehicle_minutes", ascending=False
    ).iloc[0]
    return {
        "timestamp": best["timestamp"].isoformat().replace("+00:00", "Z"),
        "recommended_phase": int(best["recommended_phase"]),
        "recommended_green_duration_seconds": int(
            best["recommended_green_duration"]
        ),
        "reason": str(best["reason"]),
        "estimated_saving_vehicle_minutes": float(
            best["estimated_saving_vehicle_minutes"]
        ),
        "advisory_only": True,
        "not_transmitted_to_controller": True,
    }


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


@app.route("/recommendation", methods=["GET"])
def get_recommendation():
    try:
        return jsonify(latest_recommendation())
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as error:
        return jsonify({"status": "error", "message": str(error)}), 503


if __name__ == "__main__":
    app.run(port=5000, debug=True)
