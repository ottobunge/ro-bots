# Wiki Schema — ro-bots

## Domain
Design decisions, architecture records, and operational learnings for the
ro-bots experiment: Clef-driven bot players inside a private rAthena server.
This wiki **drives the code**: the architecture (ADR-000), the decision-flow
(ADR-001), the interrupt system (ADR-002) and the farm-plan model (ADR-003)
are normative — when code and wiki disagree, one of them is wrong and must be
reconciled before merging.

## Conventions
- File names: lowercase, hyphens (e.g. `adr-002-interrupt-system.md`)
- ADRs live in `decisions/`, numbered `adr-NNN-slug.md`, and are **immutable
  once accepted** — to change a decision, write a new ADR that supersedes the
  old one and mark the old frontmatter `status: superseded by [[adr-NNN-…]]`
- Concepts and how-tos live in `concepts/` and `guides/`
- Every page starts with YAML frontmatter; every page links out to ≥2 others
- `[[wikilinks]]` between pages; mermaid fenced blocks for diagrams
- Bump `updated:` on every edit; append every action to `log.md`

## Frontmatter
```yaml
---
title: ...
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: decision | concept | guide
status: proposed | accepted | superseded
tags: [...]
---
```

## Tag Taxonomy
- architecture, decision-model, escalation, events, timers, scripts
- protocol, rathena, clef, llm, testing, ops

## Page Thresholds
- One ADR per *decision* (not per feature). Keep them small and final.
- Concepts can be living documents; ADRs cannot.
- Split pages over 200 lines.
