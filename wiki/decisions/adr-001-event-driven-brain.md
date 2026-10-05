---
title: ADR-001: Event-driven brain, scripts as autopilot
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [events, scripts, decision-model]
---

# ADR-001: Event-driven brain, scripts as autopilot

## Context
Calling the decision model every tick for every bot is wasteful: while
traveling or grinding, most ticks are identical. Clef should decide, not
repeat itself.

## Decision
The loop **never** calls Clef "because a tick passed". Two wake-up paths only:

1. **World events** — monster spotted, damage taken, chat heard, item seen,
   party invite, arrival, script failure (see `robots.domain.events`).
2. **Timers / reviews** — randomized timers (ADR-002) and periodic heartbeats.

Between events, the active **behavior script** (`robots.app.scripts`) runs
mechanically: walk, attack, loot, rest. Scripts make zero model calls and are
pure functions of `BotState` → actions, so they're trivially testable.

## Consequences
- Decision-model QPS scales with *interesting things happening*, not with bot count × tick rate.
- The escalation counter + decision counter on the brain give the experiment's headline metric: **LLM escalations per Clef decision**.
- A mob appearing while farming does NOT wake the brain unless the active plan says so (ADR-003).

Related: [[adr-002-randomized-timers]], [[adr-003-farm-plans]], [[decision-flow]]
