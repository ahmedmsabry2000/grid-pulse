---
title: Live deck.gl overlays for WS anomalies and ratings
effort: M
type: feature
---

# Live deck.gl overlays for WS anomalies and ratings

## Goal

Make `web-client` deck.gl react to streamed WebSocket telemetry: overlay measurement anomalies, powerflow-output / PF-result anomalies, and rating exceedances on the network map, and fit/snap the camera to network bounds on load and network change.

## Acceptance

- [ ] WS telemetry updates layer state (not only a tick list in the side panel)
- [ ] Distinct visual encoding for measurement anomalies, PF-output anomalies (`pf_residual` reserved / powerflow-related), and rating exceedances
- [ ] Bus- and line-/element-scoped overlays map from anomaly `signal_id` onto topology features when possible
- [ ] Camera `fitBounds` (or equivalent OrthographicView target/zoom) on topology load and when the selected network changes
- [ ] Unit/smoke tests for overlay mapping / bounds helpers; `npm test` and `npm run build` green

## Notes

- No real GIS; keep synthetic OrthographicView coords
- Streamlit unchanged
- Prefer existing Stage 6 anomaly event contract from WS JSONL fanout
