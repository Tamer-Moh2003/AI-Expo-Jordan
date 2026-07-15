FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY api.py feature_table.csv model_15m.txt model_30m.txt model_60m.txt /app/
COPY backend/vision_store.py /app/backend/vision_store.py

ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "api:app"]
