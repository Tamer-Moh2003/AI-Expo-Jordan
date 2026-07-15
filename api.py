from flask import Flask, jsonify
import pandas as pd
import numpy as np
import lightgbm as lgb

app = Flask(__name__)

model_15 = lgb.Booster(model_file='model_15m.txt')
model_30 = lgb.Booster(model_file='model_30m.txt')
model_60 = lgb.Booster(model_file='model_60m.txt')

@app.route('/forecast', methods=['GET'])
def get_forecast():
    df = pd.read_csv('feature_table.csv')
    
    features = ['vehicle_count', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_96',
                'rolling_mean_1h', 'rolling_mean_4h', 'hour', 'day_of_week', 
                'is_weekend', 'is_holiday']
                
    last_row = df[features].iloc[[-1]]
    
    pred_15 = max(0, int(np.round(model_15.predict(last_row)[0])))
    pred_30 = max(0, int(np.round(model_30.predict(last_row)[0])))
    pred_60 = max(0, int(np.round(model_60.predict(last_row)[0])))
    
    response = {
        "status": "success",
        "baseline_mape": "25.42%",
        "forecasts": [
            {
                "horizon": "15m",
                "predicted_count": pred_15,
                "lower_bound": int(pred_15 * 0.90),
                "upper_bound": int(pred_15 * 1.10)
            },
            {
                "horizon": "30m",
                "predicted_count": pred_30,
                "lower_bound": int(pred_30 * 0.85),
                "upper_bound": int(pred_30 * 1.15)
            },
            {
                "horizon": "60m",
                "predicted_count": pred_60,
                "lower_bound": int(pred_60 * 0.80),
                "upper_bound": int(pred_60 * 1.20)
            }
        ]
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=5000, debug=True)