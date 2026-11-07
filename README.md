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
uv run pytest --cov=gridpulse --cov-report=term-missing
```

Coverage floor: 75% (see `AGENT.md`).

## Demo + UI (two processes)

```bash
# Terminal A — live simulator (separate OS process)
uv run gridpulse-simulate --interval 1 --inject-rate 0.1

# Terminal B — UI auto-tails events.jsonl (or GRIDPULSE_EVENTS_PATH)
uv run streamlit run src/gridpulse/ui/app.py
```

Batch alternative: `uv run gridpulse --inject-faults --jsonl events.jsonl`.

Agent runbook: [AGENT.md](AGENT.md).

## Package layout

```
src/gridpulse/
  network/     # pluggable pandapower loader (default case14)
  telemetry/   # schemas + synthetic / historical ticks
  quality/     # validators + hard powerflow gate
  powerflow/   # PF runner
  anomaly/     # measurement-fault + rating + ensemble detectors
  pipeline/    # tick / batch orchestration + JSONL
  simulator/   # continuous live appender (CLI: gridpulse-simulate)
  ui/          # Streamlit + Plotly app
  config/      # settings + events path
tests/
  unit/
  integration/
```

## Locked decisions

See Project store `docs/project-context.md` and `preferences.md`. Default network is IEEE case14; anomalies are measurement faults; discrete offline batch ticks; hard-skip PF on quality failure.
