# Day 2 validation status

## Completed implementation

- Interactive lane, stop-line, spillback, and expected-direction editor.
- Per-approach vehicle counts per minute.
- Queue-length estimate from slow tracks.
- Tunable stalled-vehicle, queue-spillback, sudden-congestion, and wrong-way rules.
- Required event fields plus privacy-safe snapshots and evidence clips.
- Automated test proving that all four rules emit when their conditions are met.

## Thirty-minute ordinary-footage evaluation

- Source: `videos/raw/dataset5(30).mp4`.
- Source duration: exactly 1,800 seconds.
- Fixed elevated viewpoint, 1,280 by 960 pixels, 8 source FPS.
- Evaluation sampling: one frame per second (`frame_stride=8`).
- Processed frames: 1,800.
- Track rows: 4,958.
- Final emitted incidents: 0.
- Manually reviewable false positives: 0.
- Preliminary false-positive rate: 0 per 30 minutes at the final thresholds.

This result is valid only for this ordinary clip, these polygons, the one-frame-
per-second evaluation sampling, and the final thresholds in `day2_config.json`.
It is not a precision or recall claim.

## Tuning trail

The first run emitted 63 candidates. Fixing missing-track gap handling reduced
that to 17. Correcting direction geometry and separating opposing lanes reduced
it to 8. Increasing the minimum wrong-way displacement to reject tracker jitter
reduced the final result to 0. Contact sheets were manually inspected during
each pass; no real incident was visible in the ordinary validation clip.

## Still unavailable

Confirmed staged clips covering all four rule types are not available. The
current incident clips do not show reliable onset and end boundaries for every
rule. Therefore staged-clip threshold tuning, recall, precision, and detection
latency must not be claimed yet. These metrics require the confirmed clips and
their reviewed ground truth.
