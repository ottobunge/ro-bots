---
title: ADR-003: Clef-authored farm plans with custom interrupts
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [decision-model, events, scripts]
---

# ADR-003: Clef-authored farm plans with custom interrupts

## Decision
When a goal review chooses farming, Clef **authors a plan**, not just a step:

- `farm_duration` (score: Short/Medium/Long → 5/15/30 min) — how long the session runs.
- `farm_target` (choice over the map's mob DB entries) — what to kill.
- The plan carries an **interrupt threshold**: while farming, `MonsterSpotted`
  events wake the brain only if the mob is an **MVP** or **≥ bot level + 10**
  (margin constant `INTERRUPT_LEVEL_MARGIN`). Everything else is beneath the
  plan's notice — the `FarmScript` ignores it without a model call.
- Mob data comes from the `MobDatabase` port (rAthena mob_db via adapter).
- `PlanExpired` (ADR-002's `OnceTimer`) ends the session; the next heartbeat
  re-reviews the goal.

## Consequences
- The interrupt system is **configurable by the decision model itself** — Clef
  effectively decides what deserves its own attention.
- Unknown mobs always interrupt (fail-safe).
- Farming QPS drops to ~zero until something notable happens.

Related: [[adr-001-event-driven-brain]], [[adr-002-randomized-timers]], [[decision-flow]]
