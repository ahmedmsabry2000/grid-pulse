---
name: gridpulse-anomaly
description: Measurement-fault anomaly contracts; room for future PF residual detectors.
---

# Grid Pulse anomaly

## MVP (measurement faults + rating + ensemble)

- Detectors: spike/jump, z-score vs history; range/missing primarily via quality gate.
- Rating exceedance: after gate Run + converged PF, compare loadings/currents to object limits.
- Historical ensemble: unit-interval members (spike, z-score, Isolation Forest) → weighted average → `measurement_ensemble` with member score breakdown.
- Emit `AnomalyEvent` for measurement faults, `rating_exceedance`, and `measurement_ensemble`.
- Seeded weird readings must fire; clean noise stays under threshold.
- Isolation Forest fits on history batch only (no online streaming fit); pin `scikit-learn`.

## Orthogonality

- Rating exceedance and historical anomaly are **independent**. Never suppress one because of the other.
- Over-limit can be historically normal (still emit rating). In-limit can be anomalous (still emit historical/ensemble).

## Extension room (do not implement yet)

- Reserve enum/type member for future `pf_residual` (physics consistency).
- Do not ship residual detectors in Stages 0–8 MVP.
- PF results may be stored for future residual use; Stage 5 must not depend on them.
