# Grid Pulse

Real-time power grid anomaly detection: pandapower network context, quality-gated powerflows, measurement-fault anomalies, JSONL events, and a Streamlit + Plotly time-series UI.

## Requirements

- Python 3.11+
- Local git commits only until a remote is requested

## Setup

```bash
uv sync --extra dev
# UI (Stage 7+):
uv sync --extra dev --extra ui
```

## Tests

```bash
uv run pytest
```

## Package layout

```
src/gridpulse/
  network/     # pluggable pandapower loader (default case14)
  telemetry/   # schemas + synthetic / historical ticks
  quality/     # validators + hard powerflow gate
  powerflow/   # PF runner
  anomaly/     # measurement-fault detectors
  pipeline/    # tick / batch orchestration + JSONL
  ui/          # Streamlit + Plotly app
  config/      # settings
tests/
  unit/
  integration/
```

## Locked decisions

See Project store `docs/project-context.md` and `preferences.md`. Default network is IEEE case14; anomalies are measurement faults; discrete offline batch ticks; hard-skip PF on quality failure.
