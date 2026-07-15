"""Day 1 vehicle tracking pipeline with privacy protection and FPS reporting."""

from __future__ import annotations

import argparse
import csv
import json
import time
from urllib.parse import urlparse
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from privacy_blur import PrivacyBlur
from health_metrics import HealthMonitor


VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck in COCO
TRACK_COLUMNS = [
    "frame",
    "timestamp",
    "track_id",
    "class",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "centroid_x",
    "centroid_y",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track vehicles and produce a privacy-safe annotated video and CSV."
    )
    parser.add_argument("source", help="Video file path, camera index, or RTSP URL")
    parser.add_argument("--output-dir", default="outputs/run", help="Output directory")
    parser.add_argument("--vehicle-model", default="yolov8n.pt")
    parser.add_argument("--plate-model", default="models/best.pt")
    parser.add_argument(
        "--plate-backend",
        choices=("haar", "yolo", "none"),
        default="haar",
        help="Fast Haar blur (default), accurate legacy YOLO, or disable plates",
    )
    parser.add_argument("--tracker", default="bytetrack.yaml")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--privacy-scale",
        type=float,
        default=0.35,
        help="Scale used for face and fast plate detection (0-1)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="auto, cpu, or a CUDA device number such as 0",
    )
    parser.add_argument("--max-frames", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=1,
        help="Process every Nth source frame while preserving source timestamps",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Write tracks and performance only; do not render or privacy-process video",
    )
    parser.add_argument("--no-plate-blur", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--display", action="store_true", help="Display privacy-safe frames")
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=7.0,
        help="Live-stream reconnect delay in seconds (must be 5-10)",
    )
    parser.add_argument(
        "--health-output",
        help="Health JSON path; defaults to <output-dir>/health.json",
    )
    parser.add_argument(
        "--health-write-interval",
        type=float,
        default=1.0,
        help="Seconds between health JSON updates",
    )
    return parser.parse_args()


def source_value(source: str):
    return int(source) if source.isdigit() else source


def is_live_source(source) -> bool:
    if isinstance(source, int):
        return True
    scheme = urlparse(str(source)).scheme.lower()
    return scheme in {"rtsp", "rtsps", "http", "https", "udp", "tcp"}


def has_valid_frame(result) -> bool:
    original = getattr(result, "orig_img", None)
    return original is not None and getattr(original, "size", 0) > 0


def source_fps_and_size(source) -> tuple[float, int, int]:
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open source: {source}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()
    return (fps if fps > 0 else 30.0), width, height


