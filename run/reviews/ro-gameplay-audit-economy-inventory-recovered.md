# Recovered inventory/economy gameplay audit

**Finite partial matrix: 30 feature rows, groups 12–20.** Active profile `MAIN20180704/pre-renewal, obfuscation absent`; public source pin `e985006171d2eb320ee512a653f4c83aea3d81b6`. Research only; no implementation, tests, native login, SQL, service/model action or new network collection.

The interrupted original batch remains incomplete; these are new recovery artifacts. All ten pinned cached server/doc files match the current local public files byte-for-byte. Generic wiki sources remain advice, not active-server configuration. Existing copyright/title ledger quotes are not mechanical proof: use exact row line ranges below.

**Evidence issue:** Guide caches 11–13 differ from their original retrieval SHA-256 values; cause unknown. They are quarantined, retained in the source manifest, and excluded from all load-bearing row citations. The ten pinned server/doc sources match both the original digests and current local files. No new fetch was attempted.
Provided root readiness context `4177 tests +65 subtests,95.37%,check/audit0` was not rerun. Archived codec review approves 20+8 offline checks only (`run/reviews/playing-mvp-native-equipment-codec-approved.json:1–14`); ownership/legality/native equipping remain unaccepted. Both archived fixtures received complete empty inventory and zero equipment rows (`run/reviews/playing-mvp-passive-equipment-inventory.json:134–144,275–285`). Empty receipts prove neither positive item metadata nor transaction success.

## Top five gaps

- P0: Current owned item instances and all mutation deltas are not exposed coherently; counts/standalone metadata cannot authorize transactions.
- P0: Received zeny, weight/slots, quotes and reserve accounting are missing from the audited economic decision surface.
- P0: NPC shop buy/sell and use-item actions lack correlated positive ACK + actual stock/zeny/effect acceptance.
- P0: Equip codec approval is representational only; complete legality, framing/intent correlation and actual worn state remain unaccepted.
- P1: Storage/trade/cart/market/crafting lack multi-container or two-party reconciled transaction receipts; concrete service/recipe applicability remains partly unknown.

## Support frontier

`native_primitive_verified`: 1; `offline_pipeline`: 2; `missing`: 16; `codec_only`: 7; `offline_model`: 1; `unknown`: 3.

Only the current-epoch completeness row is `native_primitive_verified`, narrowly for archived empty receipt observations. `codec_only` means fields/requests can be represented, not applied. `missing` is absence at the audited native playing action surface; `unknown` preserves unexamined service/recipe applicability. All transaction receipts and negative tests below are required designs, not executed acceptance.

### Shared transaction contract

Bind every pending economic operation to the actual client, epoch, request/intent, actor, exact instance/index and quoted session. Retain before/after stock, currency, wear and all affected containers. Require positive protocol result where emitted **and** actual effects; storage relies on corresponding add/remove receipts rather than a fabricated universal ACK. An offer ACK, send count, dialogue close, floor disappearance or generic decoded equip success never proves the operation.

Every row additionally requires stale epoch/index, replay/deduplication, racing mutation, unhealthy transport/frame-gap, retained event/byte/slot budget and economic budget negatives. These are specified, not run.

## Feature matrix

### inventory.current_epoch — Complete current-epoch inventory, including empty inventory

Group 12 · `native_primitive_verified` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Client identity, epoch, contiguous sequence, auth/load barrier and WEIGHT completion, not absence of item packets.
- **Legal action:** Observe only; refuse economic actions until complete healthy current inventory.
- **Prerequisites:** Identity-matched client and no retained-frame gap.
- **Required positive receipt:** Fresh same-client/epoch completion barrier and exact stock snapshot. Status: Archived passive native receipts read, not rerun; no carried/equipped rows..
- **Negative/race/replay/budget tests:** Missing barrier; deletion between list and WEIGHT; reconnect equal sequence; nonempty historical rows after invalidation. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_gameplay.py:208–232` (implementation); `src/robots/adapters/native_gameplay.py:343–418` (implementation); `run/reviews/playing-mvp-passive-equipment-inventory.json:134–144` (archived fixture 0 empty receipt); `run/reviews/playing-mvp-passive-equipment-inventory.json:275–285` (archived fixture 1 empty receipt)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:10782–10794` — server load inventory/status ordering[1]
- **Unknown/frontier:** Archived receipts prove two complete empty inventories only; not nonempty instance ownership or any economic action.

### inventory.instance_index — Instance identity, stack counts and index namespaces

