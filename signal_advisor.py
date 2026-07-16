"""Explainable, advisory-only traffic-signal timing recommendations."""

from __future__ import annotations

from pathlib import Path
import math
import pandas as pd


PHASE_APPROACHES = {
    1: ("North_Arar_St", "South_Arar_St"),
    2: ("East_Approach", "West_Approach"),
}
LANES = {
    "North_Arar_St": 3,
    "South_Arar_St": 3,
    "East_Approach": 2,
    "West_Approach": 2,
}
DEFAULT_GREENS = {1: 32, 2: 28}
SATURATION_FLOW_PER_LANE = 1800
LOST_TIME_PER_PHASE = 6
MIN_GREEN = 15
MIN_CYCLE = 60
MAX_CYCLE = 120


def read_current_greens(path="parsed_signal_phase.csv"):
    """Read the last complete green duration for every phase in the phase log."""
    current = dict(DEFAULT_GREENS)
    source = {phase: "default (phase absent from log)" for phase in current}
    phase_log = Path(path)
    if not phase_log.exists():
        return current, source

    events = pd.read_csv(phase_log)
    events["timestamp"] = pd.to_datetime(events["timestamp"], errors="coerce")
    events = events.dropna(subset=["timestamp"]).sort_values("timestamp")
    for phase, rows in events.groupby("phase_number"):
        start = None
        durations = []
        for row in rows.itertuples():
            if row.light_state == "GREEN":
                start = row.timestamp
            elif row.light_state in ("YELLOW", "RED") and start is not None:
                durations.append((row.timestamp - start).total_seconds())
                start = None
        if durations and int(phase) in current:
            current[int(phase)] = int(round(durations[-1]))
            source[int(phase)] = "latest complete interval in phase log"
    return current, source


def _uniform_delay_seconds(flow, saturation, green, cycle):
    """Webster uniform control delay, capped just below saturation."""
    green_ratio = green / cycle
    degree = flow / max(saturation * green_ratio, 1)
    degree = min(max(degree, 0), 0.99)
    return 0.5 * cycle * (1 - green_ratio) ** 2 / max(1 - degree * green_ratio, 0.01)


def _total_delay_vehicle_minutes(flows, greens, cycle):
    total = 0.0
    for approach, flow in flows.items():
        phase = next(p for p, approaches in PHASE_APPROACHES.items() if approach in approaches)
        saturation = SATURATION_FLOW_PER_LANE * LANES[approach]
        delay = _uniform_delay_seconds(flow, saturation, greens[phase], cycle)
        vehicles_per_cycle = flow * cycle / 3600
        total += delay * vehicles_per_cycle / 60
    return total


def make_recommendation(predicted_counts, observed_counts, timestamp, phase_log_path="parsed_signal_phase.csv"):
    """Build one recommendation from 30-minute-horizon 15-minute counts.

    Counts are converted to hourly flow. Opposing approaches run together, so the
    larger flow ratio in each phase is its critical flow ratio.
    """
    missing = set(LANES).difference(predicted_counts)
    if missing:
        raise ValueError(f"Missing predicted approaches: {', '.join(sorted(missing))}")

    flows = {name: max(float(count), 0) * 4 for name, count in predicted_counts.items()}
    critical = {}
    for phase, approaches in PHASE_APPROACHES.items():
        critical[phase] = max(
            flows[a] / (SATURATION_FLOW_PER_LANE * LANES[a]) for a in approaches
        )
    total_ratio = sum(critical.values())
    effective_ratio = min(total_ratio, 0.90)
    lost_time = LOST_TIME_PER_PHASE * len(PHASE_APPROACHES)
    webster_cycle = (1.5 * lost_time + 5) / max(1 - effective_ratio, 0.10)
    cycle = int(round(min(MAX_CYCLE, max(MIN_CYCLE, webster_cycle))))

    available_green = cycle - lost_time
    ratio_sum = max(sum(critical.values()), 0.001)
    recommended = {
        phase: max(MIN_GREEN, int(round(available_green * ratio / ratio_sum)))
        for phase, ratio in critical.items()
    }
    # Preserve the available green after minimums and rounding.
    difference = available_green - sum(recommended.values())
    recommended[max(critical, key=critical.get)] += difference

    current, timing_source = read_current_greens(phase_log_path)
    current_cycle = sum(current.values()) + lost_time
    current_delay = _total_delay_vehicle_minutes(flows, current, current_cycle)
    proposed_delay = _total_delay_vehicle_minutes(flows, recommended, cycle)
    saving = max(0.0, current_delay - proposed_delay)

    phase = max(critical, key=critical.get)
    lead_approach = max(PHASE_APPROACHES[phase], key=lambda a: flows[a])
    observed = max(float(observed_counts.get(lead_approach, 0)), 0)
    growth = 0 if observed == 0 else round((predicted_counts[lead_approach] / observed - 1) * 100)
    direction = "rises" if growth >= 0 else "falls"
    when = pd.Timestamp(timestamp)
    reason = (
        f"Predicted demand on {lead_approach} {direction} {abs(growth)} percent by "
        f"{when.strftime('%H:%M')}. Recommend changing phase {phase} green from "
        f"{current[phase]} to {recommended[phase]} seconds. Estimated reduction in "
        f"total intersection delay: approximately {saving:.2f} vehicle-minutes per cycle."
    )

    timestamp_iso = when.isoformat()
    if when.tzinfo is None:
        timestamp_iso += "Z"
    else:
        timestamp_iso = timestamp_iso.replace("+00:00", "Z")
    response = {
        "timestamp": timestamp_iso,
        "forecast_horizon_minutes": 30,
        "recommended_phase": phase,
        "reason": reason,
        "current_cycle_length_seconds": current_cycle,
        "recommended_cycle_length_seconds": cycle,
        "current_green_seconds": {str(k): v for k, v in current.items()},
        "recommended_green_seconds": {str(k): v for k, v in recommended.items()},
        "green_delta_seconds": {str(k): recommended[k] - current[k] for k in current},
        "critical_flow_ratios": {str(k): round(v, 4) for k, v in critical.items()},
        "estimated_saving_vehicle_minutes_per_cycle": round(saving, 2),
        "delay_formula": "sum[Webster uniform delay (s/veh) * vehicles per cycle] / 60; saving = current - recommended",
        "assumptions": {
            "forecast_count_interval_minutes": 15,
            "saturation_flow_vehicle_per_hour_per_lane": SATURATION_FLOW_PER_LANE,
            "lanes_per_approach": LANES,
            "lost_time_seconds_per_phase": LOST_TIME_PER_PHASE,
            "phase_approach_mapping": {str(k): list(v) for k, v in PHASE_APPROACHES.items()},
            "current_timing_source": {str(k): v for k, v in timing_source.items()},
            "cycle_length_clamp_seconds": [MIN_CYCLE, MAX_CYCLE],
            "minimum_green_seconds": MIN_GREEN,
        },
        "advisory_only": True,
        "not_transmitted_to_controller": True,
    }
    # Backward-compatible aliases consumed by the current M3 dashboard. Keep
    # the richer per-phase fields above as the canonical Day 3 contract.
    response["current_green_duration_seconds"] = current[phase]
    response["recommended_green_duration_seconds"] = recommended[phase]
    response["estimated_saving_vehicle_minutes"] = response[
        "estimated_saving_vehicle_minutes_per_cycle"
    ]
    return response
