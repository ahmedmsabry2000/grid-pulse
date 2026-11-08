#!/usr/bin/env bash
# Start Grid Pulse without containers (simulator + API + Vite UI).
# Prefer this on 8 GiB macOS hosts where Podman VMs get jetsammed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVENTS="${GRIDPULSE_EVENTS_PATH:-$ROOT/events.jsonl}"
export GRIDPULSE_EVENTS_PATH="$EVENTS"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }; }
need npm

SIM_BIN="$ROOT/data-simulator/.venv/bin/gridpulse-simulate"
API_BIN="$ROOT/web-server/.venv/bin/uvicorn"
[[ -x "$SIM_BIN" ]] || { echo "missing $SIM_BIN (create data-simulator/.venv)" >&2; exit 1; }
[[ -x "$API_BIN" ]] || { echo "missing $API_BIN (create web-server/.venv)" >&2; exit 1; }

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required so processes outlive this script" >&2
  exit 1
fi

for s in gp-sim gp-api gp-ui; do
  tmux has-session -t "=$s" 2>/dev/null && tmux kill-session -t "$s" || true
done

tmux new-session -d -s gp-sim -c "$ROOT" -- "${SHELL:-zsh}" -l
tmux send-keys -t 'gp-sim:0.0' \
  "export GRIDPULSE_EVENTS_PATH='$EVENTS'; exec '$SIM_BIN' --interval 1 --inject-rate 0.15 --seed 42" C-m

tmux new-session -d -s gp-api -c "$ROOT" -- "${SHELL:-zsh}" -l
tmux send-keys -t 'gp-api:0.0' \
  "export GRIDPULSE_EVENTS_PATH='$EVENTS'; exec '$API_BIN' gridpulse_server.app:app --host 127.0.0.1 --port 8000" C-m

tmux new-session -d -s gp-ui -c "$ROOT/web-client" -- "${SHELL:-zsh}" -l
tmux send-keys -t 'gp-ui:0.0' \
  "exec npm run dev -- --host 127.0.0.1 --port 5173" C-m

echo "Started tmux sessions: gp-sim, gp-api, gp-ui"
echo "UI:     http://127.0.0.1:5173"
echo "API:    http://127.0.0.1:8000/health"
echo "Attach: tmux attach -t gp-api"
echo "Stop:   tmux kill-session -t gp-sim; tmux kill-session -t gp-api; tmux kill-session -t gp-ui"