Group 12 · `offline_pipeline` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Per-instance index, item ID, count, identified/damaged/cards/refine/options/expiry/binding; distinguish item ID from instance and inventory/cart/storage index.
- **Legal action:** Select a current owned instance, not an aggregate item-ID count.
- **Prerequisites:** Complete inventory plus coherent mutation updates and current instance identity.
- **Required positive receipt:** Before/after exact instance rows with counts; preserve distinct same-ID equipment and incompatible stacks. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Index replacement; duplicate row; split/merge stack; same ID different cards/options/binding; amount zero/negative. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_gameplay.py:281–299` (implementation); `src/robots/adapters/native_gameplay.py:312–326` (implementation); `src/robots/app/playing_runtime.py:243–258` (implementation); `src/robots/adapters/native_equipment.py:99–172` (implementation)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:6586–6657` — stack identity and bound/unique/card matching[2]; `rathena/src/map/clif.cpp:13621–13668` — inventory index minus 2 versus storage minus 1[1]
- **Unknown/frontier:** Gameplay tracker stores index -> item/count and projects aggregates; standalone equipment metadata decoder is not a session-owned instance tracker.

### inventory.pickup — Acquire ordinary observed ground loot

Group 12 · `offline_pipeline` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Received floor-item ID/location/quantity, own position/life and successful add-item receipt.
- **Legal action:** Pickup visible reachable permitted loot; approach only observed target.
- **Prerequisites:** Loot priority/range, remaining capacity, healthy epoch.
- **Required positive receipt:** Fresh success add-item receipt with positive amount and coherent stock increase; floor disappearance alone is insufficient. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Other player takes loot; priority timer; out of range; full/overweight; index reused; ACK replay. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_gameplay.py:40–41` (implementation); `src/robots/adapters/native_gameplay.py:302–326` (implementation); `src/robots/app/playing_runtime.py:378–391` (implementation)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:6189–6268` — loot distance, priority and inventory insertion[2]
- **Unknown/frontier:** Pickup path exists, but this recovery did not examine a successful native acquisition report; do not upgrade from send intent.

### inventory.drop — Drop/dispose only authorized expendable items

Group 12 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Current instance/count, binding, map restriction, worn/switch state.
- **Legal action:** Drop positive owned quantity only under explicit discard policy.
- **Prerequisites:** Non-trading/non-vending; legal map/item; quantity budget.
- **Required positive receipt:** Drop result and exact inventory decrement; floor object receipt when relevant. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No-drop map; bound/non-droppable; trade/vending; excess quantity; equipped-switch item. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:6137–6181` — drop legality and deletion[2]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### inventory.identify — Identify an owned unidentified item

Group 13 · `codec_only` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Identify flag and current menu/skill session; identify resource if required by selected route.
- **Legal action:** Select owned unidentified target in legitimate identify context.
- **Prerequisites:** Valid identify route/menu and current index.
- **Required positive receipt:** Successful identification response and same-instance identified flag change; resource delta for selected route. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Already identified; absent index; wrong menu; target transferred before selection. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:99–121` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:13429–13450` — requires identify menu and unidentified target[1]; `rathena/src/map/skill.cpp:10568–10588` — identify mutation and result[9]
- **Unknown/frontier:** Metadata flag decode only; no identify action/receipt pipeline found in audited playing surface.

### inventory.consume — Consume healing/usable items with real effect

Group 13 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Owned positive stack, life/status, use restrictions, cooldown, HP/SP and target/delayed-use mode.
- **Legal action:** Use only allowed consumable in current context; resolve targeted/delayed use explicitly.
- **Prerequisites:** Pinned usable item script; no forbidden trading/storage/NPC/map/status state.
- **Required positive receipt:** Fresh successful use response plus stock decrement when consumed and actual HP/SP/status/skill/warp effect; delayed consumption needs final target resolution. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Dead/busy; storage open; use cooldown; no-consumption map; wrong type; target cancellation; same stack race. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:12080–12107` — request legality and negative response[1]
- **Additional pinned/source evidence:** `rathena/src/map/pc.cpp:6276–6442` — consumable/map/status/cooldown restrictions[2]
- **Additional pinned/source evidence:** `rathena/src/map/pc.cpp:6450–6576` — consumption and script execution[2]
- **Additional pinned/source evidence:** `rathena/src/map/clif.cpp:4468–4497` — ACK includes index, actor, amount and result[1]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### inventory.ammunition — Ammunition compatibility, wear and depletion

