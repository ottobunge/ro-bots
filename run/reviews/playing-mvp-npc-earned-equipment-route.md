# Finite NPC → starter equipment handoff

**Outcome:** the observed NPC is **Nelliorde (Bard#brising), not a Novice training guide**. All 11 archived dialogue-string hashes match, in order, `npc/quests/seals/brisingamen_seal.txt:589–610`. Its received menu corresponds to **Who are you? / What's new? / Can you sing?** at612. The fixture sent cancel255; the actual run acquired nothing. There is no starter-gear instruction in the received strings.

## Actual evidence and branch effects

`playing-mvp-live-npc-guidance-cutin.json`, fixture1, epoch1/sequence82: 11 strings, indices1/2/3, three Next requests, cancel255, waiting/blocked thereafter, complete empty inventory and no acquisition/XP gain. Source association comes from exact ordered hashes, **not NPC coordinates or guessed instance IDs**. Local public script matching supports the outer seal-window false/male introduction branch for that interaction; it reveals neither numeric world flags nor private `god_brising`.

- **1 Who are you?** (613–652): biography/illustrations/Next/close2 only.
- **2 What's new?** (653–772): another menu for Prontera/seaside/desert/borderlands. Prontera text663–665 identifies the nearby gate;671 is tavern gossip. No item, warp, quest-flag, stat, skill or XP reward. These continuation strings were **not received**.
- **3 Can you sing?** (773–839): three song choices; each costs500 Zeny if Zeny>499, otherwise refuses. Audio is not a learned Bard skill. No equipment/progression reward.
- **255 cancel:** `select`, not `prompt`; do not count the send, silence or cutin cleanup as acknowledged closure. Recovery belongs to the repairwriter.

## One conditional legal route — ADVISORY ONLY

**Recover dialogue → discover Prontera/Weapon Dealer normally → receive budget and offer → buy one Knife1201 → prove it worn.** A future cognition-selected What's new?/About Prontera! continuation can supply actual gate information, but must not be forced or credited before receipt. This source reconnaissance does not inject shop locations or global NPC knowledge into cognition.

Public recipe: `npc/merchants/shops.txt:255` offers1201 at database price (`-1`); `db/pre-re/item_db_equip.yml:2262–2296` specifies Buy50, Novice allowed, minimum level1, right hand, weight400 internal units. Base10 satisfies that published minimum; empty inventory and zero learned skills/free points do not prevent this item recipe. **Current Zeny and actual price are unknown.** Receive both; purchase exactly one only when affordable and legally admissible. If insufficient/unreceived, end **funding-needed**. Combat loot/selling would be a separately bounded, actually observed funding slice—not an invented reward or assumed available monster.

Do not reroute these base10 fixtures through level1 tutorial promises. The inspected pre-re tutorial explicitly gates an XP lesson on BaseLevel<8 (455–479); no received return path, tutorial flags or gear eligibility exists here.

## Exact implementation seams

1. **Recovery → preparation cognition:** consume the repairwriter's verified closure/abandonment distinction; suppress per-tick recontact. Recontact/choices require fresh received NPC/map/range/life authority, not archived sequence82. No point/gear seeding.
2. **Information → travel:** retain real submenu/text first, then ordinary discovered navigation. Exercise same-client/epoch0091 →007D → new perception/arrival; do not call existing warp handling missing merely because this run never warped.
3. **Shop action/receipt:** retain current Zeny and offered price/discountPrice; guarded shop selection and one-item00C8 purchase; retain fresh00CA result plus actual acquisition/current-index/budget delta. Configured sender/handler excerpts are in JSON. Active shop menu/list headers, layout and inherited stream registration need targeted review; **no shop decoder claim is made**.
4. **Acquisition → gear state:** `native_gameplay.py:312–326` does decode successful0A37 acquisition, but none occurred live. Its inventory list281–294 aggregates `(item,quantity)` and drops current wear metadata. Retain full identified/broken/bind/options/allowed-locations/**WearState** by current index, including acquired gear, or obtain a reviewed fresh snapshot.
5. **Codec → actuator:** existing `native_equipment.py` is explicitly representations only:0998 request8 bytes,0999 ACK11 bytes. Scoped source search found no integration use outside the codec; direct client literals are not a full dependency/parse_stream audit. Add reviewed framing/dispatch/sender and a received-state + NativeMechanics eligibility snapshot. Manifest-matched `pc.cpp:1850–1970,12015–12070` checks class/level/sex, broken/restricted/status, cooldown, slot compatibility and already-worn state. Source Novice compatibility is not live permission.
6. **Delayed ACK:** tie one pending intent to actual client identity, epoch, fresh inventory index/item generation and post-send receive sequence. No wire nonce: stale same-index ACK after reuse or overlapping intent is ambiguous. Fail closed/refresh. Require correlated success **and subsequent current-wear evidence**; allowed slots or sends are not wearing.

## Finite acceptance

Offline TDD must cover real inherited stream framing (incremental/coalesced), metadata preservation, money/weight denial, stale client/epoch/index, unknown/failure/late ACK, cancellation and bounded retries. Existing28 codec tests remain representation proof. Run stable review + unchanged configured gate before a separately authorized native run.

The native slice closes only with ordinary cognition-selected receipts/path, current budget/offer, one legally acquired1201 at its received index, correlated equip success and worn-state evidence. Report purchase, wear and NPC information separately from XP/all-gameplay. Missing budget/offer/eligibility ends as an exact blocker, not PASS. No forced menu stimulus, SQL/private quest reads, model/context fabrication or live actions were performed by this scout.

## Authority

Host-selected **MAIN20180704/pre-re**, source revision `e985006171d2eb320ee512a653f4c83aea3d81b6`; no Renewal substitution. The3216 configured-source authority contains **no NPC files**. NPC/shop/database files are separately local-revision and exact-byte pinned, **not claimed as the active installed NPC closure**. `pc.cpp` and qualified `clif.cpp` hashes match the configured manifest. JSON contains file bytes, SHA256, excerpts/line ranges, exact11/11 hash proof and actual report references. One extractor failed because pc_isequip returns uint8, not int; corrected read-only.

### Audited file fingerprints

| File | Bytes | SHA256 | Authority |
|---|---:|---|---|
| `configured-variant/src/map/pc.cpp` | 498055 | `d12704c1ef7f8321c255175b6f61aa396209b931e2b1687fbbd16963d1def652` | configured manifest match |
| `configured-variant/qualified-clif.cpp` | 776024 | `ace16f15be3b60f730522d620b73a68a9f2cc384016aadce9c985888aea9a1ac` | configured manifest match |
| `rathena/npc/quests/seals/brisingamen_seal.txt` | 144931 | `2244773b857e63eb547bf0ec0a89890fbb487e87c968b3fad09a31989909bafb` | separate exact-byte pin |
| `rathena/npc/merchants/shops.txt` | 25042 | `220c099d0a501c021959a0bda8a8507d1956ef260026d4227773c0010ff79e56` | separate exact-byte pin |
| `rathena/db/pre-re/item_db_equip.yml` | 808389 | `2536c42cc9414f4935e7304f5969228740a5f0308b1acdb2581e5891d25450f7` | separate exact-byte pin |
| `src/robots/adapters/native_gameplay.py` | 14742 | `c7e9f16750bf117ba3a4843264e215d2e653c0376c70acd7ac45e00a6b2100f9` | separate exact-byte pin |
| `src/robots/adapters/native_equipment.py` | 6023 | `b00c9efa6f47258b4889c478c4587fe261c5b3678474e072666e3614b3701eac` | separate exact-byte pin |
| `protocol/main-20180704-pre-re-equipment.json` | 13712 | `c3e34b0a01ed9af39848426f80b035585549aaa3573a3ef9bd76b7d67f0a356a` | separate exact-byte pin |
| `spikes/003-clientless-limbs/client.py` | 46008 | `2f57a0adc0b43a20235835290499ca0043966c5def208642598afb0dc49807fd` | separate exact-byte pin |
