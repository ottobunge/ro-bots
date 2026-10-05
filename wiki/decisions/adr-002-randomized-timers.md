---
title: ADR-002: Randomized timers as time-based triggers
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [timers, events]
---

# ADR-002: Randomized timers as time-based triggers

## Decision
Time-based triggers are **event sources** (`TimerFired`) drawn from a random
range, not fixed intervals. Canonical example: "time since last action"
(`idle_review_timer`) fires after a delay uniform in **[5, 20] minutes**.

- `RandomTimer` — recurring, re-randomizes after every fire → each bot has
  its own phase; crowds of bots never review goals in lockstep.
- `OnceTimer` — single-shot (e.g. `plan_expiry_timer` fires `PlanExpired`
  when a Clef-chosen farming duration runs out).
- `TimerSet` — per-bot collection, polled once per loop tick by the runner.

## Consequences
- Deterministic in tests: inject a `FakeClock` + seeded `random.Random`.
- Human-like irregularity for free — no two bots behave on the same rhythm.

Related: [[adr-001-event-driven-brain]], [[adr-003-farm-plans]]