Group 13 · `codec_only` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Ammo subtype/count, equipped weapon, skill consumption requirements and current ammo wear.
- **Legal action:** Equip compatible ammo and reserve enough for bounded combat/skill use.
- **Prerequisites:** Weapon/ammo rules and configuration; current owned ammo.
- **Required positive receipt:** Correlated equip success with ammo worn mask, then actual consumption deltas for supported attacks/skills. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong weapon; empty ammo; stale stack; switch attempt with ammo; insufficient per-skill quantity. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:49–77` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:1850–1969` — ammo/weapon compatibility[2]; `rathena/src/map/pc.cpp:12015–12287` — ammo and requested-position constraints[2]
- **Unknown/frontier:** Only generic equip bytes exist; skill-specific ammunition recipes/consumption cross-reference combat/class report.

### economy.weight_capacity — Weight, slots and safe capacity budget

Group 13 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Received WEIGHT/MAXWEIGHT, actual slots/stack room and per-item weights.
- **Legal action:** Plan pickup/buy/withdraw/receive below applicable limits.
- **Prerequisites:** Coherent inventory and current received weight, not static guide capacity.
- **Required positive receipt:** Actual capacity/status receipts reconcile accepted additions; rejected addition leaves stock unchanged. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Boundary weight; slot full despite low weight; oversized quantity; overflow; stale weight. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_gameplay.py:405–418` (WEIGHT is completeness barrier, not stored capacity ledger); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/npc.cpp:2796–2948` — weight, slot and purchase checks[7]; `rathena/src/map/pc.cpp:6586–6657` — cart weight/stack limits[2]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### economy.zeny_budget — Zeny, reserves and receipt-based accounting

Group 13 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Current received zeny, quoted unit prices, fees, pending spend and minimum reserve.
- **Legal action:** Authorize spend only against observed balance and explicit budget; distinguish NPC quote from player-market price.
- **Prerequisites:** Same-epoch currency observer and reconciliation.
- **Required positive receipt:** Fresh zeny before/after matches actual transaction cost/proceeds including cap/fees; ACK without balance is insufficient. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Insufficient funds; concurrent spend; negative/overflow quantity*price; zeny cap; replay; reserve violated. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_gameplay.py:405–418` (only XP/completeness handling here); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:5795–5820` — payment bounds and status update[2]; `rathena/src/map/pc.cpp:5829–5856` — credit capped at MAX_ZENY[2]
- **Unknown/frontier:** Current balance, fees and any market prices are unknown; no guessed profitability.

### inventory.equipment_metadata — Equipment wire metadata is not wear/eligibility

Group 14 · `codec_only` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Allowed locations and wear state separately; identify/damage, refine, four cards and five option slots including option_count=0.
- **Legal action:** Decode complete pinned frames only; do not infer ownership, effects or equip eligibility.
- **Prerequisites:** MAIN20180704 codec framing and current-state integration for future use.
- **Required positive receipt:** Nonempty native equipment row tied to current inventory and epoch; passive empty inventory does not exercise item metadata. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Malformed lengths; signed index; duplicate index; unknown spare flags; all five options when count is zero. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:1–13` (implementation); `src/robots/adapters/native_equipment.py:99–172` (implementation); `run/reviews/playing-mvp-native-equipment-codec-approved.json:1–14` (approved bounded offline review only)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:12015–12287` — server checks still needed[2]
- **Unknown/frontier:** 20+8 archived codec checks are approved; no native wear/autoequip acceptance.

### inventory.equip_legality — Class/level/sex/map/slot and both-hand equip legality

Group 14 · `offline_model` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Owned identified intact instance, item permission catalog, current class/level/sex/status, competing worn slots.
- **Legal action:** Request only permitted position; resolve two-hand/dual-wield/slot conflicts; never equip from item ID or allowedLocation alone.
- **Prerequisites:** Complete owned instances and server-equivalent legality, restrictions, current wear plus fresh intent.
- **Required positive receipt:** Fresh positive equip ACK bound to own index/epoch/intent, then actual same-instance worn state and relevant status/look change. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong job/class/sex/level; broken/unidentified item; restricted map; two-hand conflict; already worn; stale index; spoofed ACK. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/mechanics_yaml.py:1–5` (implementation); `src/robots/adapters/mechanics_yaml.py:284–352` (implementation); `src/robots/adapters/native_equipment.py:49–77` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:1850–1969` — server permissions and class/level/sex/condition checks[2]; `rathena/src/map/pc.cpp:12015–12287` — actual equip state transition[2]
- **Unknown/frontier:** Static catalog intentionally omits custom imports, scripts/combos; not a complete legality validator. Wear/autoequip not accepted.

