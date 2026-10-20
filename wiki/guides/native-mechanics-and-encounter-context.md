---
title: Native mechanics and encounter context
created: 2026-10-07
updated: 2026-10-08
type: guide
status: proposed
tags: [protocol, rathena, decision-model, testing]
---

# Native mechanics and encounter context

## Acceptance boundary

Criteria 9 and 10 extend [[goals-ledger]]. Agents must distinguish their planned
[[adr-009-character-builds-item-cognition]] from received current character state.
Public rule cards can explain mechanics, but cannot establish learned skills,
current equipment, free points or legal success of an action.

The source-to-request audit is
`run/reviews/playing-mvp-native-character-context-audit.json`, SHA-256
`05a9e1c4956e98bdcd19b30fddd4a5a6051303adbdef88c656ce227fd168d233`.
The parent checked all 14 recorded stable source hashes. The source/profile is
rAthena `e985006171d2eb320ee512a653f4c83aea3d81b6`, MAIN 20180704/pre-Renewal.
No new native sessions, SQL queries, point allocations or equipment/skill requests
were made by the audit.

## What is missing

| Field | Existing observation | Current gap |
|---|---|---|
| Base stats and aggregate bonuses | BD/141 frames occurred in the real run | No current typed retention or Clef projection; bonus attribution to equipment is not established |
| Stat/skill free points and next cost | Source identifies B0 parameters and cost packets | Zero must differ from unknown; BE/BC framing and targeted layouts need separate admission |
| Learned skills | Existing skill-family framing | No complete current skill snapshot/delta/deletion view in the request |
| Equipped indices and item details | Inventory quantities are projected | Item identity, inventory index, WearState and effect knowledge must remain distinct |
| Observed monster species | Runtime has an appearance/job-field mapping | Targeted full-header signed-int16 job@23 proof and typed helper are approved; ordered request integration is running |
| Damage at encounter level | Real positive SELF hit receipts are retained | Earlier receipts lack species/own-level bindings and stay unknown; the new ordered pipeline must capture future facts at receipt |
| Stat/equip/skill actions | Source names legal checks and requests | No acknowledged, mechanically validated actuator path is accepted |

The complete audit holds precise pinned source paths/line ranges and distinguishes
source-derived offsets from executed compiler results. These entries are not new
layout approvals or native telemetry receipts.

## First implementation slice

`playing-mvp-native-encounter-context-scope.json` permits a **new pure component**:

1. Execute targeted full unchanged-header measurements of the three active actor
   shapes, including the appearance/job field used for observed species.
2. Build immutable encounter facts from received SELF damage, observed eligible
   actor/species and the bot's received level/provenance **at the hit**.
3. Bound facts per agent/session and retain unknown/missing joins. A later species
   appearance or level cannot rewrite an uncaptured historical encounter.
4. Cover actor reuse, vanish, epoch changes, SELF aliases, unsupported actor
   presentations, malformed frames and serialization budgets with vertical TDD.

The implementation owns only a new adapter, new tests and its report. It does
not edit REST-review-frozen runtime/model/request files, perform new inference,
open native sessions, or allocate points. Runtime integration is a later explicit
step after the reviewed snapshot is released.

## Current integration and next stat fields

The pure helper and its cursor repair are now independently approved. The new
`playing-mvp-native-encounter-request-integration-scope.json` explicitly authorizes
an ordered received-frame stream through PlayingClient, BotState and the real
request builder. It must capture level/species **before or at the hit**, clear
actor joins on vanish/map/gap/epoch boundaries, and never repair old facts using
later native levels, persona state or SQL. This implementation is running; no
new native encounter/request receipt is accepted yet.

While that source slice runs, an independent offline compiler measurement is
recorded in `playing-mvp-native-character-stat-field-oracles.json`. Both GCC and
Clang compiled and executed full unchanged configured headers after immutable
source/profile/CPPFLAGS validation. They agree on:

- `0x00BD`: packed 44-byte ZC_STATUS; point unsigned16@2; six uint8 base/cost
  pairs occupy offsets 4 through 15.
- `0x0141`: packed 14-byte ZC_COUPLESTATUS; stat ID unsigned32@2; base and
  aggregate bonus **signed32** at offsets 6 and 10.
- `0x00B0`: packed eight-byte ZC_PAR_CHANGE; parameter unsigned16@2 and
  signed32 count@4. The compiled stat/skill free-point IDs are 9/12;
  STR/AGI/VIT/INT/DEX/LUK IDs are 13 through 18.

All three are already framed at those lengths. A subsequent guarded passive
native capture, `playing-mvp-passive-character-stats.json`, received BD once,
141 twelve times and B0 nineteen times **for each existing fixture**. Both
identity-matched readers stayed healthy; supported teardown and exact SQL
both-offline readback passed in 4.136 seconds. No gameplay requests, inference,
point allocations, new accounts or operator SQL mutations were performed.

At that capture, both fixtures had:

- STR/AGI/VIT/INT/DEX/LUK: received base **1**, aggregate bonus **+1**, next
  allocation cost **2** for each.
- Received available stat points **0** and skill points **0**. These are actual
  zeros, not missing-field defaults or derived from their nominal level.

These values do not identify the source of each bonus or prove why an earlier
attack dealt one damage. They do establish that allocating points cannot be
assumed available. Current production retention, invalidation and model-request
projection remain the next stat slice. BE/BC responses and legal actuation stay
unaccepted; ordinary server session bookkeeping is not an operator SQL mutation.

## Public knowledge and private memory

The bounded rules-knowledge pilot is separate from this component and from
[[adr-004-isolated-agents-optchat-memory]]. Its source cards are advisory,
ruleset/revision tagged and byte bounded. The existing MechanicsPort and
YamlMechanics remain the starting point for deterministic legal item/skill
knowledge, with their currently documented unsupported effects left unknown.

All six milestones remain open. Received combat hits are progress, not proof of
XP, loot, a sustained population, current stat/gear awareness or safe actuation.
