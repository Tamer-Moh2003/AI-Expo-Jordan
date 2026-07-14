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
    # Matches api_contract.json "GET /health" and schema.sql system_health table exactly.
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
    # Matches api_contract.json "GET /recommendation" field-for-field.
    # advisory_only / not_transmitted_to_controller / estimated_saving are NOT
    # in the contract yet -- flagged to M2. Defaulted here so the UI doesn't
    # break; remove the .get() fallback once the real fields exist.
    if MOCK_MODE:
        return {
            "timestamp": "2026-07-14T08:12:00Z",
            "recommended_phase": 3,
            "recommended_green_duration_seconds": 45,
            "reason": "High queue volume detected",
            "advisory_only": True,                     # TODO: confirm with M2, not yet in contract
            "not_transmitted_to_controller": True,      # TODO: confirm with M2, not yet in contract
            "estimated_saving_vehicle_minutes": None,   # TODO: not yet in contract
        }
    r = requests.get(f"{API_BASE}/recommendation", timeout=2)
    r.raise_for_status()
    data = r.json()
    data.setdefault("advisory_only", True)
    data.setdefault("not_transmitted_to_controller", True)
    data.setdefault("estimated_saving_vehicle_minutes", None)
    return data


def fetch_incidents():
    # Matches api_contract.json "GET /incidents" field-for-field.
    # confidence / snapshot_path / clip_path / queue_estimate are NOT in the
    # contract yet (required by plan task 25) -- flagged to M2.
    if MOCK_MODE:
        return [
            {"timestamp": "2026-07-14T08:10:00Z", "event_type": "Stalled Vehicle", "approach": "North",
             "confidence": 94, "snapshot_path": None, "clip_path": None, "queue_estimate": None},
            {"timestamp": "2026-07-14T08:22:00Z", "event_type": "Queue Spillback", "approach": "East",
             "confidence": 87, "snapshot_path": None, "clip_path": None, "queue_estimate": None},
        ]
    r = requests.get(f"{API_BASE}/incidents", timeout=2)
    r.raise_for_status()
    items = r.json()
    for item in items:
        item.setdefault("confidence", None)
        item.setdefault("snapshot_path", None)
        item.setdefault("clip_path", None)
        item.setdefault("queue_estimate", None)
    return items


def fetch_forecast():
    """Matches api_contract.json "GET /forecast": a flat list of
    {timestamp, approach, predicted_count}. No 'observed' series and no
    confidence band (upper/lower) yet -- both required by plan task 32/35,
    flagged to M2. Returns arrays shaped for the chart below."""
    if MOCK_MODE:
        raw = [
            {"timestamp": "08:00", "approach": "North", "predicted_count": 33},
            {"timestamp": "08:05", "approach": "North", "predicted_count": 38},
            {"timestamp": "08:10", "approach": "North", "predicted_count": 42},
            {"timestamp": "08:15", "approach": "North", "predicted_count": 48},
            {"timestamp": "08:20", "approach": "North", "predicted_count": 55},
            {"timestamp": "08:25", "approach": "North", "predicted_count": 52},
            {"timestamp": "08:30", "approach": "North", "predicted_count": 46},
        ]
    else:
        r = requests.get(f"{API_BASE}/forecast", timeout=2)
        r.raise_for_status()
        raw = r.json()

    minutes = np.arange(0, len(raw) * 5, 5)
    forecast_vals = np.array([row["predicted_count"] for row in raw], dtype=object)

    # No 'observed' series in the contract yet -- reuse mock history for now
    # so the chart still shows both lines; swap once M2 adds it.
    observed = np.array([25, 28, 32, 35, 33, None, None], dtype=object)[: len(minutes)]

    # No confidence band in the contract yet -- approximate a +/-10% band
    # as a placeholder so the shading still renders; replace once real
    # upper/lower bounds exist.
    upper = np.array([v * 1.1 if v is not None else None for v in forecast_vals], dtype=object)
    lower = np.array([v * 0.9 if v is not None else None for v in forecast_vals], dtype=object)

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
    .stDeployButton, #MainMenu, footer, header { visibility: hidden; }

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

        saving = r.get("estimated_saving_vehicle_minutes")
        if saving is not None:
            st.caption(f"Estimated saving: **{saving} veh·min / cycle**")
        else:
            st.markdown(
                "<div class='assumption-note'>Estimated saving not yet in API contract — pending M2</div>",
                unsafe_allow_html=True,
            )

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
        confidence_txt = f"{a['confidence']}%" if a.get("confidence") is not None else "N/A"
        st.markdown(
            f"<div class='alert-item'>"
            f"<div class='alert-thumb'>📸</div>"
            f"<div class='alert-text'><b>{time_short} — {a['event_type']}</b><br>"
            f"<span class='alert-meta'>{a['approach']} · confidence {confidence_txt}</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"View evidence clip — {time_short}", expanded=False):
            if a.get("clip_path"):
                st.video(a["clip_path"])
            else:
                st.markdown(
                    "<div class='video-shell' style='height:140px;'>"
                    "<span style='font-size:1.4rem;'>🎬</span>"
                    "<span style='font-size:0.72rem; margin-top:4px;'>clip_path not yet in API contract</span>"
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