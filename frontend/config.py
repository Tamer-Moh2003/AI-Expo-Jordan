"""Central configuration and filesystem paths for the VISTA dashboard."""

from __future__ import annotations

import base64
import os
from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_ROOT.parent

MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() in {"1", "true", "yes"}
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
FORECAST_API_BASE = os.getenv("FORECAST_API_BASE", "http://127.0.0.1:5000")
EVENTS_WS_URL = os.getenv("EVENTS_WS_URL", "ws://localhost:8000/events")
VIDEO_STREAM_URL = os.getenv("VIDEO_STREAM_URL", "")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", API_BASE).rstrip("/")
REVIEW_API_BASE = os.getenv("REVIEW_API_BASE", API_BASE).rstrip("/")

LOGO_PATH = FRONTEND_ROOT / "assets" / "stms-logo.png"
FAVICON_PATH = FRONTEND_ROOT / "assets" / "vista-favicon.png"
LOCAL_DEMO_VIDEO_PATH = Path(
    os.getenv(
        "LOCAL_DEMO_VIDEO_PATH",
        str(FRONTEND_ROOT / "assets" / "demo" / "annotated_demo.mp4"),
    )
)

DAY3_EVIDENCE_ROOT = PROJECT_ROOT / "vision" / "outputs" / "day3_evidence_test"
DAY3_EVENTS_PATH = DAY3_EVIDENCE_ROOT / "events.json"
DAY2_EVENTS_PATH = (
    PROJECT_ROOT / "vision" / "sample_outputs" / "day2_dataset1" / "events.json"
)
VISION_EVENTS_PATH = DAY3_EVENTS_PATH if DAY3_EVENTS_PATH.exists() else DAY2_EVENTS_PATH

DAY3_PREVIEW_PATH = DAY3_EVIDENCE_ROOT / "PREVIEW_ZONE_POLYGONS.jpg"
DAY2_PREVIEW_PATH = (
    PROJECT_ROOT
    / "vision"
    / "sample_outputs"
    / "day2_dataset1"
    / "zones_preview.jpg"
)
VISION_PREVIEW_PATH = (
    DAY3_PREVIEW_PATH if DAY3_PREVIEW_PATH.exists() else DAY2_PREVIEW_PATH
)

FORECAST_EVALUATION_PATH = PROJECT_ROOT / "forecast_evaluation_summary.csv"
RECOMMENDATION_SANITY_PATH = PROJECT_ROOT / "recommendation_sanity_details.json"


def _data_uri(path: Path, mime_type: str) -> str:
    """Return a local image as an embeddable data URI."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


LOGO_DATA_URI = _data_uri(LOGO_PATH, "image/png")
VISION_PREVIEW_DATA_URI = _data_uri(VISION_PREVIEW_PATH, "image/jpeg")
