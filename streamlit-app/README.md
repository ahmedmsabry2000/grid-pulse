# streamlit-app

Streamlit + Plotly time-series UI. **Kept** as a first-class surface alongside the deck.gl web-client.

## Setup

```bash
cd streamlit-app
uv venv
source .venv/bin/activate
uv sync
```

Depends on editable `../packages/gridpulse` with the `ui` extra.

## Run

```bash
# Terminal A: data-simulator writing events.jsonl (repo root or GRIDPULSE_EVENTS_PATH)
# Terminal B:
cd streamlit-app
source .venv/bin/activate
streamlit run ../packages/gridpulse/src/gridpulse/ui/app.py
```

Open http://localhost:8501.
