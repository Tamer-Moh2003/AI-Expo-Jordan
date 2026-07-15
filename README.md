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