### inventory.unequip — Unequip and reconcile displaced equipment

Group 14 · `codec_only` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Actual current worn masks, locked status and pending equip/unequip intents.
- **Legal action:** Unequip current owned worn instance only; track automatically displaced slots separately.
- **Prerequisites:** Same-session wear observer and no forbid-unequip status.
- **Required positive receipt:** Own-index fresh success unequip ACK plus wear mask cleared and related status; no effects inferred from ACK alone. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Not worn; forbidden status; unknown result; ACK for another index; delayed old equip ACK. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:32–77` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:12398–16169` — unequip state checks and mutations[2]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### inventory.cards — Card compounding transaction

Group 15 · `codec_only` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Owned card and unequipped identified target, matching card location, free real slot, reserved special card data.
- **Legal action:** Insert one compatible card in explicit chosen target with irreversible-change consent.
- **Prerequisites:** Current instance metadata, target slots and no special reserved card layout.
- **Required positive receipt:** Successful insertion result, card consumed and exact target card array updated; preserve target identity. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Equipped target; full slots; wrong type/location; unidentified; reserved card data; missing card. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:99–172` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:5596–5657` — card legality, consumption and target update[2]
- **Unknown/frontier:** Card array observable offline; no card insertion actuator or native mutation proof.

### inventory.refine — Refinement costs, success and destructive failure

Group 15 · `codec_only` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Current refine level/refineable state, selected service, materials, zeny and success/failure rules.
- **Legal action:** At most authorized attempts on explicitly owned target; distinguish skill refine from NPC refinement.
- **Prerequisites:** Specific pinned service/recipe and cost/chance policy; irreversible-risk consent.
- **Required positive receipt:** Resolved refine success/failure plus material/zeny deltas and increased refine or actual loss/downgrade; failed rolls are not retries. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Unrefineable/max refine; missing material; budget exhausted; target replacement; fail roll; double response. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:99–172` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/skill.cpp:10593–10701` — skill weapon-refine route, not universal NPC rules[9]; `rathena/doc/script_commands.txt:2954–3010` — script refinement rate/cost interfaces[10]
- **Unknown/frontier:** Native NPC refinement script, active refine DB/config and chance/cost not verified; no universal safe-level or fee asserted.

### inventory.repair — Repair a broken owned/authorized target

Group 15 · `codec_only` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Repair2 requires MAIN >=20200916 or RE >=20200724; active MAIN20180704 takes Repair1. Renewal material arrays differ.
- **Observe:** Broken flag, repair menu, target player/index, range, item weapon/armor level and repair material.
- **Legal action:** Repair only valid target through legitimate skill/service.
- **Prerequisites:** Repair skill/menu, correct material, current target and range.
- **Required positive receipt:** Successful repair result, broken flag cleared on target and exact material consumed on repairer. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong menu; trading; intact item; missing material; out of range; other-player target disconnected. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:115–121` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:13267–13289` — version branch and trading guard[1]; `rathena/src/map/skill.cpp:10500–10563` — target/material/range checks and repair[9]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### inventory.enchant_options — Enchant/random-option transformations

Group 15 · `unknown` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Modern enchant/grade interfaces have separate client/version gates; do not apply modern UI to MAIN20180704.
- **Observe:** All five raw option records even beyond declared option_count; target/service/material/fee and selected transformation.
- **Legal action:** Only an actually loaded legal NPC service for this ruleset; do not infer service availability from encoded fields.
- **Prerequisites:** Pinned service script/DB and destructive-change policy.
- **Required positive receipt:** Service-resolved outcome with target option/card data and material/zeny/target-loss deltas reconciled. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Unsupported client UI; reset/reroll failure; zero count with nonzero spare option records; stale target; missing fee. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/native_equipment.py:151–172` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/doc/script_commands.txt:11285–11320` — script random-option access, not player action availability[10]; `rathena/doc/script_commands.txt:8669–8695` — version-specific enchant UI documentation[10]
- **Unknown/frontier:** No active pre-re enchant service established; option representation does not prove NPC availability or bonuses.

### economy.npc_shop_quote — Open shop and observe legal price/list context

