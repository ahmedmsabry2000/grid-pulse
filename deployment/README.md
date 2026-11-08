# Grid Pulse deployment (Docker + Podman)

Compose-first stack for local containers. **Same** `compose.yml` works with Docker Compose and Podman Compose / `podman-compose`.

## Services

| Service | Port | Role |
|---------|------|------|
| `data-simulator` | — | Appends Stage 6 ticks to shared `events.jsonl` |
| `web-server` | `8000` | FastAPI REST + `/ws/telemetry` |
| `web-client` | `8080` | deck.gl UI (nginx proxies `/api` + `/ws`) |
| `streamlit` | `8501` | Optional (`--profile streamlit`) |

Shared volume `events-data` mounts at `/data` so simulator → server → client works out of the box.

## Prerequisites

- Docker Engine + `docker compose`, **or**
- Podman + `podman compose` (Podman 4+) / `podman-compose`
- Ability to pull `python:3.14-slim`, `node:20-alpine`, and `nginx:1.27-alpine` (or have them cached)

On this machine `docker` may be aliased to `podman`; either CLI is fine.

If registry pulls fail (Podman auth / mirror issues), use the local three-process run in `AGENT.md` for smoke, then retry compose once pulls work.

## Up

From the **repo root**:

```bash
# Docker
docker compose -f deployment/compose.yml up --build

# Podman (Compose v2 plugin)
podman compose -f deployment/compose.yml up --build

# podman-compose (standalone)
podman-compose -f deployment/compose.yml up --build
```

Open:

- deck.gl UI: http://localhost:8080
- API health: http://localhost:8000/health
- Streamlit (optional):

```bash
docker compose -f deployment/compose.yml --profile streamlit up --build
# or: podman compose -f deployment/compose.yml --profile streamlit up --build
```

## Down

```bash
docker compose -f deployment/compose.yml down
# or
podman compose -f deployment/compose.yml down
```

Add `-v` to drop the events volume.

## Smoke check

After `up`, wait ≥1 minute and confirm:

- `data-simulator` keeps writing (no restart loop)
- `curl -sf http://localhost:8000/health` → `{"status":"ok"}`
- `curl -sf http://localhost:8000/networks` lists `case14`
- UI at `:8080` shows WS live / ticks advancing

```bash
docker compose -f deployment/compose.yml logs --tail=80
# or: podman compose -f deployment/compose.yml logs --tail=80
```
