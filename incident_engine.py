"""Day 2 zone analytics, incident rules, event JSON, and evidence writer."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive traffic analytics and incidents")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--zones", required=True)
    parser.add_argument("--config", default="day2_config.json")
    parser.add_argument("--video", help="Privacy-safe annotated video for evidence")
    parser.add_argument("--output-dir", default="outputs/day2")
    return parser.parse_args()


def inside(point: tuple[float, float], polygon: list[list[int]]) -> bool:
    if len(polygon) < 3:
        return False
    contour = __import__("numpy").array(polygon, dtype="float32")
    return cv2.pointPolygonTest(contour, point, False) >= 0


def load_tracks(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row = dict(raw)
            for field in (
                "timestamp", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
                "centroid_x", "centroid_y",
            ):
                row[field] = float(row[field])
            row["frame"] = int(row["frame"])
            row["track_id"] = int(row["track_id"])
            rows.append(row)
    rows.sort(key=lambda item: (item["timestamp"], item["track_id"]))
    return rows


def approach_for(row: dict, zones: dict) -> str | None:
    point = (row["centroid_x"], row["centroid_y"])
    for name, config in zones["approaches"].items():
        if any(inside(point, lane) for lane in config.get("lanes", [])):
            return name
    return None


def enrich_tracks(rows: list[dict], zones: dict, speed_window: float) -> list[dict]:
    history: dict[int, deque] = defaultdict(deque)
    for row in rows:
        row["approach"] = approach_for(row, zones)
        row["speed_px_s"] = 0.0
        row["vx_px_s"] = 0.0
        row["vy_px_s"] = 0.0
        track_history = history[row["track_id"]]
        while track_history and row["timestamp"] - track_history[0][0] > speed_window:
            track_history.popleft()
        if track_history:
            old_time, old_x, old_y = track_history[0]
            delta_time = row["timestamp"] - old_time
            if delta_time > 0:
                row["vx_px_s"] = (row["centroid_x"] - old_x) / delta_time
                row["vy_px_s"] = (row["centroid_y"] - old_y) / delta_time
                row["speed_px_s"] = math.hypot(row["vx_px_s"], row["vy_px_s"])
        track_history.append((row["timestamp"], row["centroid_x"], row["centroid_y"]))
    return rows


def normalized_direction(points: list[list[int]]) -> tuple[float, float] | None:
    if len(points) != 2:
        return None
    dx = points[1][0] - points[0][0]
    dy = points[1][1] - points[0][1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length else None


def confidence_from_margin(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.5
    return round(min(0.99, max(0.5, 0.5 + 0.49 * (value - threshold) / threshold)), 3)


def make_event(timestamp: float, event_type: str, approach: str, confidence: float,
               queue_estimate: int, track_id: int | None = None) -> dict:
    event_id = f"{event_type}_{approach}_{timestamp:.3f}".replace(".", "_")
    return {
        "event_id": event_id,
        "timestamp": round(timestamp, 3),
        "type": event_type,
        "approach": approach,
        "confidence": round(confidence, 3),
        "snapshot_path": "",
        "short_clip_path": "",
        "queue_estimate": int(queue_estimate),
        "track_id": track_id,
    }


def analyse(rows: list[dict], zones: dict, cfg: dict) -> tuple[list[dict], list[dict]]:
    by_time: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        if row["approach"]:
            by_time[row["timestamp"]].append(row)

    events: list[dict] = []
    cooldown: dict[tuple, float] = defaultdict(lambda: -1e9)
    stalled_start: dict[int, float] = {}
    spill_start: dict[str, float] = {}
    approach_speeds: dict[str, deque] = defaultdict(deque)
    track_origins: dict[int, tuple] = {}
    minute_stats: dict[tuple[int, str], dict] = {}

    def allowed(key: tuple, timestamp: float) -> bool:
        if timestamp - cooldown[key] >= cfg["event_cooldown_seconds"]:
            cooldown[key] = timestamp
            return True
        return False

    for timestamp in sorted(by_time):
        current = by_time[timestamp]
        by_approach: dict[str, list[dict]] = defaultdict(list)
        for row in current:
            by_approach[row["approach"]].append(row)

        queue_by_approach = {
            name: sum(r["speed_px_s"] <= cfg["queue_speed_threshold_px_s"] for r in group)
            for name, group in by_approach.items()
        }

        for approach, group in by_approach.items():
            minute = int(timestamp // 60)
            stat = minute_stats.setdefault(
                (minute, approach),
                {"minute": minute, "approach": approach, "track_ids": set(), "queue_length_estimate": 0},
            )
            stat["track_ids"].update(row["track_id"] for row in group)
            stat["queue_length_estimate"] = max(
                stat["queue_length_estimate"], queue_by_approach[approach]
            )

            speeds = [row["speed_px_s"] for row in group if row["speed_px_s"] > 0]
            mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
            history = approach_speeds[approach]
            history.append((timestamp, mean_speed))
            while history and timestamp - history[0][0] > cfg["congestion_window_seconds"]:
                history.popleft()
            older = [speed for time, speed in history if timestamp - time >= cfg["congestion_window_seconds"] / 2 and speed > 0]
            recent = [speed for time, speed in history if timestamp - time <= 10 and speed > 0]
            if older and recent:
                baseline = sum(older) / len(older)
                current_speed = sum(recent) / len(recent)
                drop = 100 * (baseline - current_speed) / baseline if baseline else 0
                if (baseline >= cfg["congestion_min_baseline_speed_px_s"] and
                        drop >= cfg["congestion_drop_percent"] and
                        allowed(("sudden_congestion", approach), timestamp)):
                    events.append(make_event(timestamp, "sudden_congestion", approach,
                                             confidence_from_margin(drop, cfg["congestion_drop_percent"]),
                                             queue_by_approach[approach]))

            spill_polygon = zones["approaches"][approach].get("spillback_zone", [])
            spill_count = sum(inside((r["centroid_x"], r["centroid_y"]), spill_polygon) for r in group)
            if spill_count >= cfg["spillback_vehicle_threshold"]:
                spill_start.setdefault(approach, timestamp)
                duration = timestamp - spill_start[approach]
                if (duration >= cfg["spillback_duration_seconds"] and
                        allowed(("queue_spillback", approach), timestamp)):
                    events.append(make_event(timestamp, "queue_spillback", approach,
                                             confidence_from_margin(spill_count, cfg["spillback_vehicle_threshold"]),
                                             queue_by_approach[approach]))
            else:
                spill_start.pop(approach, None)

        for row in current:
            approach = row["approach"]
            point = (row["centroid_x"], row["centroid_y"])
            spill_polygon = zones["approaches"][approach].get("spillback_zone", [])
            outside_queue = not inside(point, spill_polygon) and queue_by_approach[approach] < cfg["queue_context_vehicle_count"]
            if row["speed_px_s"] <= cfg["stalled_speed_threshold_px_s"] and outside_queue:
                stalled_start.setdefault(row["track_id"], timestamp)
                duration = timestamp - stalled_start[row["track_id"]]
                if (duration >= cfg["stalled_duration_seconds"] and
                        allowed(("stalled_vehicle", row["track_id"]), timestamp)):
                    events.append(make_event(timestamp, "stalled_vehicle", approach,
                                             confidence_from_margin(duration, cfg["stalled_duration_seconds"]),
                                             queue_by_approach[approach], row["track_id"]))
            else:
                stalled_start.pop(row["track_id"], None)

            origin = track_origins.setdefault(
                row["track_id"], (timestamp, row["centroid_x"], row["centroid_y"], approach)
            )
            direction = normalized_direction(zones["approaches"][approach].get("expected_direction", []))
            if direction and origin[3] == approach:
                dx = row["centroid_x"] - origin[1]
                dy = row["centroid_y"] - origin[2]
                displacement = math.hypot(dx, dy)
                cosine = (dx * direction[0] + dy * direction[1]) / displacement if displacement else 1.0
                if (displacement >= cfg["wrong_way_min_displacement_px"] and
                        cosine <= cfg["wrong_way_cosine_threshold"] and
                        allowed(("wrong_way", row["track_id"]), timestamp)):
                    confidence = min(0.99, max(0.5, (1 - cosine) / 2))
                    events.append(make_event(timestamp, "wrong_way_or_abnormal_trajectory",
                                             approach, confidence, queue_by_approach[approach], row["track_id"]))

    summaries = []
    for stat in sorted(minute_stats.values(), key=lambda item: (item["minute"], item["approach"])):
        summaries.append({
            "minute": stat["minute"],
            "minute_start_seconds": stat["minute"] * 60,
            "approach": stat["approach"],
            "vehicle_count": len(stat["track_ids"]),
            "queue_length_estimate": stat["queue_length_estimate"],
        })
    return events, summaries


def write_evidence(events: list[dict], video_path: str, output_dir: Path, cfg: dict) -> None:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open evidence video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    for event in events:
        timestamp = event["timestamp"]
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if ok:
            snapshot = evidence_dir / f"{event['event_id']}.jpg"
            cv2.imwrite(str(snapshot), frame)
            event["snapshot_path"] = str(snapshot).replace("\\", "/")

        start = max(0.0, timestamp - cfg["evidence_clip_before_seconds"])
        end = timestamp + cfg["evidence_clip_after_seconds"]
        capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
        clip = evidence_dir / f"{event['event_id']}.mp4"
        writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        while capture.get(cv2.CAP_PROP_POS_MSEC) / 1000 <= end:
            ok, frame = capture.read()
            if not ok:
                break
            writer.write(frame)
        writer.release()
        event["short_clip_path"] = str(clip).replace("\\", "/")
    capture.release()


def main() -> None:
    args = parse_args()
    zones = json.loads(Path(args.zones).read_text(encoding="utf-8"))
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = enrich_tracks(load_tracks(args.tracks), zones, cfg["speed_window_seconds"])
    events, summaries = analyse(rows, zones, cfg)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.video and events:
        write_evidence(events, args.video, output_dir, cfg)

    with (output_dir / "approach_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["minute", "minute_start_seconds", "approach", "vehicle_count", "queue_length_estimate"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    (output_dir / "events.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
    with (output_dir / "enriched_tracks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    print(f"Events: {len(events)}")
    print(f"Metrics: {output_dir / 'approach_metrics.csv'}")
    print(f"Event JSON: {output_dir / 'events.json'}")


if __name__ == "__main__":
    main()