Group 16 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Observed NPC/map/distance, shop mode, current list/item quote and stock where supplied.
- **Legal action:** Choose buy/sell only within valid NPC-shop context.
- **Prerequisites:** NPC observation/dialogue + shop codec/framing and fresh session context.
- **Required positive receipt:** Fresh shop list for matching NPC and mode; opening dialogue alone is not purchase success. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong NPC; too far; trade busy; stale list/mode; NPC despawn; closed shop. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:316–351` (dialogue exists but buy/sell selection not exposed); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:12260–12271` — buy/sell selector[1]; `rathena/src/map/npc.cpp:2796–2948` — nearby shop and listed item checks[7]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.; Guide caches 11-13 fail original retrieval digest checks; excluded from load-bearing citations. Use matching pinned server source only.

### economy.npc_buy — Purchase NPC stock without imaginary profit

Group 16 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Fresh offered item/price/stock, quantity, balance/reserve and weight/slots.
- **Legal action:** Buy bounded positive quantity actually offered by matching shop.
- **Prerequisites:** Quote/session, funds and capacity; active discount semantics only when known.
- **Required positive receipt:** Positive purchase result AND actual inventory additions AND zeny debit; finite-stock shop receipt where observable. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No funds; overweight/full slots; unlisted item; expired shop context; competing finite stock; replay. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:12299–12326` — purchase result and shop context cleared[1]; `rathena/src/map/npc.cpp:2796–2948` — checks, payment and stock insertion[7]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### economy.npc_sell — Sell selected expendable stock to NPC

Group 16 · `missing` · P0

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Exact owned sale instances/quantities, restrictions, observed sell quote, protected gear/materials.
- **Legal action:** Sell only explicit expendable positive quantities; reserve needed equipment, ammo and recipe inputs.
- **Prerequisites:** Valid sell-mode shop and current inventory; actual server price/modifier.
- **Required positive receipt:** Positive sell result plus exact inventory decrement and actual zeny credit; caps/custom-script behavior reconciled. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Bound/restricted/rental item; wrong index/quantity; selling protected item; inventory changed; zeny cap; replay. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:12347–12361` — sale response and context cleared[1]; `rathena/src/map/npc.cpp:3031–3138` — restrictions, custom shops, removal and payment[7]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### economy.merchant_modifiers — Discount/Overcharge only with learned applicable skills

Group 16 · `unknown` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Renewal Merchant guide is separate advice; no modern job-change/free-skill acquisition assumed here.
- **Observe:** Observed skill levels, actual NPC quotes and transaction balance deltas.
- **Legal action:** Use modified NPC quote, never estimate player vending prices from skills or item_db Buy.
- **Prerequisites:** Relevant learned merchant skill and selected NPC semantics.
- **Required positive receipt:** Quoted/actual spend or proceeds reconcile on a real merchant transaction. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong class; unlearned skill; custom absolute-price shop; assume NPC modifier on player shop. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/adapters/mechanics_yaml.py:1–5` (implementation); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/npc.cpp:2796–2948` — shop discount branch[7]; `rathena/src/map/npc.cpp:3031–3138` — modified sell value[7]
- **Unknown/frontier:** Cross-reference class-specials-rulesets report for learning/prerequisites; actual fixture merchant eligibility not established.; Guide caches 11-13 fail original retrieval digest checks; excluded from load-bearing citations. Use matching pinned server source only.

### inventory.storage_open — Open/close storage in valid namespace

Group 17 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** NPC storage access state, capacity/list, personal/guild/premium namespace and charge if any.
- **Legal action:** Open only authorized available storage; close session before incompatible actions.
- **Prerequisites:** Actual loaded access NPC/script, authorization and any observed fee.
- **Required positive receipt:** Fresh storage list/capacity tied to session; close response; fees reconciled if charged. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Unauthenticated storage; wrong namespace; no access; missing fee; disconnect while open. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/clif.cpp:13621–13668` — storage_flag namespaces and differing indices[1]; `rathena/src/map/storage.cpp:189–206` — put permission[3]; `rathena/src/map/storage.cpp:215–231` — get permission[3]
- **Unknown/frontier:** Active access script/fee and personal capacity are unknown; guild authorization belongs in social/guild report.

### inventory.storage_deposit — Deposit preserves instance/count across both containers

Group 17 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Current inventory and storage snapshots, permissions, count, stack room, bound/trade flags.
- **Legal action:** Deposit legal owned positive quantity to currently open correct storage.
- **Prerequisites:** Current source index and storage list; no trading or equip-switch conflict.
- **Required positive receipt:** Storage addition + inventory removal with same instance metadata/quantity; completion must reconcile both sides, not zero-amount failure packets. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No put access; storage full; forbidden bound item; excess quantity; zero-amount removal; stale namespace. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/storage.cpp:189–206` — index/count/permission checks[3]; `rathena/src/map/storage.cpp:241–296` — stack room and binding/store restrictions[3]; `rathena/src/map/storage.cpp:334–358` — remove inventory only after storage addition[3]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### inventory.storage_withdraw — Withdraw only received storage stock

