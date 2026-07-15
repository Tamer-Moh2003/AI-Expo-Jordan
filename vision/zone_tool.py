"""Interactive polygon editor for Day 2 lane, stop-line, and spillback zones."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


COLORS = {
    "lane": (0, 220, 0),
    "stop_line": (255, 200, 0),
    "spillback": (0, 0, 255),
    "direction": (255, 0, 255),
}
KINDS = ("lane", "stop_line", "spillback", "direction")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw traffic zones on a reference frame")
    parser.add_argument("source", help="Reference video or image")
    parser.add_argument("--output", default="zones.json")
    parser.add_argument(
        "--approaches",
        default="northbound,southbound,eastbound,westbound",
        help="Comma-separated approach names",
    )
    return parser.parse_args()


def load_reference(source: str):
    image = cv2.imread(source)
    if image is not None:
        return image
    capture = cv2.VideoCapture(source)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Could not read a reference frame from {source}")
    return frame


def main() -> None:
    args = parse_args()
    frame = load_reference(args.source)
    approaches = [value.strip() for value in args.approaches.split(",") if value.strip()]
    if not approaches:
        raise ValueError("At least one approach is required")

    data = {
        "reference_source": args.source,
        "frame_width": frame.shape[1],
        "frame_height": frame.shape[0],
        "approaches": {
            name: {"lanes": [], "stop_line": [], "spillback_zone": [], "expected_direction": []}
            for name in approaches
        },
    }
    current_points: list[list[int]] = []
    approach_index = 0
    kind_index = 0

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            current_points.append([x, y])

    window = "Zone configuration"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        canvas = frame.copy()
        for name, config in data["approaches"].items():
            for lane in config["lanes"]:
                cv2.polylines(canvas, [np.array(lane)], True, COLORS["lane"], 2)
            if config["stop_line"]:
                cv2.polylines(canvas, [np.array(config["stop_line"])], False, COLORS["stop_line"], 3)
            if config["spillback_zone"]:
                cv2.polylines(canvas, [np.array(config["spillback_zone"])], True, COLORS["spillback"], 2)
            if len(config["expected_direction"]) == 2:
                start, end = config["expected_direction"]
                cv2.arrowedLine(canvas, tuple(start), tuple(end), COLORS["direction"], 3)

        if current_points:
            points = np.array(current_points)
            cv2.polylines(canvas, [points], False, (255, 255, 255), 2)
            for point in current_points:
                cv2.circle(canvas, tuple(point), 4, (255, 255, 255), -1)

        approach = approaches[approach_index]
        kind = KINDS[kind_index]
        help_text = f"Approach: {approach} | Type: {kind} | A: approach  T: type  S: save  Z: undo  C: clear  Q: finish"
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 35), (0, 0, 0), -1)
        cv2.putText(canvas, help_text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.imshow(window, canvas)
        key = cv2.waitKey(30) & 0xFF

        if key == ord("a"):
            approach_index = (approach_index + 1) % len(approaches)
        elif key == ord("t"):
            kind_index = (kind_index + 1) % len(KINDS)
        elif key == ord("z") and current_points:
            current_points.pop()
        elif key == ord("c"):
            current_points.clear()
        elif key == ord("s"):
            minimum = 2 if kind in ("stop_line", "direction") else 3
            if len(current_points) < minimum:
                print(f"{kind} needs at least {minimum} points")
                continue
            target = data["approaches"][approach]
            if kind == "lane":
                target["lanes"].append(current_points.copy())
            elif kind == "stop_line":
                target["stop_line"] = current_points.copy()
            elif kind == "spillback":
                target["spillback_zone"] = current_points.copy()
            else:
                target["expected_direction"] = [current_points[0], current_points[-1]]
            current_points.clear()
        elif key == ord("q"):
            break

    cv2.destroyAllWindows()
    output = Path(args.output)
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved zones: {output}")


if __name__ == "__main__":
    main()
