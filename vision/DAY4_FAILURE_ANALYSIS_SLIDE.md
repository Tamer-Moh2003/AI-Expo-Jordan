# Incident Engine — Honest Failure Analysis

| Condition | Result | Observed limitation |
|---|---|---|
| Night | Not evaluated | No approved night footage in the labelled set. |
| Rain | Not evaluated | No approved rain footage in the labelled set. |
| Occlusion | Not evaluated separately | Dense traffic contains overlap, but no per-object occlusion labels exist. |
| Distant vehicles | Not evaluated separately | Far-field vehicles appear, but distance is not annotated for scoring. |
| Dense scenes | Weak | The queue in `sc5` was missed because the 10.47-second clip provides insufficient tracker warm-up for a rule requiring 10 continuous seconds. |

**Primary limitation:** all four stalled-positive windows are shorter than the
production 45-second stalled threshold, so they cannot trigger the rule.

**Unsupported output:** 42 wrong-way candidates were excluded from supported
metrics because this labelled set has no approved wrong-way ground truth and no
approved per-camera direction polygons.

**Demo-breaking bug fixed:** transient Windows/OneDrive locks no longer crash
atomic `health.json` updates; replacement is retried and covered by a regression
test.