Group 17 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Storage index namespace, current row/count, get access, inventory weight/slots.
- **Legal action:** Withdraw allowed positive stock into inventory.
- **Prerequisites:** Open correct storage and current capacity budget.
- **Required positive receipt:** Successful inventory addition + exact storage decrement preserving metadata; failure zero-amount messages do not count. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No get access; empty/excess source; overweight/full inventory; old storage index after reorder. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/storage.cpp:215–231` — get permission and count checks[3]; `rathena/src/map/storage.cpp:367–384` — delete storage only on inventory add success[3]
- **Unknown/frontier:** No native positive/negative transaction proof recovered; server existence is not client support.

### economy.player_trade — Two-party offer, lock, commit, cancel with atomic receipts

Group 18 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Actual partner identity/range, both item/zeny offers, lock states, capacity and item restrictions.
- **Legal action:** Offer owned permitted quantities; inspect final offer; both lock and commit; cancel on mismatch.
- **Prerequisites:** Explicit partner authorization and current offers/inventories; two healthy sessions for acceptance.
- **Required positive receipt:** Fresh committed trade result on both sides AND exact inventory/zeny deltas conserving exchanged assets; offer ACK/OK lock is not completion. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Partner disappears/declines; one side never locks; offer changes; full receiver; insufficient stock/zeny; duplicate commit. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/trade.cpp:586–686` — both-lock validation, anti-exploit checks and exchange[4]
- **Unknown/frontier:** No accepted native two-party transaction or trade receipt observer found in audited action surface.

### inventory.cart — Cart transfers and independent capacity/indices

Group 18 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Current cart state/rows/weight/max/slots and source-container instance/count.
- **Legal action:** Move legal quantities inventory<->cart; only with legitimately acquired cart and allowed map/state.
- **Prerequisites:** Cart skill/status and current two-container snapshots.
- **Required positive receipt:** Actual cart addition/removal and matching inventory inverse delta; weight and metadata reconcile. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No cart; overweight/full cart; map forbids cart; bound restriction; vending active; source changed. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/pc.cpp:6586–6657` — cart stack identity, restriction and weight checks[2]; `rathena/src/map/clif.cpp:13673–13716` — cart/storage transfers require cart and non-vending state[1]
- **Unknown/frontier:** Class-specials report owns Pushcart acquisition; no guide-derived hard capacity substituted for active receipts.

### economy.vending_buy — Buy from a current player vending shop

Group 19 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Observed seller/shop UID, offered cart index/price/stock, distance, own funds/capacity.
- **Legal action:** Buy bounded listed quantities from current shop; do not infer fair market price.
- **Prerequisites:** Same-shop identity and quote, spend cap and usable capacity.
- **Required positive receipt:** Purchase result plus buyer stock/zeny and seller cart/zeny/stock changes; partial or capped results reconciled. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Shop UID changed; seller gone; stock sold out race; duplicate list entry; out of range; funds/capacity failure. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/vending.cpp:123–286` — shop identity, stock and duplicate-purchase protections[5]
- **Unknown/frontier:** Market price discovery and profitability unknown; no third-party bot adoption.

### economy.vending_sell — Open bounded vending shop and observe sales

Group 19 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Learned Vending, active cart, eligible cart stock, prices chosen by explicit policy, shop identity and sale receipts.
- **Legal action:** Open/close own authorized shop; list only eligible stock at explicitly approved prices.
- **Prerequisites:** Merchant skill/cart and legal map; no incompatible trading state.
- **Required positive receipt:** Positive open result followed by real buyer sale with cart depletion and zeny proceeds; opening/send counters are not sales. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** No skill/cart; dead/trading; illegal count/item; duplicate stock; price overflow; close/reopen UID race. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/vending.cpp:298–418` — skill/cart and offered-list constraints[5]; `rathena/src/map/vending.cpp:123–286` — actual purchase mutation[5]
- **Unknown/frontier:** Class learning is cross-referenced; no live merchant sales acceptance or market price policy established.

### economy.buying_store — Buying-store creation and seller transaction

Group 19 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Renewal Merchant skill/academy guidance is not proof of pre-re acquisition; source supports feature gate, not active server enablement.
- **Observe:** Feature availability, learned/unlocked opening route, requested eligible item list, store UID, reserve, live zeny limit and capacity.
- **Legal action:** Open only enabled legal purchase store; sell only currently owned matching eligible items to current store.
- **Prerequisites:** Version/config support, skill/access, budget and exact matching store.
- **Required positive receipt:** Create success with budget/list, then real seller trade with both inventory/zeny deltas and reduced request quantity/limit. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Feature disabled; no slots; stale buyer ID; depleted zeny; duplicate entries; restricted item; no-buying-store map/cell. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/buyingstore.cpp:116–255` — feature/access/zeny/map gates[6]; `rathena/src/map/buyingstore.cpp:325–506` — current shop identity and live budget checks[6]
- **Unknown/frontier:** Active feature configuration and acquisition route unknown.

