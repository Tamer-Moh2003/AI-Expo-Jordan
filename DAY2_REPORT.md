# M1 Day 2 Report

## Delivered

1. `zone_tool.py` draws lane polygons, stop lines, spillback zones, and expected
   direction arrows and saves them as JSON.
2. `incident_engine.py` combines tracks and zones to derive per-approach counts,
   speeds, and queue estimates.
3. Four incident rules are implemented with explicit thresholds in
   `day2_config.json`.
4. Events contain timestamp, type, approach, confidence, snapshot path, short
   clip path, and queue estimate.
5. `review_events.py` creates a contact sheet for manual alert review.

## Final thresholds

- Queue speed: 12 pixels per second or less.
- Stalled speed: 4 pixels per second or less for 45 seconds.
- Spillback: at least 5 vehicles for 10 seconds.
- Sudden congestion: at least a 65 percent speed drop with a queue of 3 vehicles.
- Wrong way: at least 150 pixels displacement with cosine at or below -0.7.
- Duplicate-event cooldown: 60 seconds.

Pixel thresholds are camera-specific and must be retuned if resolution or camera
viewpoint changes.

## Ordinary-footage result

The final run covered exactly 30 minutes and emitted zero events. Manual review
therefore found zero false positives in that clip. The tracking pass sampled one
frame per second because the demo machine has CPU inference only.

## Honest limitation

The zero false-positive result does not establish precision because there were
no confirmed positive incidents in the 30-minute clip. Recall and latency also
remain unknown until confirmed staged clips for all four event types are used.
