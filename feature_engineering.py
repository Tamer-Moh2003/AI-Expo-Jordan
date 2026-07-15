import pandas as pd

print("🚀 Starting Feature Engineering (Task 28)...")

df = pd.read_csv('counts.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

df = df.sort_values(by=['detector_id', 'timestamp']).reset_index(drop=True)

df['lag_1'] = df.groupby('detector_id')['vehicle_count'].shift(1)
df['lag_2'] = df.groupby('detector_id')['vehicle_count'].shift(2)
df['lag_3'] = df.groupby('detector_id')['vehicle_count'].shift(3)
df['lag_4'] = df.groupby('detector_id')['vehicle_count'].shift(4)
df['lag_96'] = df.groupby('detector_id')['vehicle_count'].shift(96)

df['rolling_mean_1h'] = df.groupby('detector_id')['vehicle_count'].transform(lambda x: x.rolling(window=4).mean())
df['rolling_mean_4h'] = df.groupby('detector_id')['vehicle_count'].transform(lambda x: x.rolling(window=16).mean())

df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # الاثنين=0، الأحد=6

df['is_weekend'] = df['day_of_week'].isin([4, 5]).astype(int)

df['is_holiday'] = 0 

df = df.dropna()

df.to_csv('feature_table.csv', index=False)

print("✅ Feature table successfully created and saved as 'feature_table.csv'!")