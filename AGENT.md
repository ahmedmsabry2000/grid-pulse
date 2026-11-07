# Grid Pulse — agent runbook

Local checkout: `~/dev/personal/gridpulse`. Remote: `https://github.com/ahmedmsabry2000/grid-pulse.git`. Spec → Issue → Project via `scripts/github/`. Project store docs are source of truth for locked decisions.

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

## Two-process live demo (simulator + UI)

The simulator and Streamlit are **separate OS processes**. The UI must not spawn or embed the simulator. Shared coupling is only the events file path (`events.jsonl` in cwd, or `GRIDPULSE_EVENTS_PATH`).

**Terminal A — simulator (appends continuously):**

```bash
uv run gridpulse-simulate --interval 1 --inject-rate 0.1 --seed 42
# optional: --full-coverage  (default is sparse meters)
```

**Terminal B — UI (auto-tails the same path):**

```bash
uv run streamlit run src/gridpulse/ui/app.py
```

Open http://localhost:8501. Path is shown read-only (no picker/upload). The live chart plots **all channels** as colored traces (legend; no channel dropdown). Use **Run powerflow** to freeze an immutable snapshot of the stream up to that click plus PF / rating / ensemble panels; live ticks only feed the *next* click. Prev/Next navigates older snapshots (default: latest).

### Batch (non-live) alternative

```bash
uv run gridpulse --ticks 20 --inject-faults --jsonl events.jsonl
uv run streamlit run src/gridpulse/ui/app.py
```

Golden UI fixture: `tests/fixtures/golden_events.jsonl`.

## Cursor

- Rules (always): `.cursor/rules/`
- Skills: `.cursor/skills/gridpulse-*` (incl. `gridpulse-ui`, `gridpulse-github-workflow`)
- Specs: `docs/specs/` → `scripts/github/new-issue-from-spec.sh`

## Deferred (do not build without plan revision)

Remote/SCADA, gate severity tiers, PF residual productization, strict mypy, in-app simulator start/stop.
