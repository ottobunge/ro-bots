---
title: Completion roadmap — RO Bots
created: 2026-10-12
updated: 2026-10-13
type: guide
status: accepted
tags: [ops, testing, architecture]
---

# Completion roadmap

Source of detailed acceptance: [[goals-ledger]]. Design split:
[[adr-021-llm-planning-clef-execution]]. This is a finite delivery roadmap, not
an assertion that the existing offline components have passed live acceptance.

## Current point: 1.5 — human joinability and wider world acceptance

- **1.3 recovery gate passed:** one guarded start restored the owned map server.
  All four roles are running with parser/reciprocal peer checks; both owned fixtures
  are offline 0/0. DB, login and char lifetimes are unchanged. The new map startup
  has no new errors; historical DB/table/asset faults remain archived, not erased.
- **1.4 PASSED — narrow first native loop:** the reviewed ready-prompt policy passed
  matching full gates (5,609 unique tests +65 subtests, 95.57% coverage; check/audit0).
  One separately scoped live invocation recognized the named NPC, opened dialogue,
  completed two actual LLM calls (investigate + plan), admitted the proposal, received
  one CLEF execution decision, issued one NEXT response and observed newer matching
  same-open UI progress. Supported cleanup and exact offline readback passed; no
  owner retained. Activation was revoked after the single attempt. Receipt:
  `run/reviews/first-native-llm-clef-npc-loop-verified.json`.
  This does not establish completed dialogue, quest rewards, equipment, XP, human
  playability or sustained population. Canonical operators/data remain under `.work/`.
- **1.5 CURRENT:** qualify the user-approved uaRO-inspired starting baseline and
  supported human client/server pairing. Add missing server-side content incrementally;
  do not require a perfect clone or insist on an unavailable legacy client. Preserve
  current world/data until a successor profile is concretely qualified. See
  [[uaro-inspired-baseline]]. Wider human/lifecycle/E2E acceptance remains open.

All full milestones remain open. Server recovery is not bots playing, an NPC
response is not reward/equipment acquisition, and no gameplay activation is inferred
from import, test or HTTP-health results.

## Roadmap to completion

| Point | Deliverable and exit gate | Coverage | Status |
|---|---|---|---|
| **1 — CURRENT** | Safe isolated, human-joinable world; supported normal lifecycle; first observed LLM -> CLEF -> NPC loop. | Milestone 1; native prerequisite for milestone 2 and subgoal 11. | In progress at **1.5**; narrow native loop passed. |
| 2 | Ordinary NPC preparation; legal stats/skills/equipment; movement, damage, survival, XP, targeted loot, economy, chat, basic party and schedules observed in real play. | Milestone 2; criteria 4/9; subgoal 11. | Open; existing offline pieces and partial historical native evidence. |
| 3 | Per-agent isolated durable memory, actual reconnect/restart continuity, multiple characters/builds and overlapping schedules; human contribution observations. | Milestone 3; criteria 1/2/4/9. | Open; live persistence and contribution acceptance pending. |
| 4 | Friend-group/outsider coordination, contribution-based relationships, attenuated gossip/reputation, guild formation and WoE observed in game. | Milestone 4; criteria 1/2. | Open; policy models are not live acceptance. |
| 5 | Dashboard creates real accounts/characters/workers; edits, schedules and force actions affect live agents; Rust/browser inspector shows goals, builds, characters, events and private owner memories. | Milestone 5; criterion 3. | Open; runtime population/control frontier being mapped in parallel. |
| 6 | Mechanically valid, source-grounded builds and acquisition for Renewal and pre-Renewal; bounded discoverable public game rules alongside private experience, with current HP/SP/stats/skills/equipment/encounter context. | Milestone 6; criteria 4/7/9/10. | Open; both-ruleset progression/acquisition unaccepted. |
| 7 | Repeatable clean E2E/playground; debug/test/named-production volume isolation; human playtest; sustained believable populations; comparable Framework GPU, Cloudflare and Heavengraph GPU benchmarks. | Milestones 1/6; criteria 5/6/8; final gate for all criteria. | Open. |

All six full milestones and all added criteria remain open until their real exit
criteria are observed. A passing test total does not move a live milestone to done.

## Worker lanes

Use multiple bounded workers in parallel when ownership is disjoint:

1. Maintenance/native integration on the critical path.
2. Existing provider readiness and later benchmark qualification.
3. Dashboard/population/control integration.
4. Independent completed-snapshot review when a candidate is ready.
5. Additional progression, memory or social slices when their dependencies permit.

The coordinator owns integration, fresh operational checks, evidence reconciliation
and this roadmap. Do not let parallel workers modify another worker's files or
frozen source. Do not start a second world operator against the same fixture lock.

## Hourly report contract

Each report states:

- Local timestamp and **current point** (for example, 1.2).
- Verified changes since the previous report; explicitly say when none are verified.
- Worker lanes and last verified state; do not claim stale dispatches are running.
- Current technical blocker, next concrete exit gate, and a compact roadmap table.
- What remains unverified; no invented completion percentage or ETA.

Use `run/reviews/project-roadmap-status.json`, this page, the latest scoped reports
and [[log]] as read-only evidence. Report live results separately from synthetic,
offline, HTTP-health and historical results. Never include secret values or
connection strings; redact as `[REDACTED]`. Continue routine project work autonomously.
