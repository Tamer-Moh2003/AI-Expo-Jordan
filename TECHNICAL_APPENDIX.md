# VISTA M2 Technical Appendix

## 1. Scope and Safety Boundary

The M2 subsystem parses and generates SCATS-format traffic data, engineers forecasting features, trains LightGBM count models, evaluates them against a transparent baseline, serves forecasts, and produces explainable signal-timing advice. The prototype is decision support only:

```json
{
  "advisory_only": true,
  "not_transmitted_to_controller": true
}
```

No recommendation is transmitted to a physical traffic controller.

## 2. Data Sources and Honesty Statement

The current evaluation uses 90 days of synthetic 15-minute SCATS-format detector counts for 22 detectors on four approaches at Wadi Saqra Intersection 806. Synthetic profiles include time-of-day, weekday/weekend and Friday patterns, Poisson variation, and injected anomalies. Signal timing is read from the available phase log when possible. Phase 1 is absent from the current log and therefore uses an explicitly labelled 32-second default.

Results demonstrate the reproducibility and internal performance of the proof-of-concept pipeline. They are not a claim of verified accuracy or delay reduction on live GAM data.

## 3. Logical Data Schema

| Entity | Key fields | Purpose |
|---|---|---|
| `detectors` | `id`, `location_name`, `approach` | Detector-to-approach mapping |
| `counts` | `timestamp`, `detector_id`, `vehicle_count` | Tidy 15-minute detector counts |
| `signal_events` | `timestamp`, `intersection_id`, `phase_number`, `light_state` | Signal phase transitions |
| `incidents` | timestamp, type, approach, confidence, evidence paths | Vision incident events |
| `forecasts` | timestamp, approach, predicted count, bounds | Future traffic demand |
| `recommendations` | timestamp, timing plan, reason, benefit | Advisory signal plan |
| `system_health` | ingestion rate, dropped frames, uptime | Operational monitoring |

The API contract is maintained in `api_contract.json`.

## 4. Forecast Feature Engineering

Model inputs are constructed by the shared `forecasting_features.py` module for both training and serving:

- Current approach count.
- Lags 1, 2, 3, and 4: 15–60 minutes of recent history.
- Lag 96: the same slot one day earlier.
- Weekly and neighbouring-weekly lags around 672 intervals.
- Rolling means over 4, 8, 16, and 96 intervals.
- Quarter-hour of day and day of week.
- Weekend and holiday flags.
- Categorical approach identifier.

Rolling statistics are shifted before calculation. Targets are shifted forward only after features are constructed, preventing future observations from entering model inputs.

## 5. Baseline

The naive benchmark predicts the target slot using the same approach and 15-minute slot from the previous week:

\[
\hat{y}^{baseline}_{t+h}=y_{t+h-672}
\]

where 672 is seven days multiplied by 96 quarter-hour intervals per day.

## 6. LightGBM Training

Separate LightGBM regressors are trained for 15-, 30-, and 60-minute horizons. The model uses a Poisson objective because traffic counts are non-negative count data. Training is chronological: the final 14 days are held out as the test set, and no random split is used.

Model files and metadata:

```text
model_15m.txt / model_15m_metadata.json
model_30m.txt / model_30m_metadata.json
model_60m.txt / model_60m_metadata.json
```

## 7. Evaluation Metrics

MAPE is calculated with a denominator floor of one:

\[
MAPE=\frac{100}{n}\sum\left|\frac{y-\hat{y}}{\max(y,1)}\right|
\]

RMSE is:

\[
RMSE=\sqrt{\frac{1}{n}\sum(y-\hat{y})^2}
\]

Final per-approach results are in `forecast_evaluation.csv`; horizon summaries are in `forecast_evaluation_summary.csv`. LightGBM must have lower MAPE and RMSE than the baseline at every horizon and approach for validation to pass.

## 8. Forecast Uncertainty

For each horizon, residuals are calculated on the held-out set:

\[
r_i=y_i-\hat{y}_i
\]

The 5th and 95th residual percentiles are added to point forecasts to form an empirical 90% residual interval. Bounds are clamped at zero. This interval is a historical residual range, not a guarantee of future coverage after distribution shift.

## 9. Feature Importance

