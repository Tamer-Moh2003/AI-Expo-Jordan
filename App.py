import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# ============================================================
# 0. DATA SOURCE LAYER
# Flip MOCK_MODE to False once M2's backend is running.
# Every function below returns data in the SAME shape whether
# it comes from mock data or the real API -- so nothing else
# in this file needs to change when you swap it.
# ============================================================
MOCK_MODE = True
API_BASE = "http://localhost:8000"  # ask M4/M2 for the real host:port


def fetch_health():
    # Matches api_contract.json "GET /health" exactly. Frozen contract.
    if MOCK_MODE:
        return {"ingestion_rate_fps": 30, "dropped_frames": 2, "stream_uptime_seconds": 3600}
    try:
        r = requests.get(f"{API_BASE}/health", timeout=2)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        st.error("⚠️ Could not reach /health — falling back to last known values.")
        return {"ingestion_rate_fps": 0, "dropped_frames": 0, "stream_uptime_seconds": 0}


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
    r = requests.get(f"{API_BASE}/recommendation", timeout=2)
    r.raise_for_status()
    return r.json()


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
    r = requests.get(f"{API_BASE}/incidents", timeout=2)
    r.raise_for_status()
    return r.json()


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
        ]
    else:
        r = requests.get(f"{API_BASE}/forecast", timeout=2)
        r.raise_for_status()
        raw = r.json()

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
    page_title="STMS Console",
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
        --bg-main: #0d1117;
        --bg-card: #161b22;
        --border-color: #2d3748;
        --text-primary: #e6edf3;
        --text-muted: #8b949e;

        --accent-alert: #ff4d4f;      /* single color for ALL alert states */
        --accent-alert-bg: rgba(255, 77, 79, 0.10);
        --accent-forecast: #3fb0ff;   /* single color for ALL forecast/AI states */
        --accent-forecast-bg: rgba(63, 176, 255, 0.10);

        --accent-safe: #2ecc71;       /* used only for the advisory-only guard rail */
    }

    .stApp { background-color: var(--bg-main); }
    .block-container { padding-top: 0.8rem; padding-bottom: 0rem; max-width: 100%; }
    .stDeployButton, #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background: transparent;
        height: 2.2rem;
    }

    .dashboard-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 12px;
        height: 100%;
    }
    .card-title {
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 8px;
    }

    /* --- Demo mode banner --- */
    .demo-banner {
        background-color: #1f2937;
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--text-muted);
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 0.78rem;
        color: var(--text-muted);
        text-align: center;
        margin-bottom: 10px;
    }

    /* --- Video placeholder (no external network dependency) --- */
    .video-shell {
        background: repeating-linear-gradient(45deg, #11151c, #11151c 10px, #161b22 10px, #161b22 20px);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        height: 340px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--text-muted);
        position: relative;
    }
    .video-shell .rec-dot {
        position: absolute; top: 12px; left: 14px;
        color: var(--accent-alert); font-size: 0.75rem; font-weight: 700;
    }
    .video-shell .cam-label {
        position: absolute; bottom: 12px; left: 14px;
        font-size: 0.72rem; color: var(--text-muted);
    }

    /* --- Alert feed items --- */
    .alert-item {
        background-color: var(--accent-alert-bg);
        border-left: 3px solid var(--accent-alert);
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
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
mock_system_msgs = [
    {"time": "16:30", "text": "Connected to synthetic SCATS database successfully."},
]

minutes, observed, forecast, forecast_upper, forecast_lower = fetch_forecast()
NOW_MINUTE = 25  # vertical "now" marker — later derive this from the live clock/API

# ============================================================
# 4. HEADER
# ============================================================
st.markdown(
    "<div class='demo-banner'>🛡️ Demo mode — recorded video and synthetic SCATS logs in GAM native format</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h2 style='text-align:center; margin:0; color:#e6edf3;'>🚦 Smart Traffic Management System (STMS)</h2>"
    "<p style='text-align:center; color:#8b949e; margin-top:2px; font-size:0.85rem;'>"
    "Amman Municipality (GAM) — Real-Time Operator Control Console</p>",
    unsafe_allow_html=True,
)

# ============================================================
# 5. SIDEBAR — demo control (functional via session_state)
# ============================================================
if "playback" not in st.session_state:
    st.session_state.playback = "paused"

with st.sidebar:
    st.markdown("### 🛠️ Control Options")
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

# ============================================================
# 6. MAIN LAYOUT — 5 regions
# ============================================================
main_col, alert_col = st.columns([3, 1])

with main_col:
    # --- Region 1: Live video ---
    st.markdown("<div class='dashboard-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>📹 Live Feed & AI Vision Analysis</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='video-shell'>"
        "<span class='rec-dot'>● REC</span>"
        "<span style='font-size:2rem;'>🎥</span>"
        "<span style='font-size:0.8rem; margin-top:6px;'>Streaming — tracking vehicles…</span>"
        "<span class='cam-label'>Intersection 806 · Wadi Saqra</span>"
        "</div>",
        unsafe_allow_html=True,
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
        st.metric(
            label="Recommended Green Duration",
            value=f"{r['recommended_green_duration_seconds']}s",
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
            st.markdown(
                "<div class='video-shell' style='height:140px;'>"
                "<span style='font-size:1.4rem;'>🎬</span>"
                f"<span style='font-size:0.72rem; margin-top:4px;'>{a['clip_path']}</span>"
                "</div>",
                unsafe_allow_html=True,
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
st.markdown("---")
h = mock_health
uptime_str = "{:02d}:{:02d}:{:02d}".format(
    h["stream_uptime_seconds"] // 3600,
    (h["stream_uptime_seconds"] % 3600) // 60,
    h["stream_uptime_seconds"] % 60,
)
h1, h2, h3 = st.columns(3)
h1.metric(label="🖥️ Ingestion Rate", value=f"{h['ingestion_rate_fps']} FPS")
h2.metric(label="⚠️ Dropped Frames", value=f"{h['dropped_frames']} frames")
h3.metric(label="⏱️ Stream Uptime", value=uptime_str)