"""Create a labelled contact sheet for manual false-positive review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    capture = cv2.VideoCapture(args.video)
    tiles = []
    for event in events:
        capture.set(cv2.CAP_PROP_POS_MSEC, event["timestamp"] * 1000)
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (400, 300))
        cv2.rectangle(frame, (0, 0), (400, 48), (0, 0, 0), -1)
        label = f"{event['timestamp']:.0f}s {event['type'][:22]}"
        cv2.putText(frame, label, (5, 29), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (255, 255, 255), 2)
        tiles.append(frame)
    capture.release()
    if not tiles:
        raise RuntimeError("No event frames could be read")
    blank = np.zeros_like(tiles[0])
    while len(tiles) % 4:
        tiles.append(blank.copy())
    rows = [np.hstack(tiles[index:index + 4]) for index in range(0, len(tiles), 4)]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), np.vstack(rows))
    print(f"Contact sheet: {output}")


if __name__ == "__main__":
    main()
