# packages/gridpulse

Installable Grid Pulse core library (network, telemetry, quality, powerflow, anomaly, pipeline, simulator, ui helpers, layout).

## Setup

```bash
cd packages/gridpulse
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,ui]"
```

## Tests

```bash
uv run pytest
uv run pytest --cov=gridpulse --cov-report=term-missing
```

Coverage floor: **75%** (`ui/app.py` omitted).

## Layout

`gridpulse.network.layout` builds deterministic synthetic bus/line coordinates (NetworkX, fixed seed, cached per network id) as GeoJSON-ready FeatureCollections. No real GIS.
