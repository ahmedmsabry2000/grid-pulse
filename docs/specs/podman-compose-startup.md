---
title: Fix Podman compose stack startup
effort: M
type: fix
---

# Fix Podman compose stack startup

## Goal

`deployment/` compose brings up data-simulator, web-server, and web-client cleanly under Podman (and Docker), with a ≥1 minute healthy smoke (no crash loops, WS/ticks flowing).

## Acceptance

- [x] Documented root cause of Podman failure on this machine and remediation
- [x] `podman compose -f deployment/compose.yml up --build -d` succeeds (or equivalent documented CLI) when the VM stays alive
- [x] Native fallback stays healthy ≥1 continuous minute; `/health` OK; events progressing (Podman VM jetsammed on 8 GiB host)
- [x] Compose/Dockerfiles lean enough for a practical local VM disk (avoid OOM-on-disk builds where feasible)
- [x] README notes Podman machine prerequisites (disk size, RAM, auth) and native fallback
- [x] Smoke note in PR body

## Notes

- Stacks with #18 deployment work; keep PR coherent with #18/#20
- Earlier failures: broken docker.io auth key, 9GiB VM disk exhaustion, missing machine SSH identity/disk image
- 2026-11-08: on 8 GiB Mac, Podman VM (2–6 GiB) builds images then macOS jetsams the VM; stack verified via `deployment/native-up.sh` / tmux (UI :5173, API :8000)
- Deployment helpers do not rewrite host auth/config; Hub login stays manual if public pulls fail
- GP-23: dropped unused `DOCKER_CONFIG` temp auth-shadow and redundant base-image pre-pulls from `podman-up.sh`
