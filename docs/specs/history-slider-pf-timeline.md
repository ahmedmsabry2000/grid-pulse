---
title: History slider and powerflow timeline in web-client
effort: M
type: feature
---

# History slider and powerflow timeline in web-client

## Goal

Operators can scrub a history slider to see network overlay state at time x, and see a timeline that marks when powerflow ran (pipeline ticks with `powerflow.ran` plus on-demand UI runs).

## Acceptance

- [ ] Client buffers Stage 6 telemetry events (WS catch-up + live; optional REST history)
- [ ] History slider selects a tick/time; map overlays reflect that tick’s anomalies (not only the latest)
- [ ] “Live” / follow-latest mode resumes when scrubbed to the end (or via explicit control)
- [ ] Timeline visual marks ticks/moments when powerflow ran (`powerflow.ran === true`) and records manual Run powerflow actions
- [ ] Clicking a timeline marker jumps the history slider to that moment
- [ ] Unit tests for history/time/PF-marker helpers; `npm test` + `npm run build` green
- [ ] ≥1 min healthy local stack smoke before commit/PR

## Notes

- Stacks on deck.gl overlays (#16 / PR #18); do not merge into #18 — separate PR
- No real GIS; Streamlit unchanged
- Prefer existing Stage 6 event contract (`tick_index`, `measurements[].timestamp`, `powerflow.ran`)
