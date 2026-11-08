---
title: Operator UX — no JSON panels
effort: M
type: feature
---

# Operator UX — no JSON panels

## Goal

Replace raw JSON dumps in the web-client right aside and Streamlit powerflow panels with operator-readable summaries, tables, and badges. Operators must never see curly-brace JSON in either UI.

## Acceptance

- [ ] `web-client/src/App.tsx` has no `<pre>+JSON.stringify` (or equivalent raw JSON rendering) for selected tick, anomalies, on-demand powerflow, rating, or ensemble
- [ ] Selected tick shows a one-line plain summary (time, tick id, network/gate/PF status, anomaly count)
- [ ] Anomalies render as typed rows with legend-style badges (reuse `overlays.ts` classifiers), bus/line id, score/reason
- [ ] On-demand PF shows status + key metrics + exceedance-oriented rows (not a JSON blob)
- [ ] Rating panel is an asset loading table, worst first
- [ ] Ensemble panel is a flat detector score list (no nested cells)
- [ ] Streamlit `gridpulse.ui.app` flattens anomaly/ensemble tables (no raw-dict dataframes, no nested `member_scores` cells); Plotly charts stay
- [ ] Vitest covers formatters/presenters; no JSON visible in operator panels

## Notes

- Map, history slider, and PF timeline stay as-is
- Adapters only — no WS event schema changes
- Out of scope: deck.gl redesign; Streamlit simulator toggle
