---
title: Simulator start/stop from web-client toolbar
effort: M
type: feature
---

# Simulator start/stop from web-client toolbar

## Goal

Let operators start and stop the data simulator from the web-client toolbar without killing the whole stack. History and WebSocket stay readable while the simulator is stopped; ticks resume when started again.

## Acceptance

- [ ] web-server exposes `GET` simulator status and `POST` start/stop that supervise a `gridpulse-simulate` (or equivalent) subprocess writing the same events path the UI already tails
- [ ] Control plane does not mutate system/Docker auth config
- [ ] web-client toolbar shows Running/Stopped next to WS status; disable while a request is in flight; plain-text errors only (no JSON error blobs in the UI)
- [ ] TDD: API tests for start/stop/status; client test that the toggle hits the endpoint
- [ ] Streamlit has no simulator toggle this round

## Notes

- Today there is no start/stop/pause API; simulator is a separate CLI (`gridpulse-simulate`)
- Prefer subprocess supervision over embedding the simulation loop in the API process
- Out of scope: merging PRs; Podman RAM; Dependabot
