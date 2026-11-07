---
name: gridpulse-anomaly
description: Measurement-fault anomaly contracts; room for future PF residual detectors.
---

# Grid Pulse anomaly

## MVP (measurement faults + rating)

- Detectors: spike/jump, z-score vs history; range/missing primarily via quality gate.
- Rating exceedance: after gate Run + converged PF, compare loadings/currents to object limits.
- Emit `AnomalyEvent` with type for measurement faults and `rating_exceedance`.
- Seeded weird readings must fire; clean noise stays under threshold.

## Orthogonality

- Rating exceedance and historical anomaly are **independent**. Never suppress one because of the other.
- Over-limit can be historically normal (still emit rating). In-limit can be anomalous (still emit historical/ensemble).

## Extension room (do not implement yet)

- Reserve enum/type member for future `pf_residual` (physics consistency).
- Do not ship residual detectors in Stages 0–8 MVP.
- PF results may be stored for future residual use; Stage 5 must not depend on them.
