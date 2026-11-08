---
title: Monorepo and per-minirepo Cursor rules cleanup
effort: S
type: feature
---

# Monorepo and per-minirepo Cursor rules cleanup

## Goal

Replace the noisy single pile of root Cursor rules with short monorepo root rules plus per-minirepo `.cursor/rules/` for `packages/gridpulse`, `data-simulator`, `streamlit-app`, `web-server`, and `web-client`. Delete obsolete or conflicting root rules.

## Acceptance

- [ ] Root `.cursor/rules/` is short (project identity, TDD, GitHub Spec workflow, commits) — no minirepo-specific detail piles
- [ ] Each minirepo has its own `.cursor/rules/` with scoped alwaysApply guidance
- [ ] Obsolete/conflicting root rules removed or folded into the short root set / minirepo rules
- [ ] `AGENT.md` points agents at root + per-minirepo rules

## Notes

- Subtract before add: delete/consolidate before writing new minirepo rules
- Skills under `.cursor/skills/` may stay; this Spec is rules-focused
