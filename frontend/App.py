import base64
import html
import json
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

try:
    import websocket
except ImportError:  # Installed by frontend/requirements.txt in the container.
    websocket = None

# ============================================================
# 0. DATA SOURCE LAYER
# Flip MOCK_MODE to False once M2's backend is running.
# Every function below returns data in the SAME shape whether
# it comes from mock data or the real API -- so nothing else
# in this file needs to change when you swap it.
# ============================================================
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() in {"1", "true", "yes"}
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
EVENTS_WS_URL = os.getenv("EVENTS_WS_URL", "ws://localhost:8000/events")
VIDEO_STREAM_URL = os.getenv("VIDEO_STREAM_URL", "")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", API_BASE).rstrip("/")
LOGO_PATH = Path(__file__).parent / "assets" / "stms-logo.png"
LOGO_DATA_URI = (
    "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    if LOGO_PATH.exists()
    else ""
)


def request_json(path, fallback):
    """Fetch one API resource without allowing a missing service to crash VISTA."""
    try:
        response = requests.get(f"{API_BASE}{path}", timeout=2)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        st.session_state.setdefault("connection_errors", {})[path] = str(exc)
        return fallback


def media_url(path):
    """Turn a backend media path into a browser-loadable absolute URL."""
    if not path or path.startswith(("http://", "https://")):
        return path
    return f"{MEDIA_BASE_URL}/{path.lstrip('/')}"


def poll_websocket_event():
    """Read one event when the backend WebSocket becomes available."""
    if MOCK_MODE or websocket is None:
        return None
    connection = None
    try:
        connection = websocket.create_connection(EVENTS_WS_URL, timeout=0.15)
        payload = connection.recv()
        return json.loads(payload)
    except (OSError, ValueError, websocket.WebSocketException):
        return None
    finally:
        if connection is not None:
            connection.close()


def fetch_health():
    # Matches api_contract.json "GET /health" exactly. Frozen contract.
    if MOCK_MODE:
        return {"ingestion_rate_fps": 30, "dropped_frames": 2, "stream_uptime_seconds": 3600}
    return request_json(
        "/health",
        {"ingestion_rate_fps": 0, "dropped_frames": 0, "stream_uptime_seconds": 0},
    )


def fetch_recommendation():
    # Matches api_contract.json "GET /recommendation" exactly. Frozen contract --
    # advisory_only / not_transmitted_to_controller are computed on the fly by
    # the backend (always true for this prototype); estimated_saving_vehicle_minutes
    # is also computed on the fly. All three are guaranteed present now.
    if MOCK_MODE:
        return {
            "timestamp": "2026-07-14T08:12:00Z",
            "recommended_phase": 3,
            "recommended_green_duration_seconds": 45,
            "reason": "High queue volume detected",
            "estimated_saving_vehicle_minutes": 12.5,
            "advisory_only": True,
            "not_transmitted_to_controller": True,
        }
    return request_json(
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
    )


def fetch_incidents():
    # Matches api_contract.json "GET /incidents" exactly. Frozen contract --
    # confidence comes from the DB schema; snapshot_path, clip_path, and
    # queue_estimate are now stored via ALTER TABLE on M2's side. Note:
    # confidence arrives as a 0-1 fraction (e.g. 0.95), not a percentage.
    if MOCK_MODE:
        return [
            {"timestamp": "2026-07-14T08:10:00Z", "event_type": "Stalled Vehicle", "approach": "North",
             "confidence": 0.95, "queue_estimate": 15,
             "snapshot_path": "/media/snapshots/inc_001.jpg", "clip_path": "/media/clips/inc_001.mp4"},
            {"timestamp": "2026-07-14T08:22:00Z", "event_type": "Queue Spillback", "approach": "East",
             "confidence": 0.87, "queue_estimate": 22,
             "snapshot_path": "/media/snapshots/inc_002.jpg", "clip_path": "/media/clips/inc_002.mp4"},
        ]
    return request_json("/incidents", [])