Feature importance uses LightGBM gain. Per-horizon gain shares are saved and averaged for the combined chart. Gain importance identifies model reliance but does not establish causal relationships.

## 10. Signal Advisor Phase Mapping

The proof of concept aggregates opposing approaches into two phases:

| Phase | Approaches |
|---|---|
| 1 | North Arar Street, South Arar Street |
| 2 | East Approach, West Approach |

This is not a claim about the deployed GAM controller plan. Real deployment requires the validated controller phase plan, including protected turns and pedestrian phases.

## 11. Advisor Assumptions

| Assumption | Prototype value |
|---|---:|
| Forecast count interval | 15 minutes |
| Saturation flow | 1,800 veh/h/lane |
| North (Al-Sharif Nasser, opposite Arar) lanes | 5 |
| South (Arar Street) lanes | 3 |
| East (Prince Shaker, right of Arar) lanes | 5 |
| West (Al-Kindi, left of Arar) lanes | 5 |
| Lost time | 6 seconds/phase |
| Minimum green | 15 seconds |
| Cycle clamp | 60–120 seconds |

All assumptions are visible in the API response.

## 12. Critical Flow Ratios and Webster Cycle

The 15-minute predicted count is annualized to an hourly rate:

\[
q_a=4\hat{N}_{a,15min}
\]

Approach flow ratio:

\[
y_a=\frac{q_a}{1800\times lanes_a}
\]

The phase critical ratio is the maximum ratio of its concurrent opposing approaches. The Webster-style raw cycle is:

\[
C_{raw}=\frac{1.5L+5}{1-Y}
\]

The final cycle is clamped to 60–120 seconds and returned separately from the raw value.

## 13. Green Split

Available effective green is `cycle - total lost time`. Phase green is proportional to its critical ratio:

\[
g_p=(C-L)\frac{y_p}{\sum y_p}
\]

A 15-second minimum and rounding correction are applied. Validation requires:

```text
sum(recommended greens) + total lost time = recommended cycle
```

## 14. Delay Estimate

Uniform control delay per approach is approximated as:

\[
d_a=\frac{0.5C(1-g/C)^2}{1-X_a(g/C)}
\]

with degree of saturation capped at 0.99 for numerical stability. Vehicles per cycle are `q × C / 3600`. Total vehicle-minutes per cycle are the sum of delay seconds per vehicle multiplied by vehicles per cycle, divided by 60. Estimated saving is:

\[
Saving=Delay_{current}-Delay_{recommended}
\]

Negative estimated savings are reported as zero. This is an analytical estimate, not measured field benefit.

## 15. Guard Rails and Day 4 Sanity Checks

The recommender is checked across weekday morning, AM peak, midday, PM peak, evening, Friday, and weekend scenarios. Every scenario must satisfy:

- Cycle length between 60 and 120 seconds.
- Green time at least 15 seconds for every configured phase.
- Green sum plus lost time equals cycle length.
- Finite, non-negative delay saving.
- Finite raw Webster cycle.
- Complete coverage of configured phases.
- Both advisory safety flags set to true.

Detailed outputs are saved to `recommendation_sanity_check.csv` and `recommendation_sanity_details.json`.

## 16. API Endpoints

- `GET /forecast`: forecasts at 15, 30, and 60 minutes with uncertainty bounds and accuracy summary.
- `GET /recommendation`: live 30-minute-horizon timing advice.
- `GET /recommendation?at=<ISO timestamp>`: deterministic demo-clock recommendation.

Legacy aliases are retained to avoid breaking the current M3 dashboard while detailed per-phase fields remain canonical.

## 17. Known Limitations

- Forecast evaluation is synthetic-data evaluation.
- Phase 1 current timing is a declared default because the phase log is incomplete.
- The two-phase representation simplifies the real controller plan.
- Lane counts and saturation flow require field calibration.
- Uniform-delay theory is limited under oversaturation, platooning, incidents, and unusual arrivals.
- Holiday behaviour is not learned because the current synthetic data has no labelled holidays.
- Forecast residual intervals may lose coverage under real-world distribution shift.

## 18. Deployment Requirements

Before operational use, the system requires real GAM SCATS counts, a validated phase plan, field-calibrated saturation flows and lane geometry, simulation testing, controlled field trials, operator training, authenticated access, monitoring, and continued separation from the physical controller until formal safety approval.
