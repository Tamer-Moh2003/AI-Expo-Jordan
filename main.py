"""Day 1 vehicle tracking pipeline with privacy protection and FPS reporting."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

from privacy_blur import PrivacyBlur


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
    parser.add_argument("--no-plate-blur", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--display", action="store_true", help="Display privacy-safe frames")
    return parser.parse_args()


def source_value(source: str):
    return int(source) if source.isdigit() else source


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
    source = source_value(args.source)
    source_fps, width, height = source_fps_and_size(source)
    if not width or not height:
        raise RuntimeError("The source did not report a valid frame size")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "annotated_private.mp4"
    csv_path = output_dir / "tracks.csv"
    performance_path = output_dir / "performance.json"

    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), source_fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create output video: {video_path}")

    vehicle_model = YOLO(args.vehicle_model)
    plate_backend = "none" if args.no_plate_blur else args.plate_backend
    privacy = PrivacyBlur(
        args.plate_model,
        plate_confidence=args.confidence,
        plate_backend=plate_backend,
    )

    start = time.perf_counter()
    frame_number = 0
    track_rows = 0

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=TRACK_COLUMNS)
            csv_writer.writeheader()

            results = vehicle_model.track(
                source=source,
                tracker=args.tracker,
                classes=VEHICLE_CLASSES,
                conf=args.confidence,
                imgsz=args.imgsz,
                stream=True,
                persist=True,
                verbose=False,
            )

            for result in results:
                frame_number += 1
                timestamp = (frame_number - 1) / source_fps
                boxes = result.boxes

                if boxes is not None and boxes.id is not None:
                    ids = boxes.id.int().cpu().tolist()
                    classes = boxes.cls.int().cpu().tolist()
                    coordinates = boxes.xyxy.cpu().tolist()
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

                annotated = result.plot()
                private_frame = privacy.apply(annotated)
                writer.write(private_frame)

                if args.display:
                    cv2.imshow("Privacy-safe vehicle tracking", private_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    finally:
        writer.release()
        if args.display:
            cv2.destroyAllWindows()

    elapsed = time.perf_counter() - start
    processing_fps = frame_number / elapsed if elapsed else 0.0
    report = {
        "source": args.source,
        "source_fps": round(source_fps, 3),
        "frames_processed": frame_number,
        "track_rows": track_rows,
        "elapsed_seconds": round(elapsed, 3),
        "processing_fps": round(processing_fps, 3),
        "target_fps": 12,
        "meets_12_fps_target": processing_fps >= 12,
        "input_size": [width, height],
        "inference_size": args.imgsz,
        "privacy": {"faces": True, "licence_plates": plate_backend != "none"},
        "plate_backend": plate_backend,
    }
    performance_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Video: {video_path}")
    print(f"Tracks: {csv_path}")
    print(f"Performance: {performance_path}")
    print(f"Processing FPS: {processing_fps:.2f} ({'PASS' if processing_fps >= 12 else 'BELOW TARGET'})")


if __name__ == "__main__":
    run(parse_args())
