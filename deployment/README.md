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
- Podman Desktop / Podman CLI + `podman compose` (Podman 4+) / `podman-compose`
- Ability to pull `python:3.12-slim`, `node:20-bookworm-slim` (web-client build), and `nginx:1.27-alpine`

### Podman machine (macOS)

On macOS, containers run inside a Linux VM. Grid Pulse images (pandapower stack) need **more than the default ~9 GiB disk**. Prefer:

```bash
# On 8 GiB Macs keep memory ≤3072 so macOS does not jetsam the VM
# under Cursor / browser load. Larger VMs often start then die within seconds.
podman machine init --cpus 2 --memory 3072 --disk-size 40 --rootful --now
```

Recommended provider on Apple Silicon: **applehv** (set in `~/.config/containers/containers.conf` under `[machine] provider = "applehv"`, or export `CONTAINERS_MACHINE_PROVIDER=applehv`).

**Why pods were not running (common failures):**

1. **Host RAM jetsam (8 GiB Macs)** — a 4–6 GiB Podman VM + Cursor often gets killed by macOS; API socket then refuses connections. Prefer ≤3 GiB VM memory, or use the **native fallback** below.
2. **Missing SSH identity / wiped machine files** — `~/.local/share/containers/podman/machine/machine` deleted while the VM still looked “running”.
3. **Disk full (default 9 GiB)** — compose build of pandapower images fails with `no space left on device`.
4. **Stale gvproxy sockets** — `bind: address already in use` on `*-api.sock`.
5. **CoreOS ignition emergency mode** — after unclean `killall` of `gvproxy`/`vfkit`, the next boot of the same disk can drop into emergency mode and the API never comes up. Fix: recreate the machine (`podman machine rm -f` then `init --now`), or use `./deployment/podman-up.sh`.
6. **`npm ci` segfault on `node:20-alpine`** — observed under Podman applehv; web-client Dockerfile builds with `node:20-bookworm-slim` instead.
7. **Docker Hub auth errors on public pulls** — if `podman pull` fails with “incorrect username/password” for public `docker.io` images, fix your own Podman/Docker credentials locally (or log out of Hub). Deployment scripts do **not** rewrite `~/.config/containers/auth.json` or `~/.docker/config.json`.

Helper (recreates a healthy machine if needed, then compose up; does not mutate host auth/config):

```bash
chmod +x deployment/podman-up.sh
./deployment/podman-up.sh
```

### Native fallback (no containers)

When Podman/Docker cannot stay up (typical on 8 GiB hosts), run the three processes from the repo root. Shared file: `events.jsonl` (or `GRIDPULSE_EVENTS_PATH`).

```bash
# Terminal A — simulator
data-simulator/.venv/bin/gridpulse-simulate --interval 1 --inject-rate 0.15 --seed 42

# Terminal B — API
GRIDPULSE_EVENTS_PATH="$PWD/events.jsonl" \
  web-server/.venv/bin/uvicorn gridpulse_server.app:app --host 127.0.0.1 --port 8000

# Terminal C — deck.gl UI (Vite proxies /api and /ws → :8000)
cd web-client && npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

- UI: http://127.0.0.1:5173
- API health: http://127.0.0.1:8000/health
- Proxied health: http://127.0.0.1:5173/api/health

See also `AGENT.md` (“Live demo — three processes”).

## Up

From the **repo root**:

```bash
# Docker
docker compose -f deployment/compose.yml up --build -d

# Podman (preferred helper on macOS)
./deployment/podman-up.sh

# Podman compose directly (machine must already be healthy)
podman compose -f deployment/compose.yml up --build -d

# podman-compose (standalone)
podman-compose -f deployment/compose.yml up --build -d
```

Open:

- deck.gl UI: http://localhost:8080
- API health: http://localhost:8000/health
- Streamlit (optional):

```bash
docker compose -f deployment/compose.yml --profile streamlit up --build -d
# or: podman compose -f deployment/compose.yml --profile streamlit up --build -d
```

## Down

```bash
docker compose -f deployment/compose.yml down
# or
podman compose -f deployment/compose.yml down
```

Add `-v` to drop the events volume.

Stop the Podman VM cleanly (avoid `killall gvproxy/vfkit`):

```bash
podman machine stop
```

## Smoke check

After `up`, wait ≥1 minute and confirm:

- `data-simulator` keeps writing (no restart loop)
- `curl -sf http://localhost:8000/health` → `{"status":"ok"}`
- `curl -sf http://localhost:8000/networks` lists `case14`
- `curl -sf 'http://localhost:8000/events?limit=5'` returns ticks
- UI at `:8080` shows WS live / ticks advancing

```bash
podman compose -f deployment/compose.yml logs --tail=80
# or: docker compose -f deployment/compose.yml logs --tail=80
```