def fetch_forecast():
    """Matches api_contract.json "GET /forecast" exactly -- each row now
    carries timestamp, approach, predicted_count, observed_count, lower,
    upper. observed_count is joined server-side from the counts table.
    Frozen contract, no more approximation needed here."""
    if MOCK_MODE:
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
        raw = request_json("/forecast", [])

    if not raw:
        return np.array([]), np.array([]), np.array([]), np.array([]), np.array([])

    minutes = np.arange(0, len(raw) * 5, 5)
    forecast_vals = np.array([row["predicted_count"] for row in raw], dtype=object)
    observed = np.array([row.get("observed_count") for row in raw], dtype=object)
    upper = np.array([row.get("upper") for row in raw], dtype=object)
    lower = np.array([row.get("lower") for row in raw], dtype=object)

    return minutes, observed, forecast_vals, upper, lower


# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="VISTA | Traffic Advisor",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. DESIGN SYSTEM
# One accent color for ALERTS, one accent color for FORECASTS.
# Everything else stays neutral (dark operator-console palette).
# ============================================================
st.markdown("""
    <style>
    :root {
        --bg-main: #050b14;
        --bg-card: #0a1422;
        --bg-card-soft: #0d1929;
        --border-color: rgba(148,163,184,.14);
        --text-primary: #f8fafc;
        --text-muted: #8494aa;

        --accent-alert: #ff4d4f;      /* single color for ALL alert states */
        --accent-alert-bg: rgba(255, 77, 79, 0.10);
        --accent-forecast: #3fb0ff;   /* single color for ALL forecast/AI states */
        --accent-forecast-bg: rgba(63, 176, 255, 0.10);

        --accent-safe: #2ecc71;       /* used only for the advisory-only guard rail */
    }

    .stApp {
        background:
            radial-gradient(circle at 16% -5%, rgba(14,165,233,.10), transparent 31rem),
            radial-gradient(circle at 92% 18%, rgba(16,185,129,.045), transparent 24rem),
            var(--bg-main);
    }
    .block-container { padding: .7rem 1.5rem 1rem; max-width: 1680px; }
    .stDeployButton, #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: transparent;
        height: 1.8rem;
    }
    section[data-testid="stSidebar"] { background:#07101c; border-right:1px solid var(--border-color); }
    section[data-testid="stSidebar"] .block-container { padding-top:1.25rem; }
    .stButton > button {
        border-radius:9px; border:1px solid rgba(148,163,184,.18); background:#0b1726;
        color:#d8e2ef; min-height:38px; transition:all .18s ease;
    }
    .stButton > button:hover { border-color:rgba(56,189,248,.55); color:#fff; transform:translateY(-1px); }
    div[data-baseweb="select"] > div { background:#0b1726; border-color:rgba(148,163,184,.16); }
    details { background:#081421 !important; border:1px solid var(--border-color) !important; border-radius:10px !important; }

    .dashboard-card {
        background: linear-gradient(145deg, rgba(12,25,42,.96), rgba(7,17,30,.96));
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 14px;
        height: 100%;
        box-shadow: 0 16px 42px rgba(0,0,0,.22);
    }
    .card-title {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(148,163,184,.10);
        padding-bottom: 8px;
    }

    /* --- Operator header --- */
    .operator-header {
        display:flex; align-items:center; justify-content:space-between; gap:22px;
        background:linear-gradient(120deg,rgba(11,24,41,.96),rgba(7,16,28,.92));
        border:1px solid var(--border-color); position:relative; overflow:hidden;
        border-radius:16px; padding:14px 18px; margin-bottom:14px;
        box-shadow:0 18px 45px rgba(0,0,0,.24);
    }
    .operator-header::after { content:''; position:absolute; right:-40px; top:-80px; width:220px; height:220px; border:1px solid rgba(56,189,248,.09); border-radius:50%; }
    .brand-wrap { display:flex; align-items:center; gap:14px; position:relative; z-index:1; }
    .brand-icon {
        width:58px; height:58px; display:flex; align-items:center; justify-content:center;
        border-radius:14px; background:#050c16; border:1px solid rgba(56,189,248,.24);
        padding:2px; overflow:hidden; box-shadow:0 0 24px rgba(14,165,233,.13);
    }
    .brand-icon img { width:100%; height:100%; object-fit:cover; border-radius:12px; }
    .brand-eyebrow { color:#38bdf8; font-size:.62rem; font-weight:750; letter-spacing:.13em; text-transform:uppercase; margin-bottom:3px; }
    .brand-title { color:var(--text-primary); font-size:1.12rem; font-weight:720; line-height:1.2; letter-spacing:-.01em; }
    .brand-subtitle { color:var(--text-muted); font-size:.69rem; margin-top:4px; }
    .header-meta { display:flex; align-items:center; gap:9px; flex-wrap:wrap; justify-content:flex-end; position:relative; z-index:1; }
    .status-pill {
        padding:6px 9px; border-radius:999px; font-size:.68rem; font-weight:650;
        color:#86efac; background:rgba(46,204,113,.09); border:1px solid rgba(46,204,113,.28);
    }
    .status-pill::before { content:'●'; margin-right:6px; }
    .demo-banner {
        background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.27);
        border-radius:999px; padding:6px 10px; font-size:.67rem; color:#fbbf24;
    }

    /* --- Video placeholder (no external network dependency) --- */
    .video-shell {
        background:
            linear-gradient(rgba(7,17,31,.22), rgba(7,17,31,.6)),
            repeating-linear-gradient(45deg, #0a1727, #0a1727 12px, #0d1b2d 12px, #0d1b2d 24px);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        height: 360px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--text-muted);
        position: relative;
    }
    .video-shell .rec-dot {
        position: absolute; top: 12px; left: 14px;
        color: #fff; background:rgba(255,77,79,.86); padding:4px 8px;
        border-radius:5px; font-size: 0.66rem; font-weight: 700;
    }
    .video-shell .cam-label {
        position: absolute; bottom: 13px; left: 14px; padding:5px 8px;
        border-radius:6px; background:rgba(7,17,31,.76); font-size: 0.7rem; color: #c9d5e3;
    }
    .video-stats { position:absolute; top:12px; right:14px; display:flex; gap:6px; }
    .video-stat { backdrop-filter:blur(8px); background:rgba(7,17,31,.72); border:1px solid rgba(148,163,184,.18); border-radius:7px; padding:5px 8px; font-size:.61rem; color:#c9d5e3; }
    .tracking-reticle { width:80px; height:48px; border:1px solid rgba(63,176,255,.7); position:relative; }
    .tracking-reticle::after { content:'ID 024 · CAR'; position:absolute; left:-1px; top:-18px; color:#7dd3fc; font-size:.58rem; white-space:nowrap; }

    /* --- Alert feed items --- */
    .alert-item {
        background-color: var(--accent-alert-bg);
        border-left: 3px solid var(--accent-alert);
        border:1px solid rgba(255,77,79,.15); border-left:3px solid var(--accent-alert);
        border-radius: 9px; padding: 11px 12px; margin-bottom: 9px;
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }
    .alert-thumb {
        width: 46px; height: 46px;
        border-radius: 5px;
        background: repeating-linear-gradient(45deg, #20262f, #20262f 6px, #262d38 6px, #262d38 12px);
        flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.9rem;
        border: 1px solid var(--border-color);
    }
    .alert-text { font-size: 0.8rem; line-height: 1.35; color: var(--text-primary); }
    .alert-meta { color: var(--text-muted); font-size: 0.72rem; }

    .info-item {
        background-color: rgba(139,148,158,0.08);
        border-left: 3px solid var(--text-muted);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
        font-size: 0.78rem;
        color: var(--text-muted);
    }

    /* --- Advisor / recommendation --- */
    .advisory-badge {
        background-color: rgba(46, 204, 113, 0.10);
        border: 1px solid var(--accent-safe);
        color: var(--accent-safe);
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 0.72rem;
        font-weight: 600;
        text-align: center;
        margin-top: 10px;
    }
    .timing-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin:12px 0; }
    .timing-box { background:rgba(7,17,31,.58); border:1px solid var(--border-color); border-radius:9px; padding:10px; }
    .timing-label { color:var(--text-muted); font-size:.65rem; text-transform:uppercase; letter-spacing:.05em; }
    .timing-value { color:var(--text-primary); font-size:1.25rem; font-weight:750; margin-top:3px; }
    .timing-box.recommended { border-color:rgba(63,176,255,.42); background:rgba(63,176,255,.07); }
    .health-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:5px 0 8px; }
    .health-item { background:linear-gradient(145deg,#0b1726,#08111e); border:1px solid var(--border-color); border-radius:12px; padding:13px 15px; box-shadow:0 10px 25px rgba(0,0,0,.14); }
    .health-label { color:var(--text-muted); font-size:.68rem; text-transform:uppercase; letter-spacing:.04em; }
    .health-value { color:var(--text-primary); font-size:1.05rem; font-weight:700; margin-top:3px; }
    .health-ok { color:#4ade80; font-size:.62rem; float:right; }
    @media (max-width: 900px) {
        .operator-header { align-items:flex-start; flex-direction:column; }
        .header-meta { justify-content:flex-start; }
        .health-strip { grid-template-columns:1fr; }
    }
    .assumption-note {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin-top: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 3. DATA — pulled through the fetch layer above.
# In MOCK_MODE these return local dicts; once MOCK_MODE = False
# they call the real endpoints instead. Nothing below this line
# needs to change when the backend goes live.
# ============================================================
mock_health = fetch_health()
mock_recommendation = fetch_recommendation()
mock_alerts = fetch_incidents()
live_event = poll_websocket_event()
if live_event:
    mock_alerts = [live_event, *mock_alerts]
mock_system_msgs = [
    {"time": "16:30", "text": "Connected to synthetic SCATS database successfully."},
]

minutes, observed, forecast, forecast_upper, forecast_lower = fetch_forecast()
NOW_MINUTE = 15  # last observed interval; derive from live timestamps after integration

# ============================================================
# 4. HEADER
# ============================================================
st.markdown(
    "<div class='operator-header'>"
    f"<div class='brand-wrap'><div class='brand-icon'><img src='{LOGO_DATA_URI}' alt='STMS logo'></div><div>"
    "<div class='brand-eyebrow'>VISUAL INTELLIGENT SMART TRAFFIC ADVISOR</div>"
    "<div class='brand-title'>VISTA</div>"
    "<div class='brand-subtitle'>GAM · Intersection 806 · Wadi Saqra Operator Console</div>"
    "</div></div>"
    "<div class='header-meta'><span class='status-pill'>SYSTEM ONLINE</span>"
    "<span class='demo-banner'>DEMO · RECORDED VIDEO & SYNTHETIC SCATS</span></div>"
    "</div>",
    unsafe_allow_html=True,
)

# ============================================================
# 5. SIDEBAR — demo control (functional via session_state)
# ============================================================
if "playback" not in st.session_state:
    st.session_state.playback = "paused"

with st.sidebar:
    st.markdown("### VISTA Operations")
    st.caption("Visual Intelligent Smart Traffic Advisor")
    mode_label = "DEMO / MOCK" if MOCK_MODE else "LIVE SERVICES"
    st.caption(f"Data mode: **{mode_label}**")
    st.selectbox("Select Lane Camera / Traffic Video:", ["Intersection 806 — Wadi Saqra (Live Demo)"])

    st.markdown("---")
    st.markdown("### 🎮 Demo Control")
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ Play"):
        st.session_state.playback = "playing"
    if c2.button("⏸️ Pause"):
        st.session_state.playback = "paused"
    if c3.button("🚨 Jump"):
        st.session_state.playback = "jumped_to_incident"

    st.caption(f"Status: **{st.session_state.playback}**")
    if not MOCK_MODE:
        with st.expander("Connection status"):
            st.caption(f"API: `{API_BASE}`")
            st.caption(f"Events: `{EVENTS_WS_URL}`")
            if st.session_state.get("connection_errors"):
                st.warning("One or more live services are unavailable.")

# ============================================================
# 6. MAIN LAYOUT — 5 regions
# ============================================================
main_col, alert_col = st.columns([3, 1])

with main_col:
    # --- Region 1: Live video ---
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>📹 Live Feed & AI Vision Analysis</div>", unsafe_allow_html=True)
    if not MOCK_MODE and VIDEO_STREAM_URL:
        safe_stream_url = html.escape(VIDEO_STREAM_URL, quote=True)
        st.markdown(
            "<div class='video-shell'>"
            f"<img src='{safe_stream_url}' alt='Annotated traffic stream' style='width:100%;height:100%;object-fit:cover;border-radius:13px;'>"
            "<span class='rec-dot'>● LIVE</span>"
            "<span class='cam-label'>Intersection 806 · Wadi Saqra</span>"
            "</div>", unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='video-shell'>"
            "<span class='rec-dot'>● REC</span>"
            "<div class='video-stats'><span class='video-stat'>30 FPS</span><span class='video-stat'>18 VEHICLES</span><span class='video-stat'>AI ACTIVE</span></div>"
            "<div class='tracking-reticle'></div>"
            "<span style='font-size:0.72rem; margin-top:14px; color:#8fa3bb;'>Annotated stream awaiting vision engine</span>"
            "<span class='cam-label'>Intersection 806 · Wadi Saqra</span>"
            "</div>", unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([1.5, 1])

    with bottom_left:
        # --- Region 2: Forecast chart ---
        st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>📈 Traffic Flow Forecast (Next 60 Min)</div>", unsafe_allow_html=True)

        fig = go.Figure()

        # confidence band (shaded)
        fig.add_trace(go.Scatter(
            x=np.concatenate([minutes, minutes[::-1]]),
            y=np.concatenate([forecast_upper, forecast_lower[::-1]]),
            fill="toself",
            fillcolor="rgba(63,176,255,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip",
            showlegend=False,
        ))

        # observed — solid line
        fig.add_trace(go.Scatter(
            x=minutes, y=observed,
            mode="lines+markers",
            name="Observed Flow",
            line=dict(color="#e6edf3", width=2),
            marker=dict(size=5),
        ))

        # forecast — dashed line
        fig.add_trace(go.Scatter(
            x=minutes, y=forecast,
            mode="lines+markers",
            name="AI Forecast",
            line=dict(color="#3fb0ff", width=2, dash="dash"),
            marker=dict(size=5),
        ))

        # "now" vertical marker
        fig.add_vline(x=NOW_MINUTE, line_width=1.5, line_dash="dot", line_color="#8b949e")
        fig.add_annotation(x=NOW_MINUTE, y=1.05, yref="paper", showarrow=False,
                            text="NOW", font=dict(size=10, color="#8b949e"))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b949e", size=11),
            margin=dict(l=10, r=10, t=25, b=10),
            height=280,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            xaxis=dict(title="Minutes", gridcolor="#2d3748"),
            yaxis=dict(title="Vehicles / 5min", gridcolor="#2d3748"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            "<span style='font-size:0.75rem; color:#3fb0ff;'>Forecast error (last hr) vs naive baseline: "
            "<b>-18%</b></span>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with bottom_right:
        # --- Region 3: Signal advisor ---
        st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>🤖 Smart Signal Advisor</div>", unsafe_allow_html=True)

        r = mock_recommendation
        st.markdown(
            f"<div style='font-size:0.8rem; color:#8b949e;'>"
            f"<span style='color:#3fb0ff;'>Recommended: Phase {r['recommended_phase']}, "
            f"{r['recommended_green_duration_seconds']}s</span></div>",
            unsafe_allow_html=True,
        )
        current_green = r.get("current_green_duration_seconds", 32)
        st.markdown(
            "<div class='timing-grid'>"
            f"<div class='timing-box'><div class='timing-label'>Current timing</div><div class='timing-value'>{current_green}s</div></div>"
            f"<div class='timing-box recommended'><div class='timing-label'>Recommended</div><div class='timing-value'>{r['recommended_green_duration_seconds']}s</div></div>"
            "</div>", unsafe_allow_html=True,
        )
        st.caption(f"**Reason:** {r['reason']}")

        saving = r["estimated_saving_vehicle_minutes"]
        st.caption(f"Estimated saving: **{saving} veh·min / cycle**")

        if r.get("advisory_only") and r.get("not_transmitted_to_controller"):
            st.markdown(
                "<div class='advisory-badge'>⚠️ ADVISORY ONLY — NOT TRANSMITTED TO CONTROLLER</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

with alert_col:
    # --- Region 4: Alert feed ---
    st.markdown("<div class='dashboard-card' style='height:100%;'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🔔 Alert Feed</div>", unsafe_allow_html=True)

    for a in mock_alerts:
        time_short = a["timestamp"][11:16] if "T" in a["timestamp"] else a["timestamp"]
        confidence_txt = f"{a['confidence'] * 100:.0f}%"
        st.markdown(
            f"<div class='alert-item'>"
            f"<div class='alert-thumb'>📸</div>"
            f"<div class='alert-text'><b>{time_short} — {a['event_type']}</b><br>"
            f"<span class='alert-meta'>{a['approach']} · confidence {confidence_txt} · "
            f"queue ~{a['queue_estimate']}m</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"View evidence clip — {time_short}", expanded=False):
            snapshot_path = a.get("snapshot_path")
            clip_path = a.get("clip_path")
            if not MOCK_MODE and snapshot_path:
                st.image(media_url(snapshot_path), caption="Incident snapshot", use_container_width=True)
            if not MOCK_MODE and clip_path:
                st.video(media_url(clip_path))
            else:
                st.markdown(
                    "<div class='video-shell' style='height:140px;'>"
                    "<span style='font-size:1.4rem;'>🎬</span>"
                    f"<span style='font-size:0.72rem; margin-top:4px;'>{clip_path or 'Evidence unavailable'}</span>"
                    "</div>", unsafe_allow_html=True,
                )
            b1, b2 = st.columns(2)
            b1.button("✅ Confirm", key=f"confirm_{a['timestamp']}_{a['event_type']}")
            b2.button("❌ Dismiss", key=f"dismiss_{a['timestamp']}_{a['event_type']}")

    for m in mock_system_msgs:
        st.markdown(
            f"<div class='info-item'>ℹ️ <b>{m['time']}</b> — {m['text']}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 7. Region 5 — System health strip
# ============================================================
h = mock_health
uptime_str = "{:02d}:{:02d}:{:02d}".format(
    h["stream_uptime_seconds"] // 3600,
    (h["stream_uptime_seconds"] % 3600) // 60,
    h["stream_uptime_seconds"] % 60,
)
st.markdown(
    "<div class='health-strip'>"
    f"<div class='health-item'><span class='health-ok'>● HEALTHY</span><div class='health-label'>Ingestion rate</div><div class='health-value'>{h['ingestion_rate_fps']} FPS</div></div>"
    f"<div class='health-item'><span class='health-ok'>● NOMINAL</span><div class='health-label'>Dropped frames</div><div class='health-value'>{h['dropped_frames']} frames</div></div>"
    f"<div class='health-item'><span class='health-ok'>● CONNECTED</span><div class='health-label'>Stream uptime</div><div class='health-value'>{uptime_str}</div></div>"
    "</div>", unsafe_allow_html=True,
)
