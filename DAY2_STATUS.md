# Day 2 validation status

## Implemented

- Interactive lane, stop-line, spillback, and expected-direction editor.
- Per-approach vehicle counts per minute.
- Queue-length estimate from slow tracks.
- Tunable stalled-vehicle, queue-spillback, sudden-congestion, and wrong-way rules.
- Required event fields plus privacy-safe snapshots and evidence clips.

## Preliminary run

The first run on `dataset1.mp4` processed 211.1 seconds of ordinary footage and
produced 13 candidate events with the initial thresholds. Because this is not a
30-minute validation sample and the zones have not been operator-verified, the
13 events are a diagnostic result, not a precision claim. Most are likely false
positives caused by normal signal stopping and sparse detections.

## Still required for Task 26

- Verify every polygon and direction arrow in the interactive editor.
- Provide confirmed clips covering all four event types.
- Tune thresholds against those clips.
- Track and run 30 minutes of ordinary footage.
- Manually review every emitted event and report the true false-positive count.
