---
title: First host-connected LLM planning segment
created: 2026-10-09
updated: 2026-10-09
type: guide
status: proposed
tags: [architecture, llm, testing, ops]
---

# First host-connected LLM planning segment

Implements the first bounded runtime slice of [[adr-021-llm-planning-clef-execution]].
Acceptance remains in [[goals-ledger]]; this is not permission to activate a live world.

## Finite acceptance boundary

Wire the production planner into the actual host in explicit opt-in mode. Initially
support passive IDLE and persistent REST on the agent's current received map only.
The LLM investigates and authors plans; CLEF makes bounded execution/safety/replan
choices without replacing the objective or phases. Mechanical steps make no model
calls. Preserve the existing legacy default without the opt-in flag.

The read-only frontier reproduced actual ScheduledAgent -> PlayingClient pickup
requests during a hypothetical planning-pending state. Keepalive continued, so an
empty action tuple is insufficient. Disable mechanical loot/patrol/NPC fallback for
all opt-in states, including pending/invalid and empty admitted idle/rest outcomes.
Do not use the moving IdleTownScript as passive idle or fall back to GrindScript.

## Offline implementation policies

- Capture job context on the serialized host owner thread, independently of fresh
  admission/execution validation. No worker receives live native callbacks, journal
  stores, or another agent's memory.
- Maximum 64 private notes and 8,192 bytes of their text; maximum 32,768 serialized
  UTF-8 bytes for the complete job. These are capture ceilings, not model-context
  expansion. Existing rendered-token admission and the 4,096-token ceiling remain.
- Capture the whole bounded note prefix with stable source IDs. If memory exceeds
  a bound or its lock is contended, private memory is UNKNOWN, not empty/complete.
  Do not truncate notes, renumber IDs, block the native tick, summarize, migrate,
  or read private live journals for implementation tests.
- Deeply separate mutable state containers from the live host; immutable outer
  dataclasses alone do not protect inventory and encounter dictionaries.
- One physical planning worker and one completion slot per agent. Four model calls
  maximum, 30-second provider transport timeout, 120-second logical planning wait,
  and a one-second shutdown join bound. No provider configuration is changed here.
- Logical timeout/session invalidation never establishes physical cancellation.
  Retain worker ownership and refuse replacement/reconnect until termination is
  confirmed. An unsuccessful join remains unresolved, not successful cleanup.
- Keep lifecycle mutation, current identity/capability validation and plan install
  on the host thread. A captured capability snapshot is advisory, not fresh native
  action authority. Drain received events and keepalive while planning waits.

## Required offline evidence

Six named cases in `run/reviews/llm-planning-host-integration-frontier.json` cover:
construction without effects and unchanged defaults; blocked-provider event drain
and keepalive; suppression of loot/patrol/NPC fallback; owner/session/fresh-capability
admission; typed idle/rest with CLEF execution and bounded replanning; and actual
thread/cleanup ownership. Snapshot isolation and contention/budget cases accompany
these paths. Preserve vertical RED/GREEN history, independently review the completed
snapshot, and run unchanged full quality/audit gates before any acceptance label.

## Exclusions

No real inference, native sessions, SQL, Docker, service modifications, private live
journal/config access, context expansion, memory migration or live flag activation.
Free-form planning chat, farming/progression, dashboard persistence, schedules/social
scope and both-ruleset native acceptance remain separate open work. The previous
format/provider repair budgets and consumed one-rerun grant are not reset.

The bounded real-model evidence is synthetic-context admission with an explicitly
preserved final report-serialization failure and exact offline replay—not observed
host execution or game progress. See [[gameplay-coverage-roadmap]] for broader gaps.
