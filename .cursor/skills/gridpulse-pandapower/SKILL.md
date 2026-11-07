---
name: gridpulse-pandapower
description: Network load, powerflow run, and non-convergence handling for Grid Pulse.
---

# Grid Pulse pandapower

## Network loader

- API: `load_network(name_or_path="case14")`.
- Default: IEEE case14. Return an **isolated copy** so callers cannot mutate the registry.
- Unknown id → raise a clear error. Registry must allow stub/registered extras for extensibility.

## Powerflow

- Run only after `PowerflowGate` returns Run.
- Result must include `converged: bool`. Non-convergence is a clean failure, not success.
- Do not mutate the shared registry net; work on copies.

## Non-convergence

- Catch / check pandapower convergence flags; surface structured failure for pipeline decision records.
