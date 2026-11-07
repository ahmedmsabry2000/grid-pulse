---
name: gridpulse-github-workflow
description: Spec → GitHub Issue → Project board → implement for Grid Pulse using scripts/github.
---

# Grid Pulse GitHub workflow

## Rule

Fill a Spec, then run the scripts. Never hand-roll `gh` / GraphQL when a script under `scripts/github/` exists.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/github/bootstrap-project.sh` | Create Project **Grid Pulse** if missing; Effort S/M/L; Status Todo/In Progress/Done; labels `effort:S\|M\|L`, `type:feature\|fix` |
| `scripts/github/new-issue-from-spec.sh <spec.md>` | Create Issue from Spec, label, add to Project, Effort + Status=Todo |
| `scripts/github/project-set-status.sh <n> <Todo\|In Progress\|Done>` | Move Issue status on the board |

## Spec

Copy `docs/specs/_template.md`. Required frontmatter: `title`, `effort` (S/M/L), `type` (feature|fix).

## Flow

1. Write Spec under `docs/specs/`.
2. `scripts/github/new-issue-from-spec.sh docs/specs/<name>.md`
3. `scripts/github/project-set-status.sh <n> "In Progress"`
4. Implement on a `cursor/<name>-f9a7` branch; TDD; commit; push; open PR if needed.
5. `scripts/github/project-set-status.sh <n> Done` (and close Issue when shipped).

## Auth

If scripts fail on Projects scopes: `gh auth login` then `gh auth refresh -h github.com -s project,read:project`.
