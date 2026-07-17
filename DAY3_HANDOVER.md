# M1 Day 3 Handover

## Evidence

- Every incident snapshot is taken from the privacy-safe annotated video.
- Every evidence clip covers 10 seconds before and 10 seconds after the event.
- API-compatible incidents are written to `events.json`.
- Evidence files are written below the selected output directory in `evidence/`.

## Stream resilience

- File sources end normally.
- Camera, RTSP, HTTP, UDP, and TCP sources are treated as live sources.
- A live source that ends or raises a decoder/source error retries after 7 seconds.
- The retry delay is configurable but restricted to 5 through 10 seconds.
- Empty or corrupt frames are skipped and counted instead of crashing the pipeline.

## Health contract

The tracker atomically rewrites `health.json` with exactly:

```json
{
  "ingestion_rate_fps": 12.5,
  "dropped_frames": 0,
  "stream_uptime_seconds": 120.0
}
```

For the shared Docker volume, run the tracker with:

```powershell
python main.py "rtsp://camera/stream" `
  --output-dir "/app/data/vision" `
  --health-output "/app/data/vision/health.json" `
  --reconnect-delay 7
```

M2 can serve `/app/data/vision/health.json` from `GET /health`. M3 can render the
three fields without translation because they match the frozen API contract.

## Contract validation

```powershell
python validate_event_contract.py --contract api_contract.json --events outputs/day2/events.json
python validate_health_contract.py --contract api_contract.json --health outputs/run/health.json
```

## Validation handoff

`validation_labels_day4.csv` is the handoff sheet for M4. Rows marked
`needs_review` must be reviewed together before Day 4 metrics are calculated.

## Current limitation

The confirmed validation set still does not cover every incident type with a
reliable onset and end. Precision, recall, and latency must not be claimed until
M4 completes that review.
