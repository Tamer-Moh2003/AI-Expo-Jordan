"""Data adapters for VISTA's demo files and live backend services.

The UI consumes one stable shape regardless of whether ``MOCK_MODE`` is enabled.
Keeping this boundary outside ``App.py`` makes the dashboard easier to review and
lets the presentation layer remain independent from M1/M2 transport details.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st

from frontend.config import (
    API_BASE,
    EVENTS_WS_URL,
    FORECAST_API_BASE,
    FORECAST_EVALUATION_PATH,
    MEDIA_BASE_URL,
    MOCK_MODE,
    PROJECT_ROOT,
    RECOMMENDATION_SANITY_PATH,
    REVIEW_API_BASE,
    VISION_EVENTS_PATH,
)

try:
    import websocket
except ImportError:  # Optional when the dashboard runs in demo mode.
    websocket = None


def request_json(path: str, fallback: Any, base_url: str | None = None) -> Any:
    """Fetch one API resource without allowing a missing service to crash VISTA."""
    try:
        response = requests.get(f"{base_url or API_BASE}{path}", timeout=2)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        st.session_state.setdefault("connection_errors", {})[path] = str(exc)
        return fallback


def format_video_timestamp(value: Any) -> str:
    """Format a numeric video offset or preserve an existing timestamp string."""
    if isinstance(value, (int, float)):
        total_seconds = int(value)
        return f"00:{total_seconds // 60:02d}:{total_seconds % 60:02d}"
    return str(value)


def incident_video_offset(event: dict[str, Any]) -> int:
    """Return an incident cue point in seconds for the recorded demo video."""
    for field in ("video_timestamp_seconds", "offset_seconds", "clip_timestamp_seconds"):
        value = event.get(field)
        if isinstance(value, (int, float)):
            return max(0, int(value))

    # M1 event IDs end in _seconds_milliseconds, for example _73_900.
    match = re.search(r"_(\d+)_(\d{3})$", str(event.get("event_id", "")))
    return int(match.group(1)) if match else 0


def load_validated_forecast_metrics() -> dict[str, dict[str, float]] | None:
    """Load M2's checked evaluation results for offline/demo mode."""
    if not FORECAST_EVALUATION_PATH.exists():
        return None
    try:
        frame = pd.read_csv(FORECAST_EVALUATION_PATH)
        return {
            str(row["horizon"]): {
                "ai_mape": float(row["lightgbm_mape"]),
                "baseline_mape": float(row["baseline_mape"]),
                "ai_rmse": float(row["lightgbm_rmse"]),
                "baseline_rmse": float(row["baseline_rmse"]),
            }
            for _, row in frame.iterrows()
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def load_validated_recommendation() -> dict[str, Any] | None:
    """Load one scenario already validated by M2 for a credible offline demo."""
    if not RECOMMENDATION_SANITY_PATH.exists():
        return None
    try:
        scenarios = json.loads(RECOMMENDATION_SANITY_PATH.read_text(encoding="utf-8"))
        recommendation = scenarios.get("weekday_am_peak") or next(iter(scenarios.values()))
        return {
            **recommendation,
            "current_phase": recommendation.get(
                "current_phase", recommendation.get("recommended_phase", 0)
            ),
        }
    except (OSError, ValueError, TypeError, StopIteration):
        return None


def normalize_incident(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize both the frozen API event and M1's file-based event shape."""
    event_type = event.get("event_type") or event.get("type") or "Unknown Event"
    approach = str(event.get("approach", "Unknown")).replace("_", " ").title()
    timestamp = format_video_timestamp(event.get("timestamp", ""))
    event_id = event.get("event_id") or (
        f"{timestamp}-{event_type}-{approach}".replace(" ", "-").lower()
    )
    return {
        **event,
        "event_id": event_id,
        "timestamp": timestamp,
        "event_type": str(event_type).replace("_", " ").title(),
        "approach": approach,
        "confidence": float(event.get("confidence", 0)),
        "queue_estimate": event.get("queue_estimate", 0),
        "snapshot_path": event.get("snapshot_path"),
        "clip_path": event.get("clip_path") or event.get("short_clip_path"),
    }


def load_vision_sample_events() -> list[dict[str, Any]]:
    """Load M1's newest file-based delivery until the live service is ready."""
    if not VISION_EVENTS_PATH.exists():
        return []
    try:
        events = json.loads(VISION_EVENTS_PATH.read_text(encoding="utf-8"))
        normalized = []
        for event in events[-3:]:
            incident = normalize_incident(event)
            incident["evidence_root"] = str(VISION_EVENTS_PATH.parent)
            normalized.append(incident)
        return normalized[::-1]
    except (OSError, ValueError, TypeError):
        return []


def media_url(path: str | None) -> str | None:
    """Turn a backend media path into a browser-loadable absolute URL."""
    if not path or path.startswith(("http://", "https://")):
        return path
    return f"{MEDIA_BASE_URL}/{path.lstrip('/')}"


def incident_media_source(incident: dict[str, Any], field: str) -> str | None:
    """Resolve local Day 3 evidence first, then a served media URL."""
    path = incident.get(field)
    if not path:
        return None
    if str(path).startswith(("http://", "https://")):
        return str(path)

    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    evidence_root = incident.get("evidence_root")
    if evidence_root:
        candidate = Path(evidence_root) / path
        if candidate.exists():
            return str(candidate)

    candidate = PROJECT_ROOT / path
    if candidate.exists():
        return str(candidate)
    return media_url(str(path))


def poll_websocket_event() -> dict[str, Any] | None:
    """Read one event when the backend WebSocket becomes available."""
    if MOCK_MODE or websocket is None:
        return None
    connection = None
    try:
        connection = websocket.create_connection(EVENTS_WS_URL, timeout=0.15)
        return json.loads(connection.recv())
    except (OSError, ValueError, websocket.WebSocketException):
        return None
    finally:
        if connection is not None:
            connection.close()


def submit_incident_review(event_id: str, decision: str) -> tuple[bool, str]:
    """Save an operator decision in the demo session or review backend."""
    if MOCK_MODE:
        st.session_state.setdefault("incident_reviews", {})[event_id] = decision
        return True, "Saved in demo session"
    try:
        response = requests.post(
            f"{REVIEW_API_BASE}/incidents/{event_id}/review",
            json={"decision": decision},
            timeout=3,
        )
        response.raise_for_status()
        st.session_state.setdefault("incident_reviews", {})[event_id] = decision
        return True, "Saved to backend"
    except requests.RequestException as exc:
        return False, f"Review service unavailable: {exc}"


def fetch_health() -> dict[str, Any]:
    """Fetch the three health fields frozen in ``api_contract.json``."""
    if MOCK_MODE:
        return {
            "ingestion_rate_fps": 30,
            "dropped_frames": 2,
            "stream_uptime_seconds": 3600,
        }
    return request_json(
        "/health",
        {"ingestion_rate_fps": 0, "dropped_frames": 0, "stream_uptime_seconds": 0},
    )


def fetch_recommendation() -> dict[str, Any]:
    """Fetch M2's guarded signal recommendation or validated demo scenario."""
    if MOCK_MODE:
        return load_validated_recommendation() or {
            "timestamp": "2026-07-14T08:12:00Z",
            "current_phase": 3,
            "current_green_duration_seconds": 32,
            "recommended_phase": 3,
            "recommended_green_duration_seconds": 45,
            "reason": "High queue volume detected",
            "estimated_saving_vehicle_minutes": 12.5,
            "advisory_only": True,
            "not_transmitted_to_controller": True,
            "assumptions": [
                "Green split is proportional to predicted approach demand.",
                "Saturation flow is assumed at 1,800 vehicles/hour/lane.",
                "Estimate is advisory and isolated from the traffic controller.",
            ],
        }
    recommendation = request_json(
        "/recommendation",
        {
            "timestamp": "",
            "recommended_phase": 0,
            "recommended_green_duration_seconds": 0,
            "reason": "Recommendation service unavailable",
            "estimated_saving_vehicle_minutes": 0,
            "advisory_only": True,
            "not_transmitted_to_controller": True,
        },
        base_url=FORECAST_API_BASE,
    )
    recommendation.setdefault(
        "assumptions",
        [
            "Green split is proportional to predicted approach demand.",
            "Saturation flow and delay parameters require GAM validation.",
            "Recommendation is advisory only and is not transmitted to the controller.",
        ],
    )
    return recommendation


def fetch_incidents() -> list[dict[str, Any]]:
    """Fetch live incidents or M1's latest evidence delivery."""
    if MOCK_MODE:
        samples = load_vision_sample_events()
        if samples:
            return samples
        return [
            normalize_incident(
                {
                    "timestamp": "2026-07-14T08:10:00Z",
                    "event_type": "Stalled Vehicle",
                    "approach": "North",
                    "confidence": 0.95,
                    "queue_estimate": 15,
                    "snapshot_path": "/media/snapshots/inc_001.jpg",
                    "clip_path": "/media/clips/inc_001.mp4",
                }
            )
        ]
    return [
        normalize_incident(event) for event in request_json("/incidents", [])
    ]


def fetch_forecast() -> tuple[np.ndarray, ...]:
    """Support both the frozen API list and M2's horizon-based payload."""
    accuracy_metrics = None
    if MOCK_MODE:
        accuracy_metrics = load_validated_forecast_metrics() or {
            "ai_forecast_error_1h": "18.98%",
            "naive_baseline_error": "25.42%",
            "status": "AI Outperforming Baseline",
        }
        raw = [
            {"timestamp": "08:00", "approach": "North", "predicted_count": 33, "observed_count": 32, "lower": 30, "upper": 36},
            {"timestamp": "08:05", "approach": "North", "predicted_count": 38, "observed_count": 36, "lower": 34, "upper": 41},
            {"timestamp": "08:10", "approach": "North", "predicted_count": 42, "observed_count": 40, "lower": 38, "upper": 46},
            {"timestamp": "08:15", "approach": "North", "predicted_count": 48, "observed_count": 46, "lower": 43, "upper": 53},
            {"timestamp": "08:20", "approach": "North", "predicted_count": 55, "observed_count": None, "lower": 50, "upper": 60},
            {"timestamp": "08:25", "approach": "North", "predicted_count": 52, "observed_count": None, "lower": 47, "upper": 57},
            {"timestamp": "08:30", "approach": "North", "predicted_count": 46, "observed_count": None, "lower": 41, "upper": 51},
            {"timestamp": "08:35", "approach": "North", "predicted_count": 49, "observed_count": None, "lower": 44, "upper": 54},
            {"timestamp": "08:40", "approach": "North", "predicted_count": 53, "observed_count": None, "lower": 48, "upper": 59},
            {"timestamp": "08:45", "approach": "North", "predicted_count": 57, "observed_count": None, "lower": 51, "upper": 63},
            {"timestamp": "08:50", "approach": "North", "predicted_count": 61, "observed_count": None, "lower": 55, "upper": 68},
            {"timestamp": "08:55", "approach": "North", "predicted_count": 58, "observed_count": None, "lower": 52, "upper": 65},
            {"timestamp": "09:00", "approach": "North", "predicted_count": 54, "observed_count": None, "lower": 48, "upper": 60},
        ]
    else:
        payload = request_json("/forecast", [], base_url=FORECAST_API_BASE)
        if isinstance(payload, dict):
            accuracy_metrics = payload.get("accuracy") or payload.get("accuracy_chip")
            if not accuracy_metrics and payload.get("baseline_mape"):
                accuracy_metrics = {"naive_baseline_error": payload["baseline_mape"]}
            raw = payload.get("forecasts", [])
        else:
            raw = payload

    if not raw:
        return (np.array([]),) * 5 + (accuracy_metrics,)

    is_horizon_payload = "horizon" in raw[0]
    if is_horizon_payload and len({row.get("approach") for row in raw}) > 1:
        grouped: dict[str, dict[str, Any]] = {}
        for row in raw:
            horizon = str(row["horizon"])
            item = grouped.setdefault(
                horizon,
                {
                    "horizon": horizon,
                    "timestamp": row.get("timestamp"),
                    "predicted_count": 0,
                    "observed_count": 0,
                    "lower": 0,
                    "upper": 0,
                },
            )
            for field in ("predicted_count", "observed_count", "lower", "upper"):
                item[field] += int(row.get(field) or 0)
        raw = sorted(
            grouped.values(), key=lambda row: int(row["horizon"].rstrip("m"))
        )

    if is_horizon_payload:
        horizon_minutes = [int(str(row["horizon"]).rstrip("m")) for row in raw]
        minutes = np.array([0, *horizon_minutes])
        current_observed = raw[0].get("observed_count")
        observed = np.array([current_observed, *([None] * len(raw))], dtype=object)
        forecast_values = np.array(
            [None, *[row["predicted_count"] for row in raw]], dtype=object
        )
        upper = np.array(
            [None, *[row.get("upper", row.get("upper_bound")) for row in raw]],
            dtype=object,
        )
        lower = np.array(
            [None, *[row.get("lower", row.get("lower_bound")) for row in raw]],
            dtype=object,
        )
        return minutes, observed, forecast_values, upper, lower, accuracy_metrics

    if len(raw) == 3 and all(row.get("timestamp") for row in raw):
        minutes = np.array([15, 30, 60])
    else:
        minutes = np.arange(0, len(raw) * 5, 5)
    forecast_values = np.array(
        [row["predicted_count"] for row in raw], dtype=object
    )
    observed = np.array([row.get("observed_count") for row in raw], dtype=object)
    upper = np.array(
        [row.get("upper", row.get("upper_bound")) for row in raw], dtype=object
    )
    lower = np.array(
        [row.get("lower", row.get("lower_bound")) for row in raw], dtype=object
    )
    return minutes, observed, forecast_values, upper, lower, accuracy_metrics
