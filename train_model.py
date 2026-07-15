import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error

df = pd.read_csv('feature_table.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

df = df.sort_values(by=['detector_id', 'timestamp'])

df['target_15m'] = df.groupby('detector_id')['vehicle_count'].shift(-1)
df['target_30m'] = df.groupby('detector_id')['vehicle_count'].shift(-2)
df['target_60m'] = df.groupby('detector_id')['vehicle_count'].shift(-4)
df = df.dropna()

features = ['vehicle_count', 'lag_1', 'lag_2', 'lag_3', 'lag_4', 'lag_96',
            'rolling_mean_1h', 'rolling_mean_4h', 'hour', 'day_of_week', 
            'is_weekend', 'is_holiday']

split_date = df['timestamp'].max() - pd.Timedelta(days=14)
train_df = df[df['timestamp'] <= split_date]
test_df = df[df['timestamp'] > split_date]

X_train, X_test = train_df[features], test_df[features]

def calc_mape(actual, pred):
    return np.mean(np.abs((actual - pred) / (actual + 1e-5))) * 100

horizons = {'15m': 'target_15m', '30m': 'target_30m', '60m': 'target_60m'}

for name, target in horizons.items():
    y_train, y_test = train_df[target], test_df[target]
    
    model = lgb.LGBMRegressor(
        objective='mape',
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=63,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    preds = np.maximum(preds, 0)
    
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mape = calc_mape(y_test, preds)
    
    print(f"\n✅ Forecast Horizon: {name} ahead")
    print(f"   - RMSE: {rmse:.2f} vehicles")
    print(f"   - MAPE: {mape:.2f}% (Target: < 25.42%)")
    
    model.booster_.save_model(f'model_{name}.txt')