---
title: Historical ensemble anomaly with Isolation Forest
effort: L
type: feature
---

# Historical ensemble anomaly with Isolation Forest

## Goal

Score incoming measurements against history with an ensembled detector (spike, z-score, Isolation Forest). Emit one `measurement_ensemble` event when the weighted-average score meets threshold, with per-member score breakdown — independent of rating exceedance.

## Orthogonality

Rating exceedance and historical anomaly are **independent signals**. They must not imply each other.

| Case | Rating exceedance | Historical anomaly |
|------|-------------------|--------------------|
| Object often run over limit | Yes | No (if that is normal historically) |
| Weird vs history but within rating | No | Yes |
| Both | Yes | Yes |
| Neither | No | No |

Emit separate event types. UI/JSONL show both. Never suppress a rating event because the ensemble score is low, and never suppress an ensemble event because limits are fine.

## Acceptance

- [ ] Detector protocol returns a numeric score in `[0, 1]`
- [ ] Members for MVP: spike, z-score, Isolation Forest (`sklearn.ensemble.IsolationForest`) over a history window of selected channels
- [ ] Weighted-average aggregator with documented default weights; emit when ensemble ≥ threshold
- [ ] Payload includes per-member score breakdown; type `measurement_ensemble` (clear name)
- [ ] Fit Isolation Forest on history batch (no online streaming fit); deterministic seed in tests
- [ ] Pin `scikit-learn` in `pyproject.toml`
- [ ] Keep `pf_residual` unused
- [ ] Unit tests cover member scores, aggregator threshold, IF determinism, and orthogonality vs rating exceedance
- [ ] Out of scope: online streaming fit; deep learning; rating exceedance (separate issue)

## Notes

- Ensemble = weighted average of member scores; Isolation Forest included now
- Rating path is Issue A / separate Spec — do not conflate
- Prefer extending the anomaly package without removing existing spike/z-score emit paths unless ensemble supersedes them by design (document choice in PR)
