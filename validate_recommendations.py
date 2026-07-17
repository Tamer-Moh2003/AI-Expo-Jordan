"""Day 4 sanity checks for signal-advisor recommendations across the demo day."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

import api
from signal_advisor import LOST_TIME_PER_PHASE, MAX_CYCLE, MIN_CYCLE, MIN_GREEN, PHASE_APPROACHES


SCENARIOS = {
    "weekday_morning": "2026-06-15T07:30:00",
    "weekday_am_peak": "2026-06-15T08:30:00",
    "weekday_midday": "2026-06-15T12:30:00",
    "weekday_pm_peak": "2026-06-15T17:30:00",
    "weekday_evening": "2026-06-15T21:00:00",
    "friday_midday": "2026-06-19T12:30:00",
    "weekend_evening": "2026-06-20T18:00:00",
}


def validate_payload(payload):
    errors = []
    cycle = payload["recommended_cycle_length_seconds"]
    greens = {int(phase): value for phase, value in payload["recommended_green_seconds"].items()}
    lost_time = LOST_TIME_PER_PHASE * len(PHASE_APPROACHES)

    if not MIN_CYCLE <= cycle <= MAX_CYCLE:
        errors.append(f"cycle {cycle} outside [{MIN_CYCLE}, {MAX_CYCLE}]")
    if any((not math.isfinite(value) or value < MIN_GREEN) for value in greens.values()):
        errors.append(f"green below {MIN_GREEN}s or non-finite: {greens}")
    if sum(greens.values()) + lost_time != cycle:
        errors.append("green sum plus lost time does not equal cycle")
    saving = payload["estimated_saving_vehicle_minutes_per_cycle"]
    if not math.isfinite(saving) or saving < 0:
        errors.append("delay saving is negative or non-finite")
    if not payload.get("advisory_only") or not payload.get("not_transmitted_to_controller"):
        errors.append("mandatory safety boundary is missing")
    if not math.isfinite(payload["raw_webster_cycle_length_seconds"]):
        errors.append("raw Webster cycle is non-finite")
    if set(greens) != set(PHASE_APPROACHES):
        errors.append("recommendation does not cover every configured phase")
    return errors


def main():
    rows = []
    details = {}
    for scenario, at in SCENARIOS.items():
        payload = api.live_recommendation(at)
        errors = validate_payload(payload)
        details[scenario] = payload
        rows.append({
            "scenario": scenario,
            "requested_time": at,
            "forecast_time": payload["timestamp"],
            "raw_webster_cycle_seconds": payload["raw_webster_cycle_length_seconds"],
            "recommended_cycle_seconds": payload["recommended_cycle_length_seconds"],
            "phase_1_green_seconds": payload["recommended_green_seconds"]["1"],
            "phase_2_green_seconds": payload["recommended_green_seconds"]["2"],
            "estimated_saving_vehicle_minutes_per_cycle": payload[
                "estimated_saving_vehicle_minutes_per_cycle"
            ],
            "recommended_phase": payload["recommended_phase"],
            "passed": not errors,
            "errors": "; ".join(errors),
        })

    results = pd.DataFrame(rows)
    results.to_csv("recommendation_sanity_check.csv", index=False)
    Path("recommendation_sanity_details.json").write_text(
        json.dumps(details, indent=2), encoding="utf-8"
    )
    print(results.to_string(index=False))
    if not results["passed"].all():
        raise SystemExit("One or more recommendation scenarios failed")
    print(f"\nAll {len(results)} recommendation scenarios passed.")


if __name__ == "__main__":
    main()
