---
name: gridpulse-stage-workflow
description: Next stage selection, stage notes, and tracker handoff for Grid Pulse.
---

# Grid Pulse stage workflow

## Per stage

1. Read Project store stage note for previous stage + master plan exit criteria.
2. TDD the stage until green.
3. Local commit with stage-scoped message.
4. Write `docs/stages/stage-N.md` in the Project store: what landed, how to verify.
5. Report branch, commit SHA, pytest summary to coordinator.

## Notes path

Project store: `docs/stages/stage-N.md` (mapped from `/cursor/stores/self/docs/stages/`).

## Do not

- Edit the operator plan artifact.
- Push remotes unless asked.
- Skip stage notes or advance with red tests.
