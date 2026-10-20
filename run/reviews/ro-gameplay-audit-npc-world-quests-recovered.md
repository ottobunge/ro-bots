# NPC / world / quest audit — cached recovery

Completed bounded synthesis of cached evidence only; not recovery of the original unfinished result. **18 feature rows. No native effects, source edits, retrieval, tests, SQL, services, builds, model calls, installs or Git.**

## Readiness versus gameplay

The reviewed baseline reports Talk/Next/Select/Close and received private NPC memory source readiness (614 prior test executions; parent 4177 tests + 65 subtests, 95.37%). Those gates were not rerun. Native NPC dialogue, rewards and quest/progression acceptance remain **false** (`playing-mvp-native-npc-approved.json:1–20`).

NPC click can attack a PC/MOB on the pinned server (`clif.cpp:12200–12243`). Current source restricts targets to received type 6/12 and guards map, epoch, range, life and movement. Menus retain blank indices and reserve cancel 255. Close is a UI/request state, never proof of quest completion, items or EXP. Numeric/text input stops at `unsupported_input`; buy/sell choice stops at `unsupported_shop` and is not ordinary Select.

## Coverage frontier

| ID | Tier | Stopping point |
|---|---|---|
| `npc.target_safety` | offline_pipeline | Native safe-click behavior unaccepted. |
| `npc.dialogue_cursor` | offline_pipeline | No native dialogue acceptance; close_requested/instructions_received cannot prove quest completion. |
| `npc.received_memory` | offline_pipeline | Memory/guidance is not a quest state machine or earned progression. |
| `npc.numeric_text_input` | missing | Numeric/text submission is unimplemented. |
| `npc.shop_selection` | missing | Shop selector/transactions are unsupported; unsupported_shop has no Close encoder here. |
| `world.public_load_frontier` | offline_model | Public default load does not prove deployed availability. |
| `world.portal_interface` | offline_model | UseWarp exists in domain but native dispatch has no corresponding handler. |
| `world.safe_travel` | offline_pipeline | Movement plumbing is not demonstrated end-to-end safe multi-map travel. |
| `world.kafra_services` | offline_pipeline | Service menus are not accepted storage/cart/save/teleport behaviors. |
| `world.kafra_teleport` | missing | NPC teleport has no accepted effect-correlation/arrival workflow. |
| `world.save_death_return` | missing | Savepoint and server-confirmed death-return lifecycle unaccepted. |
| `world.dungeon_access` | missing | No quest/access-state authority; Nameless hidden flags cannot be fabricated. |
| `world.instances` | missing | No accepted instance lifecycle or cooldown reconciliation. |
| `quest.journal` | missing | Talk support has no authoritative quest journal reducer. |
| `quest.scripted_progression` | missing | No earned-prerequisite/objective state machine; Goal.QUEST or quest memory kind is not implementation. |
| `quest.rewards` | missing | No native NPC reward acceptance; neither text nor close proves anything granted. |
| `quest.starter_frontier` | unknown | No accepted starter route: script load proven but actual initial/earned prerequisites and native reward are unproven. |
| `quest.renewal_eden_frontier` | not_applicable | Cached Renewal leveling guide cannot establish enabled starter quests here. |

## Five priority gaps

1. Typed numeric/text input and real shop selection/transactions missing.
2. No authoritative quest journal/objective/earned-prerequisite state machine.
3. No end-to-end safe multi-map travel or accepted portal/Kafra/save/death-return effects.
4. No native NPC conversation or correlated server-confirmed reward acceptance.
5. No received instance identity/membership/cooldown or dungeon-access lifecycle.

## Public content and safe travel

Authority is pinned rAthena `e985006171d2eb320ee512a653f4c83aea3d81b6`, MAIN20180704/pre-re. The public generator imports `npc/pre-re/scripts_main.conf` (`rathena_runtime.py:155–159`); that root imports common **and** pre-re scripts (`cached fetched-0.txt:28–41`). The cached tree has 522 active public paths. It proves default script reachability, not deployed private overrides, map enablement, prices or live NPC presence. Kafra common functions and common/pre-re placements, Nameless common quests plus pre-re duplicate placements, and Endless Tower must be interpreted together. Renewal Eden is outside that default tree, not universally impossible on a custom deployment.

Touch warps are server effects, not a generic native `UseWarp` action: the domain declares it but native dispatch does not handle it (`actions.py:49–54`; `playing_runtime.py:296–314`). Same-map feedback plumbing does not establish safe multi-map routing. Require each leg arrival, destination/map-load receipt, stale actor/UI invalidation, access/fee checks and bounded failure handling. Kafra teleport must correlate fee/ticket debit with arrival; save text must not stand in for an observed later death-return. Instances additionally need real identity, party eligibility, reservation, entry, cooldown and teardown receipts.

## Starter reward decision

The smallest cached candidate is Shion: the first “Where should I go?” branch sets `nov_1st_cos=1` (`fetched-4.txt:286–329`), and a later eligible conversation grants `getexp 9,0` (`:266–284`). Public inclusion is proved (`fetched-0.txt:37–38`; `fetched-2.txt:18`). **No starter route is accepted**: actual initial flags, prior history, earned first conversation and native EXP receipt are not available. This is an EXP candidate, not a demonstrated item reward. No hidden live coordinates or spawned characters are invented.

## Reward and knowledge boundaries

Require separate server quest/status/objective receipts and correlated inventory/currency/EXP changes, including rejection, capacity, duplicate and concurrent-update cases. Some legacy scripts use hidden variables rather than journal entries (Nameless `fetched-12.txt:68–82` comments out `setquest`), so an empty journal cannot prove no progression. Operator scripts are research evidence only; agents may use their own received pages and actors. Inventory transaction semantics belong to the economy-inventory stream; job/EXP budgets belong to combat-progression; party requirements cross-reference social-guild-woe.

## Evidence limits and deliverables

Cached retrieval records: 25; source ledger entries: 24; digest-checked files: 24; mismatches: 0. An earlier Quest_Window URL returned 404; the cached Quest guide is used instead. Guide descriptions and iRO-specific fees/VIP rules are advice, not pinned deployment mechanics. Negative tests in JSON are requirements, not fresh execution claims. Exact pinned file/cache line ranges, guide locators, mode/config unknowns, support tiers and required receipts are recorded for every row.

- JSON: `run/reviews/ro-gameplay-audit-npc-world-quests-recovered.json`
- Markdown: `run/reviews/ro-gameplay-audit-npc-world-quests-recovered.md`
