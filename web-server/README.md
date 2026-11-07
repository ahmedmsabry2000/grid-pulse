# web-server

FastAPI REST + WebSocket backend. Tails `events.jsonl` (or `GRIDPULSE_EVENTS_PATH`) and fans out over `/ws/telemetry`.

## Setup

```bash
cd web-server
uv venv
source .venv/bin/activate
uv sync --extra dev
```

Depends on editable `../packages/gridpulse`.

## Run

```bash
# Prefer repo-root cwd so events.jsonl matches the simulator, or set GRIDPULSE_EVENTS_PATH
cd ..   # repo root
web-server/.venv/bin/uvicorn gridpulse_server.app:app --host 0.0.0.0 --port 8000
# or: web-server/.venv/bin/gridpulse-web
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/networks` | Registered network ids |
| GET | `/networks/{id}/topology` | GeoJSON-ready buses/lines (synthetic layout) |
| POST | `/powerflow` | Body `{ "network_id": "case14" }` → gate / PF / rating / ensemble panels |
| WS | `/ws/telemetry` | JSONL event fanout (`{"type":"telemetry","event":...}`) |

## Tests

```bash
cd web-server
uv run pytest
```
