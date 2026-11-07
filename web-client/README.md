# web-client

React + Vite + deck.gl UI. Network dropdown, synthetic Orthographic topology map, Run powerflow, live WS ticks.

## Setup

```bash
cd web-client
npm install
```

## Run

Start `web-server` on port 8000 first (Vite proxies `/api` and `/ws`).

```bash
npm run dev
```

Open http://localhost:5173.

Optional env:

- `VITE_API_BASE` (default `/api`)
- `VITE_WS_URL` (default `ws://<host>/ws/telemetry`)

## Test / build

```bash
npm test
npm run build
```
