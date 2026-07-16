FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY api.py forecasting_features.py signal_advisor.py /app/
COPY feature_table.csv forecast_evaluation.csv parsed_signal_phase.csv /app/
COPY model_15m.txt model_30m.txt model_60m.txt /app/
COPY model_15m_metadata.json model_30m_metadata.json model_60m_metadata.json /app/
COPY backend/vision_store.py /app/backend/vision_store.py

ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "api:app"]
