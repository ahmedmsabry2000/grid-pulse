---
title: Live data-simulator and UI powerflow
effort: L
type: feature
---

# Live data-simulator and UI powerflow

## Goal

Add a continuous data-simulator as a **separate OS process** that appends sparse (default) or full-coverage synthetic ticks with sprinkled measurement anomalies to a fixed `events.jsonl` path, and evolve the Streamlit UI to auto-tail that file with a **Run powerflow** button that shows rating exceedances and ensemble anomalies as orthogonal panels — without any events-file path prompt or upload.

## Acceptance

- [ ] Events path is fixed: `events.jsonl` in process cwd, overridable only by `GRIDPULSE_EVENTS_PATH`; UI never prompts for path or upload (read-only path label only)
- [ ] Simulator runs as a separate OS process (`gridpulse-simulate` or `gridpulse simulate`); UI must not spawn or embed the simulator
- [ ] Default sparse meters: each tick reports a random subset of channels; missing channels are omitted (not fabricated); `--full-coverage` forces every channel every tick
- [ ] Continuous append with `--interval`, `--inject-rate`, and `--seed`; append does not truncate the file
- [ ] Simulator writes pipeline-compatible JSONL via `run_tick` so gate / PF / rating / ensemble detectors appear in-file
- [ ] UI auto-tails the fixed path; **Run powerflow** uses the **latest** tick → panels for rating exceedances and ensemble anomalies (orthogonal); gate skip / non-converge messaging when applicable
- [ ] Tests: sparse omits channels; full_coverage includes all; inject produces anomaly-typed events through the pipeline; append does not truncate; UI path resolution has no prompt
- [ ] `AGENT.md` documents the two-process run (simulator terminal + Streamlit terminal)

## Notes

- Out of scope: in-app start/stop of the simulator; real SCADA adapters; supervisord/systemd packaging
- Shared coupling between processes is only the events file path
- Rating exceedance and ensemble anomalies remain independent signals (see `docs/specs/rating-exceedance.md`)
- Expected files: `src/gridpulse/simulator/`, CLI entry in `pyproject.toml`, `src/gridpulse/ui/app.py` + path helper, tests under `tests/unit/`, `AGENT.md`
