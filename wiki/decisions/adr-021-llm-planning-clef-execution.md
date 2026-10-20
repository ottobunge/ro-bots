---
title: "ADR-021: Context-rich LLM planning, CLEF execution"
created: 2026-10-09
updated: 2026-10-09
type: decision
status: accepted
tags: [architecture, decision-model, escalation, scripts, testing]
---

# ADR-021: Context-rich LLM planning, CLEF execution

## Context

The user explicitly requires LLMs to investigate each agent's context and author
objectives and plans, with CLEF making fast execution decisions and escalating
when replanning is needed. Numeric skill receipts without explanations exposed
an important gap: available observations alone do not teach the game's rules.

This decision overrides the plan-authorship portions of
[[adr-003-farm-plans]] and [[adr-011-decision-runtime-strategy]]. Their accepted
historical text is preserved. The event-driven script execution of
[[adr-001-event-driven-brain]] remains in effect. This is an architectural goal,
not a claim that the existing brain implements the new split.

## Decision

1. **LLM planner:** investigates read-only context, proposes a high-level objective
   and structured plan, explains its assumptions, and revises the plan after
   escalation. A swappable planning port is separate from free-form chat.
2. **CLEF executor:** chooses fast actions within a validated active plan using
   current perceptions, plan progress and relevant mechanically prepared context.
   It may request replanning, but does not silently replace the objective.
3. **Deterministic scripts:** perform supported movement, combat, loot and recovery
   between interesting events with zero model calls. A tick alone invokes neither
   model. Existing CLEF-selectable premade phrases remain valid; free-form player
   communication uses the LLM.
4. **Investigation tools:** provide the agent's character state, skills/items/rules,
   known maps/navigation, received NPC/quest information, private memories,
   relationships, schedules and prior plan outcomes. Tools bind to that agent and
   world; no other agent's memories, hidden live populations or privileged server
   state may fill missing observations.
5. **Context availability:** make relevant information discoverable through
   bounded searches, lookups and zoom, not an unbounded prompt dump. Preserve
   UNKNOWN values, freshness and provenance. Public rules, private experience and
   current native state are distinct sources. Mechanics are computed outside the
   models; descriptive prose does not establish casting/spending permission.
6. **Plan contract:** carry identity/ruleset, objective/reason, prerequisites,
   destination/targets, ordered phases, observable success/progress, duration/review
   deadline, safety limits, fallbacks and replanning conditions. Plans are data,
   not arbitrary executable code or direct native commands.
7. **Admission:** validate capabilities, mechanics, current resources and applicable
   rules before acceptance. Revalidate action prerequisites during execution.
   Reject unsupported plans, foreign identities and stale responses. Caller labels
   and source hashes alone do not establish native resource authority.
8. **Replanning lifecycle:** one in-flight request per agent, bounded/coalesced
   reasons and retries, cooldowns and timeouts. Maintain transport/keepalive and
   safe supported fallback while planning is pending; never block the native
   maintenance loop on a slow LLM call.
9. **Continuity and observability:** retain/revalidate plans across supported
   reconnect/restart, expose progress, revisions, consulted evidence and escalation
   reasons through the real dashboard contract. Distinguish LLM planning/chat,
   CLEF decisions and scripted actions in instrumentation.

## Finite acceptance

- A real LLM uses investigation tools and proposes a mechanically admitted plan
  using only that agent's permitted context.
- CLEF/scripts execute supported native actions and produce observed progress;
  routine execution does not call the LLM on every tick/action.
- A controlled failure or changed situation generates an evidenced escalation;
  a subsequent validated plan changes behavior. Duplicate escalation is bounded.
- Tests prove isolation, unknown/stale-state handling, invalid-plan rejection,
  single-flight/retry limits and safe pending behavior.
- Plan persistence/dashboard integration are exercised through actual consumers,
  not synthetic feed events or logged command intent alone.
- Strict vertical TDD, independent completed-snapshot review, unchanged quality
  thresholds and separately scoped native verification apply.

## Boundaries and implementation state

Subgoal 11 is **OPEN**. Plan/tool ports, provider adapters, brain/scheduled-host
wiring, native progress, persistence/dashboard controls and instrumentation remain
to be implemented or verified. The first slice is an offline typed plan admission
and bounded replanning lifecycle; it cannot alone close this decision.

This does not select the unresolved literal-versus-scaled UniiChat adoption policy,
migrate journals, expand provider context sizes, purchase services, alter server
worlds, or authorize fresh native effects. Preserve all earlier goals and the
safeguards of [[adr-018-trusted-user-local-workspace]] and
[[adr-020-pinned-protocol-gameplay-first]]. Acceptance is tracked in [[goals-ledger]].
