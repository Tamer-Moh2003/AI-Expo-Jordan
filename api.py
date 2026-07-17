from functools import lru_cache
import json
import os
from pathlib import Path
import sys

from flask import Flask, jsonify, request
import numpy as np
import pandas as pd

from forecasting_features import build_approach_features, FEATURE_COLUMNS, HORIZONS
from signal_advisor import make_recommendation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from vision_store import read_health, read_incidents

app = Flask(__name__)
VISION_HEALTH_PATH = os.environ.get("VISION_HEALTH_PATH", "/app/data/vision/health.json")
VISION_EVENTS_PATH = os.environ.get("VISION_EVENTS_PATH", "/app/data/vision/events.json")

@lru_cache(maxsize=1)
def forecast_dependencies():
    import lightgbm as lgb

    models = {
        horizon: lgb.Booster(model_file=f"model_{horizon}.txt")
        for horizon in HORIZONS
    }
    metadata = {}
    for horizon in HORIZONS:
        with open(f"model_{horizon}_metadata.json", encoding="utf-8") as file:
            metadata[horizon] = json.load(file)
    return models, metadata

def accuracy_summary():
    try:
        results = pd.read_csv("forecast_evaluation.csv")
        return {
            horizon: {
                "ai_mape": round(part["mape"].mean(), 2),
                "baseline_mape": round(part["baseline_mape"].mean(), 2),
            }
            for horizon, part in results.groupby("horizon")
        }
    except FileNotFoundError:
        return {}

def dashboard_accuracy_chip(accuracy):
    sixty = accuracy.get("60m", {})
    ai_mape = sixty.get("ai_mape")
    baseline_mape = sixty.get("baseline_mape")
    if ai_mape is None or baseline_mape is None:
        return None
    return {
        "ai_forecast_error_1h": f"{ai_mape:.2f}%",
        "naive_baseline_error": f"{baseline_mape:.2f}%",
        "status": (
            "AI Outperforming Baseline"
            if ai_mape < baseline_mape
            else "Baseline Outperforming AI"
        ),
    }

def live_recommendation(at=None):
    models, _ = forecast_dependencies()
    features = build_approach_features()
    if at is not None:
        demo_time = pd.to_datetime(at, errors="coerce")
        if pd.isna(demo_time):
            raise ValueError("Invalid 'at' timestamp")
        features = features[features["timestamp"] <= demo_time]
    if features.empty:
        raise ValueError("No feature data are available at the requested time")
    latest = features.groupby("approach", observed=True).tail(1).copy()
    if len(latest) != latest["approach"].nunique() or latest["approach"].nunique() < 4:
        raise ValueError("Forecast data are incomplete for the four approaches")
    predictions = np.maximum(models["30m"].predict(latest[FEATURE_COLUMNS]), 0)
    predicted = {
        str(row.approach): value
        for row, value in zip(latest.itertuples(), predictions)
    }
    observed = {
        str(row.approach): row.vehicle_count for row in latest.itertuples()
    }
    forecast_time = latest["timestamp"].max() + pd.Timedelta(minutes=30)
    return make_recommendation(predicted, observed, forecast_time)

@app.route("/forecast", methods=["GET"])
def get_forecast():
    models, metadata = forecast_dependencies()
    features = build_approach_features()
    latest = features.groupby("approach", observed=True).tail(1).copy()
    accuracy = accuracy_summary()
    forecasts = []

    for horizon, steps in HORIZONS.items():
        predictions = np.maximum(models[horizon].predict(latest[FEATURE_COLUMNS]), 0)
        residuals = metadata[horizon]["residual_quantiles"]
        for (_, row), prediction in zip(latest.iterrows(), predictions):
            lower = max(0, int(round(prediction + residuals["lower"])))
            upper = max(lower, int(round(prediction + residuals["upper"])))
            forecasts.append({
                "timestamp": (
                    row["timestamp"] + pd.Timedelta(minutes=15 * steps)
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "horizon": horizon,
                "approach": str(row["approach"]),
                "observed_count": int(row["vehicle_count"]),
                "predicted_count": int(round(prediction)),
                "lower": lower,
                "upper": upper,
                "confidence_level": 0.90,
            })

    return jsonify({
        "status": "success",
        "accuracy": accuracy,
        "accuracy_chip": dashboard_accuracy_chip(accuracy),
        "forecasts": forecasts,
    })

@app.route("/recommendation", methods=["GET"])
def get_recommendation():
    try:
        return jsonify(live_recommendation(request.args.get("at")))
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as error:
        return jsonify({"status": "error", "message": str(error)}), 503

@app.route("/incidents", methods=["GET"])
def get_incidents():
    return jsonify(read_incidents(VISION_EVENTS_PATH))

@app.route("/incidents/<incident_id>/<action>", methods=["POST"])
def update_incident(incident_id, action):
    if action not in ["confirm", "dismiss"]:
        return jsonify({"status": "error", "message": "Invalid action. Use 'confirm' or 'dismiss'."}), 400
    return jsonify({
        "status": "success",
        "message": f"Incident {incident_id} successfully marked as {action}",
        "action": action
    })

@app.route("/health", methods=["GET"])
def get_health():
    return jsonify(read_health(VISION_HEALTH_PATH))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)