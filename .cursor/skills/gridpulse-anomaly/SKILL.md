---
name: gridpulse-anomaly
description: Measurement-fault anomaly contracts; room for future PF residual detectors.
---

# Grid Pulse anomaly

## MVP (measurement faults)

- Detectors: spike/jump, z-score vs history; range/missing primarily via quality gate.
- Emit `AnomalyEvent` with type for measurement faults.
- Seeded weird readings must fire; clean noise stays under threshold.

## Extension room (do not implement yet)

- Reserve enum/type member for future `pf_residual` (physics consistency).
- Do not ship residual detectors in Stages 0–8 MVP.
- PF results may be stored for future residual use; Stage 5 must not depend on them.
