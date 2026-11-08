---
title: Top-level deployment compose for Docker and Podman
effort: M
type: feature
---

# Top-level deployment compose for Docker and Podman

## Goal

Add a top-level `deployment/` folder with container definitions and a compose file that brings up the full stack with both Docker Compose and Podman Compose / podman-compose. Services: `data-simulator`, `web-server`, `web-client`; Streamlit optional. Shared events volume / networking so simulator → server → client works out of the box.

## Acceptance

- [ ] `deployment/` contains compose + Dockerfiles (or build contexts) for simulator, web-server, web-client
- [ ] Same compose works with `docker compose` and `podman compose` / `podman-compose`
- [ ] Optional Streamlit service documented / profile-gated
- [ ] Shared events volume (or equivalent) so simulator writes are visible to web-server
- [ ] README documents both CLIs with copy-paste up/down commands
- [ ] Client reaches API/WS through compose networking (proxy or env)

## Notes

- Out of scope: Kubernetes / cloud orchestrators
- Compose-first; one place to bring everything up