def run(args: argparse.Namespace) -> None:
    if args.frame_stride < 1:
        raise ValueError("frame_stride must be at least 1")
    if args.analysis_only and args.display:
        raise ValueError("--display cannot be combined with --analysis-only")
    if not 5 <= args.reconnect_delay <= 10:
        raise ValueError("reconnect_delay must be between 5 and 10 seconds")
    if args.health_write_interval <= 0:
        raise ValueError("health_write_interval must be greater than zero")
    source = source_value(args.source)
    live_source = is_live_source(source)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    health_path = Path(args.health_output) if args.health_output else output_dir / "health.json"
    health = HealthMonitor(health_path)

    while True:
        try:
            source_fps, width, height = source_fps_and_size(source)
            health.set_connected(True)
            break
        except RuntimeError as error:
            health.record_dropped()
            health.set_connected(False)
            health.write()
            if not live_source:
                raise
            health.record_reconnect()
            print(f"Stream unavailable: {error}. Retrying in {args.reconnect_delay:.1f}s")
            time.sleep(args.reconnect_delay)
    if not width or not height:
        raise RuntimeError("The source did not report a valid frame size")

    video_path = output_dir / "annotated_private.mp4"
    csv_path = output_dir / "tracks.csv"
    performance_path = output_dir / "performance.json"

    writer = None
    if not args.analysis_only:
        writer = cv2.VideoWriter(
            str(video_path), cv2.VideoWriter_fourcc(*"mp4v"),
            source_fps / args.frame_stride, (width, height)
        )
        if not writer.isOpened():
            raise RuntimeError(f"Could not create output video: {video_path}")

    vehicle_model = YOLO(args.vehicle_model)
    device = ("0" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    plate_backend = "none" if args.no_plate_blur else args.plate_backend
    privacy = None
    if not args.analysis_only:
        privacy = PrivacyBlur(
            args.plate_model,
            plate_confidence=args.confidence,
            plate_backend=plate_backend,
            detection_scale=args.privacy_scale,
        )

    start = time.perf_counter()
    frame_number = 0
    track_rows = 0
    stop_requested = False
    last_health_write = 0.0

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=TRACK_COLUMNS)
            csv_writer.writeheader()

            while not stop_requested:
                try:
                    results = vehicle_model.track(
                        source=source,
                        tracker=args.tracker,
                        classes=VEHICLE_CLASSES,
                        conf=args.confidence,
                        imgsz=args.imgsz,
                        stream=True,
                        persist=True,
                        verbose=False,
                        device=device,
                        vid_stride=args.frame_stride,
                    )

                    received_in_connection = False
                    health.set_connected(True)
                    for result in results:
                        received_in_connection = True
                        if not has_valid_frame(result):
                            health.record_dropped()
                            print("Skipped a corrupt or empty frame")
                            continue
                        health.record_frame()
                        now = time.monotonic()
                        if now - last_health_write >= args.health_write_interval:
                            health.write()
                            last_health_write = now

                        frame_number += 1
                        timestamp = (frame_number - 1) * args.frame_stride / source_fps
                        boxes = result.boxes
                        privacy_vehicle_boxes = []

                        if boxes is not None and boxes.id is not None:
                            ids = boxes.id.int().cpu().tolist()
                            classes = boxes.cls.int().cpu().tolist()
                            coordinates = boxes.xyxy.cpu().tolist()
                            privacy_vehicle_boxes = coordinates
                            for track_id, class_id, (x1, y1, x2, y2) in zip(
                                ids, classes, coordinates
                            ):
                                csv_writer.writerow(
                                    {
                                        "frame": frame_number,
                                        "timestamp": round(timestamp, 3),
                                        "track_id": track_id,
                                        "class": vehicle_model.names[class_id],
                                        "bbox_x1": round(x1, 2),
                                        "bbox_y1": round(y1, 2),
                                        "bbox_x2": round(x2, 2),
                                        "bbox_y2": round(y2, 2),
                                        "centroid_x": round((x1 + x2) / 2, 2),
                                        "centroid_y": round((y1 + y2) / 2, 2),
                                    }
                                )
                                track_rows += 1

                        private_frame = None
                        if not args.analysis_only:
                            annotated = result.plot()
                            private_frame = privacy.apply(annotated, privacy_vehicle_boxes)
                            writer.write(private_frame)

                        if args.display:
                            cv2.imshow("Privacy-safe vehicle tracking", private_frame)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                stop_requested = True
                                break
                        if args.max_frames and frame_number >= args.max_frames:
                            stop_requested = True
                            break

                    if stop_requested or not live_source:
                        break
                    health.set_connected(False)
                    health.record_dropped()
                    health.record_reconnect()
                    health.write()
                    reason = "stream ended" if received_in_connection else "no frames received"
                    print(f"Live {reason}. Retrying in {args.reconnect_delay:.1f}s")
                    time.sleep(args.reconnect_delay)
                except (cv2.error, OSError, RuntimeError) as error:
                    health.record_dropped()
                    health.set_connected(False)
                    health.write()
                    if not live_source:
                        print(f"Stopped gracefully after a corrupt frame/source error: {error}")
                        break
                    health.record_reconnect()
                    print(f"Stream error: {error}. Retrying in {args.reconnect_delay:.1f}s")
                    time.sleep(args.reconnect_delay)
    finally:
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()
        health.set_connected(False)
        health.write()

    elapsed = time.perf_counter() - start
    processing_fps = frame_number / elapsed if elapsed else 0.0
    report = {
        "source": args.source,
        "source_fps": round(source_fps, 3),
        "frames_processed": frame_number,
        "frame_stride": args.frame_stride,
        "source_duration_covered_seconds": round(
            frame_number * args.frame_stride / source_fps, 3
        ),
        "track_rows": track_rows,
        "elapsed_seconds": round(elapsed, 3),
        "processing_fps": round(processing_fps, 3),
        "target_fps": 12,
        "meets_12_fps_target": processing_fps >= 12,
        "input_size": [width, height],
        "inference_size": args.imgsz,
        "device": device,
        "privacy_detection_scale": args.privacy_scale,
        "analysis_only": args.analysis_only,
        "privacy": {
            "faces": not args.analysis_only,
            "licence_plates": not args.analysis_only and plate_backend != "none",
        },
        "plate_backend": plate_backend,
    }
    performance_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not args.analysis_only:
        print(f"Video: {video_path}")
    print(f"Tracks: {csv_path}")
    print(f"Performance: {performance_path}")
    print(f"Health: {health_path}")
    print(f"Processing FPS: {processing_fps:.2f} ({'PASS' if processing_fps >= 12 else 'BELOW TARGET'})")


if __name__ == "__main__":
    run(parse_args())
