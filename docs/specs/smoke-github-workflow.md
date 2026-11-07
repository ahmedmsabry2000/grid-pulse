---
title: Smoke GitHub Spec→Issue→Project workflow
effort: S
type: feature
---

# Smoke GitHub Spec→Issue→Project workflow

## Goal

Verify `scripts/github/new-issue-from-spec.sh` creates an Issue on the **Grid Pulse** Project board with Effort=S and Status=Todo.

## Acceptance

- [x] Issue created from this Spec
- [x] Labels `effort:S` and `type:feature` applied
- [x] Issue appears on Project **Grid Pulse**

## Notes

Smoke only — no product code change required.

- Issue: https://github.com/ahmedmsabry2000/grid-pulse/issues/1
- Project: https://github.com/users/ahmedmsabry2000/projects/4
- Status exercised: Todo → In Progress → Done (Issue left open).
