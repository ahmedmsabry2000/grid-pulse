---
name: gridpulse-ui
description: Streamlit + Plotly time-series UI conventions for Grid Pulse Stage 6 events.
---

# Grid Pulse UI

## Contract

- Read Stage 6 JSONL only — do not re-run the pipeline inside the UI.
- Plot selected measurement series vs tick index.
- Mark gate skips and anomaly timestamps on the same chart.

## Run

```bash
uv sync --extra ui
uv run gridpulse --inject-faults --jsonl events.jsonl
uv run streamlit run src/gridpulse/ui/app.py
```

## Modules

- `gridpulse.ui.events` — load JSONL, build series frame
- `gridpulse.ui.plots` — Plotly figure with skip/anomaly markers
- `gridpulse.ui.app` — Streamlit entry
