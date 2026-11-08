#!/usr/bin/env bash
# Bring up Grid Pulse via Podman Compose with a healthy Podman machine.
# Recovers common macOS failures: missing SSH identity, tiny disk, libkrun
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

mkdir -p "${HOME}/.config/containers"
CONF="${HOME}/.config/containers/containers.conf"
if [[ ! -f "$CONF" ]] || ! grep -q '\[machine\]' "$CONF" 2>/dev/null; then
  cat >>"$CONF" <<EOF

[machine]
provider = "${PROVIDER}"
EOF
elif ! grep -q 'provider' "$CONF"; then
  # shellcheck disable=SC2016
  awk -v p="$PROVIDER" '
    BEGIN{done=0}
    /^\[machine\]/{print; print "provider = \"" p "\""; done=1; next}
    {print}
    END{if(!done) print "[machine]\nprovider = \"" p "\""}
  ' "$CONF" >"${CONF}.tmp" && mv "${CONF}.tmp" "$CONF"
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
  # macOS often uses a per-user folder under /var/folders/.../T/podman
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

  # Give API forwarding a moment after reported start.
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

ensure_anonymous_dockerhub() {
  # Bad/empty docker.io credHelpers in auth.json cause "incorrect username/password"
  # on anonymous Hub pulls. Keep ghcr.io helpers; drop docker.io helpers.
  local auth="${HOME}/.config/containers/auth.json"
  mkdir -p "$(dirname "$auth")"
  python3 - "$auth" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text()) if path.exists() else {}
helpers = dict(data.get("credHelpers") or {})
auths = dict(data.get("auths") or {})
changed = False
for k in list(helpers):
    if "docker.io" in k or "index.docker.io" in k:
        helpers.pop(k)
        changed = True
for k in list(auths):
    if "docker.io" in k or "index.docker.io" in k:
        if not auths[k]:
            auths.pop(k)
            changed = True
data["credHelpers"] = helpers
data["auths"] = auths
if changed or not path.exists():
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"updated {path} for anonymous docker.io pulls")
PY
}

ensure_machine
ensure_anonymous_dockerhub

echo "==> Pre-pulling base images"
podman pull docker.io/library/python:3.12-slim
podman pull docker.io/library/node:20-bookworm-slim
podman pull docker.io/library/nginx:1.27-alpine

echo "==> Building and starting compose stack"
# Isolate from host ~/.docker/config.json credsStore quirks during compose builds.
DOCKER_CONFIG="$(mktemp -d)"
export DOCKER_CONFIG
printf '%s\n' '{}' >"${DOCKER_CONFIG}/config.json"
trap 'rm -rf "${DOCKER_CONFIG}"' EXIT

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
