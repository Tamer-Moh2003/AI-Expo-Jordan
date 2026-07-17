# M1 Day 4 Validation Report

## Scope

No new incident feature was added on Day 4. Work was limited to evaluation,
honest failure reporting, and one demo-breaking health-file fix.

## Approved mapping

- `illegal_stop`, `blocked_lane`, `blocked_entrance` → `stalled_vehicle`
- queue extension → `queue_spillback`
- unsuitable types → `unsupported`

The approved `sc3.mp4` interval is 17–37 seconds. Events active at the first
frame participate in precision and recall; their latency is `N/A`.

## Metrics

| Incident type | Ground truth | Predictions | TP | FP | FN | Precision | Recall | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Stalled vehicle | 4 | 0 | 0 | 0 | 4 | N/A | 0.000 | N/A |
| Queue spillback | 1 | 0 | 0 | 0 | 1 | N/A | 0.000 | N/A |
| Unsupported | 0 | 42 | 0 | 42 | 0 | 0.000 | N/A | N/A |

The stalled rule requires 45 continuous seconds, while the approved positive
windows last 15.7, 20, 20, and 5 seconds. The dense queue clip lasts about
10.47 seconds, leaving insufficient tracker warm-up for a rule that requires
10 continuous qualifying seconds.

The unsupported outputs are wrong-way candidates produced without approved
per-camera expected-direction polygons. Night and rain were not present;
occlusion and distance were not separately annotated.

## Demo-breaking fix

Atomic `health.json` replacement now retries transient Windows/OneDrive file
locks with bounded backoff. The full suite passes with five tests.
