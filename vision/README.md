# M1 Vision Pipeline — Day 1

The pipeline reads a video file, camera index, or RTSP URL; detects and tracks
vehicle classes with YOLO and ByteTrack; blurs faces and licence plates before
display or storage; and writes an annotated video, tracks CSV, and performance
report.

## Install

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py "videos/raw/dataset1.mp4" --output-dir "outputs/day1"
```

For a live stream:

```powershell
python main.py "rtsp://user:password@host/stream" --output-dir "outputs/live"
```

Add `--display` to show the privacy-safe output while processing. Press `q` to
stop. The default inference size is 640. If `performance.json` reports less
than 12 FPS, try `--imgsz 480` or `--imgsz 320` and retain the best report.
The default plate detector is the fast OpenCV Haar cascade. Use
`--plate-backend yolo` for the larger, more accurate legacy plate model when a
GPU is available; use `--plate-backend none` only for controlled debugging.

## Outputs

- `annotated_private.mp4`: annotated video with privacy blur already applied.
- `tracks.csv`: one row per tracked vehicle per frame.
- `performance.json`: measured processing FPS and the 12 FPS pass/fail result.

Raw, unblurred frames are never written or displayed by this script.

## Day 2: zones and incident rules

Draw the lane polygons, stop lines, spillback polygons, and expected travel
direction arrows on a reference frame:

```powershell
python zone_tool.py "videos/raw/dataset1.mp4" --output zones_dataset1.json
```

In the editor, left-click to add points. Press `A` to change approach, `T` to
change shape type, `S` to save the current shape, `Z` to undo, `C` to clear,
and `Q` to finish and write JSON.

Run the analytics and incident engine:

```powershell
python incident_engine.py `
  --tracks "outputs/day1_final_balanced/tracks.csv" `
  --zones "zones_dataset1.json" `
  --video "outputs/day1_final_balanced/annotated_private_final.mp4" `
  --output-dir "outputs/day2_dataset1"
```

Thresholds are explicit and tunable in `day2_config.json`. Outputs are per
approach counts and queue estimates in `approach_metrics.csv`, enriched tracks
with speed and approach, events matching the required API fields in
`events.json`, and privacy-safe snapshots and short evidence clips.

The supplied `zones_dataset1.json` is an initial configuration and must be
checked in the visual editor before evaluation. Threshold tuning and the final
30-minute false-positive measurement require confirmed staged incident clips.

For a CPU-friendly 30-minute ordinary-footage tracking pass without rendering a
new video:

```powershell
python main.py "videos/raw/dataset5(30).mp4" `
  --output-dir "outputs/day2_30min_tracks" `
  --imgsz 320 --frame-stride 8 --analysis-only
```

The final ordinary-footage evaluation and its limitations are documented in
`DAY2_REPORT.md` and `DAY2_STATUS.md`.

## Day 3: resilient stream and health output

Live sources automatically reconnect after seven seconds by default. The delay
can be set from five through ten seconds with `--reconnect-delay`. Corrupt or
empty frames are skipped and counted. Health metrics are atomically written to
`health.json` and match the frozen `GET /health` contract.

```powershell
python main.py "rtsp://camera/stream" `
  --output-dir "outputs/live" `
  --health-output "outputs/live/health.json" `
  --reconnect-delay 7
```

Evidence clips now cover ten seconds before and ten seconds after every event.
See `DAY3_HANDOVER.md` for the integration and validation handoff.
