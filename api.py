from functools import lru_cache
import os
import sys

from flask import Flask, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from vision_store import read_health, read_incidents


app = Flask(__name__)
VISION_HEALTH_PATH = os.environ.get("VISION_HEALTH_PATH", "/app/data/vision/health.json")
VISION_EVENTS_PATH = os.environ.get("VISION_EVENTS_PATH", "/app/data/vision/events.json")


@lru_cache(maxsize=1)
def forecast_dependencies():
    import lightgbm as lgb
    import numpy as np
    import pandas as pd

    models = {
        "15m": lgb.Booster(model_file="model_15m.txt"),
        "30m": lgb.Booster(model_file="model_30m.txt"),
        "60m": lgb.Booster(model_file="model_60m.txt"),
    }
    return models, np, pd


@app.route("/forecast", methods=["GET"])
def get_forecast():
    models, np, pd = forecast_dependencies()
    df = pd.read_csv("feature_table.csv")
    features = [
        "vehicle_count", "lag_1", "lag_2", "lag_3", "lag_4", "lag_96",
        "rolling_mean_1h", "rolling_mean_4h", "hour", "day_of_week",
        "is_weekend", "is_holiday",
    ]
    last_row = df[features].iloc[[-1]]
    forecasts = []
    margins = {"15m": 0.10, "30m": 0.15, "60m": 0.20}
    for horizon, model in models.items():
        predicted = max(0, int(np.round(model.predict(last_row)[0])))
        margin = margins[horizon]
        forecasts.append(
            {
                "horizon": horizon,
                "predicted_count": predicted,
                "lower_bound": int(predicted * (1 - margin)),
                "upper_bound": int(predicted * (1 + margin)),
            }
        )
    return jsonify({"status": "success", "baseline_mape": "25.42%", "forecasts": forecasts})


@app.route("/incidents", methods=["GET"])
def get_incidents():
    return jsonify(read_incidents(VISION_EVENTS_PATH))


@app.route("/health", methods=["GET"])
def get_health():
    return jsonify(read_health(VISION_HEALTH_PATH))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