### economy.craft_skill — Recipe-based forging/mixing with consumed-failure accounting

Group 20 · `missing` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Actually legal recipe/menu, required skill/tools/material quantities, current inputs, output metadata and success/failure result.
- **Legal action:** One authorized bounded craft attempt or explicitly bounded quantity; consume-failure ends attempt.
- **Prerequisites:** Pinned active recipe DB and applicable class/skill route; budget and capacity.
- **Required positive receipt:** Resolved craft outcome plus every material decrement and actual output count/identity if successful; failure may consume resources and must not invent output. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Unknown recipe; wrong class/skill; absent tools/materials; changed input; output capacity; RNG fail; duplicate result. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/src/map/skill.cpp:12844–13515` — recipe selection, resources and probabilistic production[9]
- **Unknown/frontier:** Actual active recipe files/formula and class-specific legal route not recovered. Cross-reference class-specials-rulesets report; do not copy all class mechanics.

### economy.craft_npc — NPC material exchange/crafting service

Group 20 · `unknown` · P1

- **Ruleset:** Applicable subject to pinned item/map/class/session restrictions; actual loaded public configuration not established by this audit. Renewal: Separate ruleset; do not transfer item, price, formula, capacity or packet assumptions from Renewal guides.
- **Observe:** Observed NPC instructions/choices, exact requirements, output, fee and target restrictions.
- **Legal action:** Follow finite legitimate dialogue only for an actually verified service; refuse unseen recipe assumptions.
- **Prerequisites:** Specific loaded public NPC script plus material/zeny observer and dialogue session.
- **Required positive receipt:** Terminal service response AND input/zeny loss AND actual output/target-state change; dialogue closure alone insufficient. Status: required acceptance design, not an executed transaction.
- **Negative/race/replay/budget tests:** Wrong choice; insufficient inputs/fee; timeout after payment; repeated selection; unavailable NPC; wrong recipe variant. Shared tests above also apply; not run.
- **Current implementation/evidence:** `src/robots/app/playing_runtime.py:316–358` (generic dialogue only); `src/robots/app/playing_runtime.py:296–376` (audited native action dispatch: economic action not exposed)
- **Pinned/source evidence:** `rathena/doc/script_commands.txt:4990–5050` — script item creation documentation, not loaded player service[10]
- **Unknown/frontier:** Specific loaded NPC craft script absent from cached evidence; generic getitem commands do not establish a playable service.

## Finite ordinary-player economic loop

**Proposed acceptance scenario, not implementation or a completed native run.** One cycle, 180-second wall-clock cap, at most five pickups, one sale, one buy, one use, one equip, one deposit, one withdrawal, one trade commit per party and one craft attempt. These are proposed audit limits, not server constants. Economic mutation timeout resends: zero.

Require observed initial zeny Z0, explicit operator spend cap B, retained reserve R, quotes, fees and received capacity. Commit only while pending+new spend <= B and actual balance-new cost >= R; all variables unknown until observed. No numeric market prices or expected profit invented.

1. **Observe healthy current-epoch complete inventory, life/position, zeny and weight/capacity; obtain explicit spend/reserve/discard policy.** Exact received initial ledger or STOP_BLOCKED; the archived fixtures start empty, not stocked. (`inventory.current_epoch`, `inventory.instance_index`, `economy.zeny_budget`, `economy.weight_capacity`)

2. **Earn at most five actual accessible loot pickups via legal combat/navigation covered by combat-progression report, or use already owned expendable stock; never grant stock.** Actual current stock acquired; no loot before deadline => STOP_NO_STOCK, not success. (`inventory.pickup`)

3. **Visit observed valid ordinary NPC shop; sell one approved expendable batch, preserving gear/ammo/material reserve.** Sale result, stock loss and zeny credit reconcile; unknown quote/action support => STOP_BLOCKED. (`economy.npc_shop_quote`, `economy.npc_sell`)

4. **Buy one offered usable healing item within actual funds, reserve and capacity; use once only when legitimate effect needed.** Purchase ACK+actual debit/addition, then use ACK+consumption/effect; no injured/eligible state => record conditional use not exercised. (`economy.npc_buy`, `inventory.consume`)

5. **If legally owned suitable equipment exists, request at most one equip after full class/sex/level/map/slot validation. Do not buy hypothetical equipment or autoequip from allowedLocation.** Fresh own-epoch/index equip ACK AND worn-state receipt; absent equipment/legality observer => NOT_EXERCISED or STOP_BLOCKED. (`inventory.equip_legality`, `inventory.equipment_metadata`)

6. **If an actual authorized storage service is available, deposit then withdraw one expendable legal item, each once.** Both-container inverse deltas and fees reconcile; unavailable service => NOT_EXERCISED. (`inventory.storage_open`, `inventory.storage_deposit`, `inventory.storage_withdraw`)

7. **Optional authorized ordinary partner trade: inspect final offer, both lock, commit once each; no partner => skip without waiting indefinitely.** Both completion results and actual conserved inventory/zeny changes; unconfirmed commit => STOP_UNCERTAIN. (`economy.player_trade`)

8. **Optional one actually legal recipe/service attempt only if existing class/skill and observed materials permit it; otherwise skip.** Craft result plus materials/currency/output deltas; consumed failure is recorded failure, never fictional production or retry. (`economy.craft_skill`, `economy.craft_npc`)

9. **Close sessions; observe final same-epoch exact stock/wear/zeny/capacity and reconcile each completed receipt. End, do not start another cycle.** COMPLETE_CORE only for received sale+purchase and required usage effects; optional storage/trade/equip/craft get independent exercised/pass/fail/not_exercised verdicts. (`inventory.current_epoch`, `economy.zeny_budget`)

**Stop conditions:** Deadline/action limit reached.; Missing/current-state gap or stale epoch/index.; Reserve/weight/slots/quantity limit violated.; Negative ACK or changed quote: record failure and terminate that action.; Unknown outcome after request: stop uncertain, resnapshot with explicit authorization, never resend economic mutation blindly.

**Cross-report dependencies:** combat-progression: lawful earning/navigation and ammo-use details; npc-world-quests: actual service discovery and dialogue; class-specials-rulesets: recipe/class skill acquisition and exceptions; social-guild-woe: partner authorization and guild-storage access

**Applicability frontier:** No executed loop, profitability, sustained population, merchant shop activity, class completion or native equipment acceptance.

## Sources

[1] src/map/clif.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/clif.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-1.txt`; SHA-256 `0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5`.

