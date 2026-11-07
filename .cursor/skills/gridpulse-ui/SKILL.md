---
name: gridpulse-ui
description: Streamlit + Plotly time-series UI conventions for Grid Pulse Stage 6 events.
---

# Grid Pulse UI

## Contract

- Events path is fixed: `events.jsonl` in cwd, or `GRIDPULSE_EVENTS_PATH`. Never prompt for path/upload.
- Auto-tail the stream; plot selected measurement series vs tick index.
- Mark gate skips and anomaly timestamps on the same chart.
- **Run powerflow** re-runs gate/PF/rating/ensemble on the **latest** tick and shows orthogonal panels.
- Simulator is a **separate OS process** — UI must not spawn or embed it.

## Run (two terminals)

```bash
uv sync --extra ui
uv run gridpulse-simulate --interval 1 --inject-rate 0.1
uv run streamlit run src/gridpulse/ui/app.py
```

## Modules

- `gridpulse.config.paths` — `resolve_events_path`
- `gridpulse.ui.events` — load JSONL, build series frame
- `gridpulse.ui.plots` — Plotly figure with skip/anomaly markers
- `gridpulse.ui.powerflow_panel` — latest-tick PF + anomaly lists
- `gridpulse.ui.app` — Streamlit entry
