---
name: gridpulse-tdd
description: Red-green-refactor playbook and pytest patterns for Grid Pulse.
---

# Grid Pulse TDD

## When to use

Before writing or changing production code in `packages/gridpulse/` (or other minirepos).

## Playbook

1. Write a failing test under `tests/unit/` or `tests/integration/` that names the behavior.
2. Run `uv run pytest` and confirm red (failure is the intended missing behavior, not import noise unless Stage 0).
3. Implement the smallest production change to go green.
4. Refactor with tests still green.
5. Stage exit: all tests green; then local commit + stage note.

## Patterns

- Prefer fixtures for nets, samples, and seeded RNG.
- Seed synthetic telemetry for reproducibility.
- Integration tests cover `run_tick` / `run_batch` and JSONL contracts.
- Do not advance stages with red tests.
