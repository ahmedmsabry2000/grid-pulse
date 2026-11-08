---
title: Introduce PNetwork domain type in packages/gridpulse
effort: M
type: feature
---

# Introduce PNetwork domain type in packages/gridpulse

## Goal

Make `PNetwork` the foundational domain type in `packages/gridpulse`: wrap a pandapower net plus a corresponding NetworkX graph, and migrate public APIs so callers take/return `PNetwork` instead of mutating raw pandapower nets.

## Acceptance

- [ ] `gridpulse.network.PNetwork` wraps pandapower net + NetworkX graph; graph stays in sync with topology
- [ ] `load_network(...)` returns `PNetwork` (isolated copies); registry/list APIs unchanged in spirit
- [ ] Public mutation of pandapower state happens only via `PNetwork` methods (apply measurements, run powerflow, copy)
- [ ] Pipeline, simulator, powerflow, layout, rating, and quality gate consume `PNetwork` (not raw nets at public boundaries)
- [ ] Layout uses the NetworkX graph from `PNetwork`
- [ ] Pytest coverage for construction, isolation, graph sync, and migrated call sites stays green

## Notes

- Default network remains IEEE case14; loader stays pluggable
- Reading PF result tables for detectors may go through controlled accessors; no external `net.load.at[...]` mutation
- Stacked with rules / deck / deployment Issues; this Issue is core-only
