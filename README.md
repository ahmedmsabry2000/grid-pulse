# Grid Pulse

Real-time power grid anomaly detection: pandapower network context, quality-gated powerflows, measurement-fault anomalies, JSONL events, Streamlit UI, and a deck.gl + WebSocket UI.

## Minirepos (own venv / node_modules each)

| Path | Purpose |
|------|---------|
| [`packages/gridpulse/`](packages/gridpulse/) | Core library + layout |
| [`data-simulator/`](data-simulator/) | Continuous events writer |
| [`streamlit-app/`](streamlit-app/) | Streamlit + Plotly (kept) |
| [`web-server/`](web-server/) | FastAPI REST + WS |
| [`web-client/`](web-client/) | React/Vite + deck.gl |

See [AGENT.md](AGENT.md) for full setup and the three-process live demo.

## Quick start (deck.gl)

```bash
# once per folder
cd packages/gridpulse && uv venv && source .venv/bin/activate && uv sync --extra dev --extra ui
cd ../../data-simulator && uv venv && source .venv/bin/activate && uv sync
cd ../web-server && uv venv && source .venv/bin/activate && uv sync --extra dev
cd ../web-client && npm install

# three terminals from repo root / web-client
data-simulator/.venv/bin/gridpulse-simulate --interval 1 --inject-rate 0.1
GRIDPULSE_EVENTS_PATH="$PWD/events.jsonl" web-server/.venv/bin/uvicorn gridpulse_server.app:app --port 8000
cd web-client && npm run dev
```

## Package layout (core)

```
packages/gridpulse/src/gridpulse/
  network/     # loader + synthetic layout (GeoJSON-ready)
  telemetry/   # schemas + synthetic / historical ticks
  quality/     # validators + hard powerflow gate
  powerflow/   # PF runner
  anomaly/     # measurement-fault + rating + ensemble detectors
  pipeline/    # tick / batch orchestration + JSONL
  simulator/   # continuous live appender (CLI: gridpulse-simulate)
  ui/          # Streamlit helpers + powerflow panel
  config/      # settings + events path
```

## Locked decisions

See Project store `docs/project-context.md` and `preferences.md`. Default network is IEEE case14; anomalies are measurement faults; discrete offline batch ticks; hard-skip PF on quality failure; geometry is synthetic (no real GIS).
