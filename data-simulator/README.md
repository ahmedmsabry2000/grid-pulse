# data-simulator

Continuous `events.jsonl` writer. **Separate OS process** from Streamlit / web-server.

## Setup

```bash
cd data-simulator
uv venv
source .venv/bin/activate
uv sync
```

Depends on editable `../packages/gridpulse`.

## Run

```bash
# from repo root (events.jsonl lands in cwd) or set GRIDPULSE_EVENTS_PATH
cd ../..   # repo root
data-simulator/.venv/bin/gridpulse-simulate --interval 1 --inject-rate 0.1 --seed 42
# optional: --full-coverage
```

Or with the minirepo venv activated and `GRIDPULSE_EVENTS_PATH` pointing at the shared file.
