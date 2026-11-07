---
title: Powerflow snapshot pages UI
effort: M
type: feature
---

# Powerflow snapshot pages UI

## Goal

Replace the single expanding powerflow result view with **immutable snapshot pages**: each **Run powerflow** click freezes the stream data up to that moment plus PF / rating / ensemble results. The live simulator tail only feeds the *next* click. Show one multi-series Plotly chart (all channels, colored traces + legend) with no channel dropdown; navigate prior PF panels with prev/next (default: latest).

## Acceptance

- [ ] Each **Run powerflow** appends an immutable snapshot to `session_state.snapshots` holding a deep copy of stream events up to the click plus PF / rating / ensemble panel payloads
- [ ] Live JSONL appends without a new click do **not** mutate prior snapshot payloads or grow a single expanding PF result table
- [ ] One Plotly graph: every measurement channel as a differently colored trace with a legend; **no** channel `selectbox` / dropdown
- [ ] PF result panels (gate / rating / ensemble) default to the **latest** snapshot; prev/next (or tabs) navigate older snapshots — not a channel picker
- [ ] No events-path prompt or upload (fixed path / `GRIDPULSE_EVENTS_PATH` only; unchanged)
- [ ] Tests: multi-series traces present; click adds a snapshot; live append without click leaves prior snapshot payloads unchanged
- [ ] `AGENT.md` updated if the two-process UX / Run powerflow steps change

## Notes

- Out of scope: persisting snapshots across Streamlit restarts; changing the two-process simulator model; events path picker
- Snapshot navigation is for PF panels only; the live chart continues to auto-tail
- Rating exceedance and ensemble anomalies remain orthogonal lists within each snapshot
- Expected files: `src/gridpulse/ui/snapshots.py` (or equivalent), `plots.py` multi-series helper, `app.py`, tests under `tests/unit/`, optional `AGENT.md`