[2] src/map/pc.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pc.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-2.txt`; SHA-256 `d12704c1ef7f8321c255175b6f61aa396209b931e2b1687fbbd16963d1def652`.

[3] src/map/storage.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/storage.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-3.txt`; SHA-256 `b66a2a85f062966b1cc9aab2a54401f45c0c53b11a712ffe88e6caa1fb4605f8`.

[4] src/map/trade.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/trade.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-4.txt`; SHA-256 `a989bf38399d7b14bb0c822e6825385e00ec812d2c438695b1387c12f976f30e`.

[5] src/map/vending.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/vending.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-5.txt`; SHA-256 `605f67a293ee137ff97bbaf04a168c0287a9c615fb20644433e644921d180193`.

[6] src/map/buyingstore.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/buyingstore.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-6.txt`; SHA-256 `0daa9c410b03fc3561fbc1570b103deb83cabc9d9cfbf49db0eb132c622c1913`.

[7] src/map/npc.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/npc.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-7.txt`; SHA-256 `90d582661668e5cb8567de5a7b92d067e5d0db479963b00bab340af9fe477534`.

[9] src/map/skill.cpp — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/skill.cpp
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-9.txt`; SHA-256 `aad3c2f3968e0ddf38b89aff953d77a4cae66a0aa54b539a47723dd5f25b6c04`.

[10] doc/script_commands.txt — https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/doc/script_commands.txt
Cached evidence: `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/economy-inventory/source-10.txt`; SHA-256 `7d8d446f93e5575041319560cfea0a88ec523334a97156cf72138cf4126b266e`.

