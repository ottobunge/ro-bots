# Ragnarok agent gameplay coverage audit

Compiled **104 unique requirement rows** from five recovered research reports. These are candidate mechanic families, not proof that every enabled server feature has been inventoried or that any broad gameplay milestone is complete.

## Current support classification

| Classification | Requirement rows |
|---|---:|
| codec_only | 7 |
| missing | 55 |
| native_primitive_verified | 5 |
| not_applicable | 1 |
| offline_model | 10 |
| offline_pipeline | 12 |
| unknown | 14 |

Only five rows have historical **native primitive** evidence: observed targeting/approach, normal attack damage, current-epoch inventory completion, public chat and party membership. None is labelled native_behavior_verified. Each has limits and requires broader acceptance.

## Verified operator/code observations

- Current typed action union lacks item-use, equip/unequip, stat/skill spending and shop transactions (`src/robots/domain/actions.py`).
- Session progression currently accepts only raw job 0 / Novice. Class templates do not make other jobs playable (`src/robots/adapters/native_session_progression.py`).
- NPC dialogue was independently approved offline; the actual safe click reached unknown NPC illustration packet `0x01b3`, so text/menu/private memory and reward acceptance remain open.
- Missing or stale player state stays unknown. Actual free stat/skill points of zero must remain zero. Public advice does not authorize a game action.

## Finite implementation order

1. P0: exactNPCcutinframing -> reviewedstablegate -> actualNPCpages/menu/privateinstructionreceipt
2. P1: receivedcurrentstats/bonuses/freepoints/learnedskills and ownediteminstances/zeny/weight/mutationstate
3. P2: legal item use/equip/stat/skill actions withcorrelatedresult+state change, then earnedXP/loot/progression
4. P3: NPCshop/quest/warp/input transaction support and authoritativeclass refresh beyondNovice
5. P4: useful party/support/contribution/privatechannels/reconnectmemory, humanplaytest andcleanE2E
6. P5: dashboardpopulationreconciliation, specialistclasses/guildWoE andsustainedpopulation/benchmarks

## Domain evidence and gaps

### ro-gameplay-audit-class-specials-rulesets-recovered
18 rows. Evidence: `run/reviews/ro-gameplay-audit-class-specials-rulesets-recovered.json`; report SHA256 `b130cbba4395e82028b02fdcc95acbb2ec41b6e0ba35ae083c5cb7f1ffc84d2d`.

- Actual-job gate supports only source-verified JOB_NOVICE=0; offline tree/template coverage cannot authorize all enabled classes.
- No specialist companion ownership/control state or action contracts; pet/homunculus/mercenary/elemental lifecycle is not generic SELF combat.
- No native accepted learned-skill/stat/equipment action loop; equipment codecs and provisional plans remain non-actuating/offline.
- Ground units, performances/duets and skill-specific menus need persistent state, partner/placement legality and correlated effects absent from generic actions.
- Enabled class/NPC/flag inventory is unknown; MAIN20180704/pre-re must not inherit Renewal or later class/UI availability from cached DBs or public guides.

### ro-gameplay-audit-combat-progression-recovered
18 rows. Evidence: `run/reviews/ro-gameplay-audit-combat-progression-recovered.json`; report SHA256 `c1d5eb1e6bdc06e0751bf9b8849a5422a11d4c77386ebd2f4fc70d0aea97ee24`.

- Receive exact base/bonus stats, learned skills and unspent budgets; preserve actual0 versus unknown.
- Prove received XP/level growth and inventory gain; hits do not close XP/loot acceptance.
- Exercise reviewed native NPC dialogue and receipt-guided Swordman exam; source readiness is not gameplay.
- Provide authoritative post-change class refresh beyond Novice-only baseline; appearance is not actual class.
- Repeat native survival/recovery and add guarded skill actions with timing/resource/status feedback.

### ro-gameplay-audit-economy-inventory-recovered
30 rows. Evidence: `run/reviews/ro-gameplay-audit-economy-inventory-recovered.json`; report SHA256 `300dc1cb3123efb584cad34e2f6c56b23b9d2e07b9d12080deefe7d96da254b6`.

- P0: Current owned item instances and all mutation deltas are not exposed coherently; counts/standalone metadata cannot authorize transactions.
- P0: Received zeny, weight/slots, quotes and reserve accounting are missing from the audited economic decision surface.
- P0: NPC shop buy/sell and use-item actions lack correlated positive ACK + actual stock/zeny/effect acceptance.
- P0: Equip codec approval is representational only; complete legality, framing/intent correlation and actual worn state remain unaccepted.
- P1: Storage/trade/cart/market/crafting lack multi-container or two-party reconciled transaction receipts; concrete service/recipe applicability remains partly unknown.

### ro-gameplay-audit-npc-world-quests-recovered
18 rows. Evidence: `run/reviews/ro-gameplay-audit-npc-world-quests-recovered.json`; report SHA256 `52c3c155143d4eb1f684900b69a91e13f4bef3503d49b7e37d7e868d43cd99ef`.

- Typed numeric/text input and real shop selection/transactions missing.
- No authoritative quest journal/objective/earned-prerequisite state machine.
- No end-to-end safe multi-map travel or accepted portal/Kafra/save/death-return effects.
- No native NPC conversation or correlated server-confirmed reward acceptance.
- No received instance identity/membership/cooldown or dungeon-access lifecycle.

### ro-gameplay-audit-social-guild-woe-recovered
20 rows. Evidence: `run/reviews/ro-gameplay-audit-social-guild-woe-recovered.json`; report SHA256 `9574427fd66df88dfdd31d306f6344a31e5326dc75adb3de776f71b435185da9`.

- Recipient- and epoch-bound private channel/roster receivers, including whisper and party/guild delivery.
- Useful coordinated group behavior: legal support-skill actions, fresh ally telemetry, roles, regroup and effective heal/buff receipts.
- Witness-bound contribution schema and native bridge; recipient identity, damage/heal/buff effect and sequence provenance before scoring.
- Private relationship persistence and gossip learned only by actual recipients, not shared score-store/log shortcuts.
- Native guild lifecycle/permissions/storage/alliance foundation before configured WoE/PvP/BG objectives.

## Limits

- Pre-Renewal active profile and Renewal guide/source applicability are separate; cached class keys, public scripts and source handlers do not prove enablement on the running server.
- Economy guide caches 11–13 differ from their original retrieval digests; they are quarantined and excluded from feature claims. Current-cache hash checks do not restore original retrieval integrity.
- Cached-source integrity was checked separately from semantic evidence. Some original citation ledgers contain copyright/header-only quotes; exact substantive file ranges are required for implementation, not placeholder quote verification.
- The original research batch exited without final reports. These recovered reports compile its cached evidence and keep missing/failed retrievals explicit.
- Full JSON catalogue retains observations, prerequisites, legal actions, required native receipts, negative tests, source references and each report’s caveats. CSV is a compact planning view.

## Artifacts

- `run/reviews/ro-gameplay-coverage-catalogue.json`
- `run/reviews/ro-gameplay-coverage-catalogue.csv`
