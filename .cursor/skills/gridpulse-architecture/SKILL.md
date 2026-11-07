---
name: gridpulse-architecture
description: Module map, allowed imports, and domain-types-first guidance for Grid Pulse.
---

# Grid Pulse architecture

## Module map

| Package | Owns |
|---------|------|
| `network` | Pluggable loader + synthetic layout; pandapower net isolation |
| `telemetry` | Measurement schemas, history, synthetic ticks |
| `quality` | Validators; `PowerflowGate` Run\|Skip |
| `powerflow` | Apply sample + PF run + converged result |
| `anomaly` | Measurement-fault detectors; `AnomalyEvent` |
| `pipeline` | `run_tick` / `run_batch`; JSONL + stdout |
| `ui` | Streamlit helpers + Plotly over Stage 6 events |
| `config` | Settings / thresholds |
| `simulator` | Continuous live JSONL appender |

Top-level minirepos (own venvs): `packages/gridpulse`, `data-simulator`, `streamlit-app`, `web-server`, `web-client`.

## Allowed imports

- Only `network` and `powerflow` import pandapower.
- `pipeline` may depend on all domain packages; `ui` reads events/JSONL only.
- Prefer domain dataclasses/enums over raw DataFrames at package boundaries.

## Domain first

Define measurement, gate decision, PF result, and anomaly event types before wiring adapters.
