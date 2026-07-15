import pandas as pd
import numpy as np

print("⏳ Loading data and calculating Naive Baseline...")

df = pd.read_csv('counts.csv')

df['timestamp'] = pd.to_datetime(df['timestamp'])

df_past = df[['timestamp', 'detector_id', 'vehicle_count']].copy()
df_past['timestamp'] = df_past['timestamp'] + pd.Timedelta(days=7)
df_past = df_past.rename(columns={'vehicle_count': 'predicted_count'})

baseline_df = pd.merge(df, df_past, on=['timestamp', 'detector_id'], how='inner')

# 3. حساب نسبة الخطأ (MAPE - Mean Absolute Percentage Error)
actual = baseline_df['vehicle_count']
predicted = baseline_df['predicted_count']

epsilon = 1e-5 
mape = np.mean(np.abs((actual - predicted) / (actual + epsilon))) * 100

print("-" * 40)
print(f"🎯 Naive Baseline MAPE: {mape:.2f}%")
print("🔥 Write this number on the wall! Your LightGBM AI must beat it.")
print("-" * 40)