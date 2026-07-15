import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Reproducible demo data: every full pipeline run produces the same evaluation.
random.seed(42)
np.random.seed(42)

start_date = pd.to_datetime('2026-04-15')
days = 90
timestamps = pd.date_range(start=start_date, periods=days * 24 * 4, freq='15min')

detectors_dict = {
    'North_Arar_St': ['D1', 'D2', 'D3', 'D4', 'D5', 'D6'],
    'South_Arar_St': ['D7', 'D8', 'D9', 'D10', 'D11', 'D12'],
    'East_Approach': ['D13', 'D14', 'D15', 'D16', 'D17'],
    'West_Approach': ['D18', 'D19', 'D20', 'D21', 'D22']
}

detectors_data = []
for approach, lanes in detectors_dict.items():
    for d in lanes:
        detectors_data.append({
            'id': d,
            'location_name': 'Wadi Saqra Intersection',
            'approach': approach
        })
pd.DataFrame(detectors_data).to_csv('detectors.csv', index=False)

counts_data = []
signal_data = []
incidents_data = []
forecasts_data = []
recommendations_data = []
health_data = []

uptime = 0

for ts in timestamps:
    hour = ts.hour
    day_of_week = ts.dayofweek
    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')

    if day_of_week < 4 or day_of_week == 6:
        if 7 <= hour <= 9:
            base_vol = 70
        elif 15 <= hour <= 18:
            base_vol = 120
        elif 18 < hour <= 21:
            base_vol = 70
        else:
            base_vol = 15
    elif day_of_week == 4:
        if 14 <= hour <= 22:
            base_vol = 45
        else:
            base_vol = 15
    else:
        if 10 <= hour <= 21:
            base_vol = 50
        else:
            base_vol = 20

    if random.random() < 0.02:
        base_vol *= 0.5

    event = "Normal"
    rand_val = random.random()
    if rand_val < 0.005:
        event = "Accident"
    elif rand_val < 0.015:
        event = "Emergency"

    uptime += 900
    if random.random() < 0.001:
        uptime = 0

    health_data.append({
        'timestamp': ts_str,
        'ingestion_rate_fps': random.choice([29, 30]),
        'dropped_frames': random.choice([0, 0, 0, 1, 2]),
        'stream_uptime_seconds': uptime
    })

    for phase in [1, 2, 3, 4]:
        signal_data.append({
            'intersection_id': 'Wadi_Saqra_Int',
            'phase_number': phase,
            'light_state': random.choice(['Green', 'Yellow', 'Red']),
            'timestamp': ts_str
        })

    for approach, lanes in detectors_dict.items():
        multiplier = 1.25 if 'Arar' in approach else 1.0
        
        for d in lanes:
            final_volume = base_vol * multiplier
            if event == "Accident" and 'Arar' in approach:
                final_volume *= 1.8
            elif event == "Emergency":
                final_volume *= 1.4
            
            count = np.random.poisson(final_volume)
            counts_data.append({
                'detector_id': d,
                'timestamp': ts_str,
                'vehicle_count': int(count)
            })

        pred = int(base_vol * multiplier * random.uniform(0.9, 1.1))
        forecasts_data.append({
            'timestamp': ts_str,
            'approach': approach,
            'predicted_count': pred,
            'lower_bound': int(pred * 0.8),
            'upper_bound': int(pred * 1.2)
        })

        if event == "Accident" and 'Arar' in approach:
            incidents_data.append({
                'timestamp': ts_str,
                'event_type': 'Accident',
                'approach': approach,
                'confidence': round(random.uniform(85.0, 99.9), 2),
                'queue_estimate': int(base_vol * multiplier * 2.5),
                'snapshot_path': f'/snapshots/{ts.strftime("%Y%m%d_%H%M")}_{approach}_accident.jpg',
                'clip_path': f'/clips/{ts.strftime("%Y%m%d_%H%M")}_{approach}_accident.mp4'
            })
        elif event == "Emergency":
            incidents_data.append({
                'timestamp': ts_str,
                'event_type': 'Emergency Vehicle',
                'approach': approach,
                'confidence': round(random.uniform(90.0, 99.9), 2),
                'queue_estimate': int(base_vol * multiplier * 1.5),
                'snapshot_path': f'/snapshots/{ts.strftime("%Y%m%d_%H%M")}_{approach}_emergency.jpg',
                'clip_path': f'/clips/{ts.strftime("%Y%m%d_%H%M")}_{approach}_emergency.mp4'
            })

        if base_vol * multiplier > 80 or event != "Normal":
            rec_phase = 1 if 'North' in approach else (2 if 'South' in approach else (3 if 'East' in approach else 4))
            dur = int(random.uniform(45, 90))
            saving = round(random.uniform(5.0, 30.0), 2)
            recommendations_data.append({
                'timestamp': ts_str,
                'recommended_phase': rec_phase,
                'recommended_green_duration': dur,
                'reason': f'High queue volume detected' if event == "Normal" else event,
                'estimated_saving_vehicle_minutes': saving
            })

pd.DataFrame(counts_data).to_csv('counts.csv', index=False)
pd.DataFrame(signal_data).to_csv('signal_events.csv', index=False)
pd.DataFrame(incidents_data).to_csv('incidents.csv', index=False)
pd.DataFrame(forecasts_data).to_csv('forecasts.csv', index=False)
pd.DataFrame(recommendations_data).to_csv('recommendations.csv', index=False)
pd.DataFrame(health_data).to_csv('system_health.csv', index=False)
