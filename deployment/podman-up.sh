#!/usr/bin/env bash
# Bring up Grid Pulse via Podman Compose with a healthy Podman machine.
# Recovers common macOS failures: missing SSH identity, tiny disk,
# gvproxy races, and CoreOS ignition emergency mode after unclean restarts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT/deployment/compose.yml"
PROVIDER="${CONTAINERS_MACHINE_PROVIDER:-applehv}"
DISK_GIB="${PODMAN_MACHINE_DISK_GIB:-40}"
CPUS="${PODMAN_MACHINE_CPUS:-2}"
# Default 3072: 8 GiB Mac hosts OOM-kill a 4–6 GiB VM under Cursor load.
# If the VM still dies, use the native fallback in deployment/README.md.
MEMORY_MIB="${PODMAN_MACHINE_MEMORY_MIB:-3072}"

export PATH="/opt/podman/bin:/opt/homebrew/bin:${HOME}/.local/bin:${PATH}"
export CONTAINERS_MACHINE_PROVIDER="$PROVIDER"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing required command: $1" >&2; exit 1; }; }
need podman

if ! command -v docker-compose >/dev/null 2>&1 && ! podman compose version >/dev/null 2>&1; then
  echo "need podman compose (or docker-compose provider)" >&2
  exit 1
fi

podman_ok() {
  podman info >/dev/null 2>&1
}

ensure_machine() {
  if podman_ok; then
    echo "==> Podman machine already usable"
    return 0
  fi

  echo "==> Podman not reachable; recreating machine (provider=${PROVIDER}, disk=${DISK_GIB}GiB)"
  killall -9 gvproxy vfkit krunkit 2>/dev/null || true
  sleep 1
  # Best-effort cleanup of stale temp sockets that break gvproxy bind.
  PODMAN_TMP="${TMPDIR:-/tmp}/podman"
  rm -rf "$PODMAN_TMP" 2>/dev/null || true
  if [[ -d /var/folders ]]; then
    find /var/folders -type d -name podman -path '*/T/podman' -maxdepth 4 2>/dev/null \
      | while read -r d; do rm -rf "$d"; done || true
  fi

  podman machine stop 2>/dev/null || true
  podman machine rm -f 2>/dev/null || true

  podman machine init \
    --cpus "$CPUS" \
    --memory "$MEMORY_MIB" \
    --disk-size "$DISK_GIB" \
    --rootful \
    --now

  for _ in $(seq 1 30); do
    if podman_ok; then
      echo "==> Podman machine ready"
      return 0
    fi
    sleep 1
  done
  echo "Podman machine started but API still unreachable" >&2
  podman machine list >&2 || true
  exit 1
}

ensure_machine

echo "==> Building and starting compose stack"
podman compose -f "$COMPOSE_FILE" up --build -d

echo "==> Stack status"
podman compose -f "$COMPOSE_FILE" ps
echo
echo "UI:     http://localhost:8080"
echo "API:    http://localhost:8000/health"
echo "Logs:   podman compose -f deployment/compose.yml logs -f"
echo
echo "Note: if the machine later enters CoreOS emergency mode after an unclean"
echo "stop, re-run this script (it recreates the VM). Prefer 'podman machine stop'"
echo "over killall on gvproxy/vfkit."
