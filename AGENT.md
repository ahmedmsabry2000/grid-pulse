# Grid Pulse — agent runbook

Local checkout: `~/dev/personal/gridpulse`. **Local commits only** until a remote is requested. Project store docs are source of truth for locked decisions.

## Setup

```bash
cd ~/dev/personal/gridpulse
uv sync --extra dev --extra ui
```

Python ≥3.11 (CI-local uses 3.12 via uv).

## Tests

```bash
uv run pytest
uv run pytest --cov=gridpulse --cov-report=term-missing
```

Coverage floor: **75%** (Streamlit `ui/app.py` omitted). Stage exit = green tests + stage note under Project store `docs/stages/`.

## Stages 0–8 (order)

| Stage | Focus | Key check |
|-------|--------|-----------|
| 0 | Scaffold, rules, skills | `tests/unit/test_smoke.py` |
| 1 | `load_network` | `tests/unit/test_network_loader.py` |
| 2 | Telemetry | `tests/unit/test_telemetry.py` |
| 3 | Quality gate | `tests/unit/test_quality_gate.py` |
| 4 | Powerflow | `tests/unit/test_powerflow.py` |
| 5 | Anomalies | `tests/unit/test_anomaly.py` |
| 6 | Pipeline/CLI | `tests/integration/test_pipeline.py` |
| 7 | Streamlit UI | `tests/unit/test_ui_events.py` + live UI |
| 8 | Hardening | coverage + golden fixtures + this file |

## Headless demo + UI

```bash
uv run gridpulse --ticks 20 --inject-faults --jsonl events.jsonl
uv run streamlit run src/gridpulse/ui/app.py
```

Open http://localhost:8501 and select a signal. Markers: gate skips (x), anomalies (diamond).

Golden UI fixture: `tests/fixtures/golden_events.jsonl`.

## Cursor

- Rules (always): `.cursor/rules/`
- Skills: `.cursor/skills/gridpulse-*` (incl. `gridpulse-ui`)

## Deferred (do not build without plan revision)

Remote/SCADA, wall-clock streaming, gate severity tiers, PF residual productization, strict mypy.
