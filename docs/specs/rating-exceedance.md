---
title: Rating exceedance detector
effort: M
type: feature
---

# Rating exceedance detector

## Goal

After a successful powerflow (gate Run + converged), flag network objects whose loadings/currents exceed their ratings (`max_loading_percent`, `max_i_ka`, and similar where present). Emit a distinct `rating_exceedance` anomaly event with object id, quantity, value, limit, and margin — independent of historical anomaly scoring.

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

- [ ] After gate Run + converged PF, compare results to pandapower object limits (`max_loading_percent`, `max_i_ka`, similar where present)
- [ ] Emit `AnomalyType.rating_exceedance` with object id, quantity, value, limit, margin
- [ ] Wire into pipeline/JSONL/UI markers like other anomaly events
- [ ] Unit tests: over-limit fires; under-limit clean; skipped PF does not invent ratings; non-converged PF does not invent ratings
- [ ] Orthogonality: rating events are emitted regardless of historical/ensemble scores (and vice versa when both exist)
- [ ] Out of scope: historical/ensemble scoring; changing hard quality gate

## Notes

- Files (expected): `src/gridpulse/anomaly/`, `src/gridpulse/powerflow/`, `src/gridpulse/pipeline/`, tests under `tests/unit/`, UI event legend if needed
- Rating path depends on PF results/limits, not historical Isolation Forest
- Keep `pf_residual` unused / reserved
