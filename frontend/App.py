"""VISTA operator dashboard presentation layer.

Configuration and backend adapters live in dedicated modules so this entry point
stays focused on the Streamlit page that operators and judges interact with.
"""

import html

import numpy as np
import plotly.graph_objects as go
import streamlit as st

try:
    from frontend.config import (
        API_BASE,
        EVENTS_WS_URL,
        FAVICON_PATH,
        LOCAL_DEMO_VIDEO_PATH,
        LOGO_DATA_URI,
        MOCK_MODE,
        VIDEO_STREAM_URL,
        VISION_PREVIEW_DATA_URI,
    )
    from frontend.data_service import (
        fetch_forecast,
        fetch_health,
        fetch_incidents,
        fetch_recommendation,
        format_video_timestamp,
        incident_media_source,
        incident_video_offset,
        normalize_incident,
        poll_websocket_event,
        submit_incident_review,
    )
    from frontend.styles import load_css
except ModuleNotFoundError as exc:
    if exc.name != "frontend":
        raise
    from config import (
        API_BASE,
        EVENTS_WS_URL,
        FAVICON_PATH,
        LOCAL_DEMO_VIDEO_PATH,
        LOGO_DATA_URI,
        MOCK_MODE,
        VIDEO_STREAM_URL,
        VISION_PREVIEW_DATA_URI,
    )
    from data_service import (
        fetch_forecast,
        fetch_health,
        fetch_incidents,
        fetch_recommendation,
        format_video_timestamp,
        incident_media_source,
        incident_video_offset,
        normalize_incident,
        poll_websocket_event,
        submit_incident_review,
    )
    from styles import load_css


# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="VISTA | Traffic Advisor",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. DESIGN SYSTEM
# One accent color for ALERTS, one accent color for FORECASTS.
# Everything else stays neutral (dark operator-console palette).
# ============================================================
st.markdown(load_css(), unsafe_allow_html=True)

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
    mock_alerts = [normalize_incident(live_event), *mock_alerts]
mock_system_msgs = [
    {"time": "16:30", "text": "Connected to synthetic SCATS database successfully."},
]

minutes, observed, forecast, forecast_upper, forecast_lower, accuracy_metrics = fetch_forecast()
observed_minutes = [minutes[i] for i, value in enumerate(observed) if value is not None]
NOW_MINUTE = max(observed_minutes, default=0)

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
if "video_start_seconds" not in st.session_state:
    st.session_state.video_start_seconds = 0
if "video_cue_label" not in st.session_state:
    st.session_state.video_cue_label = "Start of recording"

with st.sidebar:
    st.markdown("### VISTA Operations")
    st.caption("Visual Intelligent Smart Traffic Advisor")
    mode_label = "DEMO / MOCK" if MOCK_MODE else "LIVE SERVICES"
    st.caption(f"Data mode: **{mode_label}**")
    st.selectbox("Select Lane Camera / Traffic Video:", ["Intersection 806 — Wadi Saqra (Live Demo)"])

    st.markdown("---")
    st.markdown("### Demo Control")
    c1, c2, c3 = st.columns(3)
    if c1.button("Play", icon=":material/play_arrow:", width="stretch"):
        st.session_state.playback = "playing"
    if c2.button("Pause", icon=":material/pause:", width="stretch"):
        st.session_state.playback = "paused"
    if c3.button("Jump", icon=":material/emergency:", width="stretch"):
        st.session_state.playback = "jumped_to_incident"
        if mock_alerts:
            target_incident = mock_alerts[0]
            st.session_state.video_start_seconds = incident_video_offset(target_incident)
            st.session_state.video_cue_label = (
                f"{target_incident['event_type']} · {target_incident['approach']}"
            )

    st.caption(
        f"Status: **{st.session_state.playback.replace('_', ' ').title()}**  \n"
        f"Cue: **{st.session_state.video_cue_label}** "
        f"({format_video_timestamp(st.session_state.video_start_seconds)})"
    )
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
    elif LOCAL_DEMO_VIDEO_PATH.exists():
        st.video(
            str(LOCAL_DEMO_VIDEO_PATH),
            start_time=st.session_state.video_start_seconds,
            autoplay=st.session_state.playback in {"playing", "jumped_to_incident"},
            loop=True,
            muted=True,
            width="stretch",
        )
        st.caption("M1 annotated demo · 1280×720 · privacy-safe recorded feed")
    else:
        preview_image = (
            f"<img src='{VISION_PREVIEW_DATA_URI}' alt='M1 zone configuration preview' "
            "style='position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.58;'>"
            if VISION_PREVIEW_DATA_URI else ""
        )
        st.markdown(
            "<div class='video-shell'>"
            f"{preview_image}"
            "<span class='rec-dot'>● REC</span>"
            "<div class='video-stats'><span class='video-stat'>30 FPS</span><span class='video-stat'>18 VEHICLES</span><span class='video-stat'>AI ACTIVE</span></div>"
            "<div class='tracking-reticle'></div>"
            "<span style='font-size:0.72rem; margin-top:14px; color:#c8d7eb;position:relative;'>M1 zone output · annotated stream adapter ready</span>"
            "<span class='cam-label'>Intersection 806 · Wadi Saqra</span>"
            "</div>", unsafe_allow_html=True,
        )

    bottom_left, bottom_right = st.columns([1.5, 1])

    with bottom_left:
        # --- Region 2: Forecast chart ---
        st.markdown("<div class='card-title'>📈 Traffic Flow Forecast (Next 60 Min)</div>", unsafe_allow_html=True)

        fig = go.Figure()

        # confidence band (shaded)
        band_mask = np.array(
            [
                upper is not None and lower is not None
                for upper, lower in zip(forecast_upper, forecast_lower)
            ],
            dtype=bool,
        )
        band_minutes = minutes[band_mask]
        band_upper = forecast_upper[band_mask]
        band_lower = forecast_lower[band_mask]
        fig.add_trace(go.Scatter(
            x=np.concatenate([band_minutes, band_minutes[::-1]]),
            y=np.concatenate([band_upper, band_lower[::-1]]),
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        if accuracy_metrics and any(key in accuracy_metrics for key in ("15m", "30m", "60m")):
            parts = []
            for horizon in ("15m", "30m", "60m"):
                metrics = accuracy_metrics.get(horizon)
                if metrics:
                    parts.append(
                        f"{horizon}: AI <b>{metrics['ai_mape']:.2f}%</b> vs "
                        f"baseline {metrics['baseline_mape']:.2f}% "
                        f"<span style='color:#8ea0b8'>(RMSE {metrics['ai_rmse']:.2f})</span>"
                    )
            accuracy_text = " &nbsp;·&nbsp; ".join(parts)
        elif accuracy_metrics:
            ai_error = accuracy_metrics.get("ai_forecast_error_1h", "Pending")
            baseline_error = accuracy_metrics.get("naive_baseline_error", "Pending")
            accuracy_status = accuracy_metrics.get("status", "Evaluation available")
            accuracy_text = f"AI error: <b>{ai_error}</b> · Baseline: <b>{baseline_error}</b> · {accuracy_status}"
        elif MOCK_MODE:
            accuracy_text = "Demo model improvement vs naive baseline: <b>18%</b>"
        else:
            accuracy_text = "Forecast accuracy unavailable"
        st.markdown(
            f"<span style='font-size:0.75rem; color:#3fb0ff;'>{accuracy_text}</span>",
            unsafe_allow_html=True,
        )

    with bottom_right:
        # --- Region 3: Signal advisor ---
        st.markdown("<div class='card-title'>🤖 Smart Signal Advisor</div>", unsafe_allow_html=True)

        r = mock_recommendation
        recommendation_available = bool(r.get("recommended_green_duration_seconds"))
        if not recommendation_available:
            st.warning(
                "Signal recommendation is temporarily unavailable.",
                icon=":material/warning:",
            )
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

        assumptions = r.get("assumptions", [])
        if assumptions:
            assumption_items = (
                [f"{key.replace('_', ' ').title()}: {value}" for key, value in assumptions.items()]
                if isinstance(assumptions, dict)
                else assumptions
            )
            assumptions_html = "<br>".join(
                f"• {html.escape(str(assumption))}" for assumption in assumption_items
            )
            st.markdown(
                f"<div class='assumption-note'><b>Model assumptions</b><br>{assumptions_html}</div>",
                unsafe_allow_html=True,
            )

with alert_col:
    # --- Region 4: Alert feed ---
    st.markdown("<div class='card-title'>🔔 Alert Feed</div>", unsafe_allow_html=True)

    if not mock_alerts:
        st.info(
            "No incidents are available for operator review.",
            icon=":material/info:",
        )

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
            event_id = a["event_id"]
            st.caption(
                f"Event ID: `{event_id}` · Approach: **{a['approach']}** · "
                f"Confidence: **{confidence_txt}** · Queue: **~{a['queue_estimate']} m**"
            )
            snapshot_path = a.get("snapshot_path")
            clip_path = a.get("clip_path")
            snapshot_source = incident_media_source(a, "snapshot_path")
            clip_source = incident_media_source(a, "clip_path")
            if snapshot_source:
                st.image(snapshot_source, caption="Incident snapshot", width="stretch")
            if clip_source:
                st.video(clip_source)
            else:
                st.markdown(
                    "<div class='video-shell' style='height:140px;'>"
                    "<span style='font-size:1.4rem;'>🎬</span>"
                    f"<span style='font-size:0.72rem; margin-top:4px;'>{clip_path or 'Evidence unavailable'}</span>"
                    "</div>", unsafe_allow_html=True,
                )
            b1, b2 = st.columns(2)
            if b1.button(
                "Confirm",
                icon=":material/check_circle:",
                key=f"confirm_{event_id}",
                width="stretch",
            ):
                success, message = submit_incident_review(event_id, "confirmed")
                if success:
                    st.success(message, icon=":material/check_circle:")
                else:
                    st.error(message, icon=":material/error:")
            if b2.button(
                "Dismiss",
                icon=":material/cancel:",
                key=f"dismiss_{event_id}",
                width="stretch",
            ):
                success, message = submit_incident_review(event_id, "dismissed")
                if success:
                    st.success(message, icon=":material/check_circle:")
                else:
                    st.error(message, icon=":material/error:")

            saved_decision = st.session_state.get("incident_reviews", {}).get(event_id)
            if saved_decision:
                st.caption(f"Operator decision: **{saved_decision.title()}**")

    for m in mock_system_msgs:
        st.markdown(
            f"<div class='info-item'>ℹ️ <b>{m['time']}</b> — {m['text']}</div>",
            unsafe_allow_html=True,
        )

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
