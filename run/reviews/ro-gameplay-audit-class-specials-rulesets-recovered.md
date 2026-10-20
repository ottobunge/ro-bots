# Recovered class-specials / ruleset-applicability audit

Public pin: `e985006171d2eb320ee512a653f4c83aea3d81b6`. Active scope: **MAIN20180704 / pre-renewal**.

**Recovery complete for these new artifacts only. The old batch is still interrupted; original completion, ownership and cleanup are not established.**

## Finding

Generic agents cannot yet play every enabled class. The selected native progression adapter explicitly supports only JOB_NOVICE=0; the action union lacks skills, stat/equipment spending and specialist actions. Catalogs and provisional build templates are offline. The reviewed NPC pipeline is source-ready, not accepted live; equipment codecs do not confer actuation authority. [Implementation: `src/robots/adapters/native_progression.py:87-103`, `src/robots/domain/actions.py:1-94`, `src/robots/domain/build_templates.py:1-36`, `src/robots/adapters/native_equipment.py:1-71`, `wiki/guides/goals-ledger.md:50-63`.]

## Evidence boundary

18 grouped rows; 12 class-family groups. The cached trees contain 77 pre-re and 175 Renewal keys, **not playable/enabled class totals**. Mounted aliases, high/baby stages and experimental keys are retained rather than promoted. Runtime enablement flags and script imports are unknown. Scope establishes the active profile; this recovery did not probe the server.

44 retrieval-manifest entries: 41 successful cached files, all SHA256-checked; 3 failed fetches. The ledger has 43 sources because two job_stats snapshots were added outside the manifest. No new web collection. Guides are advice only; pinned public source and received state are mechanics authorities. Ledger header/copyright quotes alone do not prove gameplay mechanics.

Support tiers: missing=16, offline_model=1, offline_pipeline=1. A missing specialist can depend on offline catalogs or NPC substrate without becoming supported.

## Top five gaps

1. Actual-job gate supports only source-verified JOB_NOVICE=0; offline tree/template coverage cannot authorize all enabled classes.
2. No specialist companion ownership/control state or action contracts; pet/homunculus/mercenary/elemental lifecycle is not generic SELF combat.
3. No native accepted learned-skill/stat/equipment action loop; equipment codecs and provisional plans remain non-actuating/offline.
4. Ground units, performances/duets and skill-specific menus need persistent state, partner/placement legality and correlated effects absent from generic actions.
5. Enabled class/NPC/flag inventory is unknown; MAIN20180704/pre-re must not inherit Renewal or later class/UI availability from cached DBs or public guides.

## Class-family applicability (grouped, not per-skill exhaustive)

| Family | Cached pre-re keys | Renewal-only keys / frontier | Applicable special rows |
|---|---|---|---|
| Novice and Supernovice | Novice, Supernovice, Novice_High, Baby, Super_Baby | Hyper_Novice, Super_Baby_E, Super_Novice_E | ruleset.native_class_acceptance, ruleset.adoption_baby, ruleset.profile_class_frontier |
| Sword lineage | Swordman, Knight, Knight2, Crusader, Crusader2, Swordman_High, Lord_Knight, Lord_Knight2, Paladin, Paladin2, Baby_Swordman, Baby_Knight, Baby_Knight2, Baby_Crusader, Baby_Crusader2 | Baby_Royal_Guard, Baby_Royal_Guard2, Baby_Rune_Knight, Baby_Rune_Knight2, Dragon_Knight, Dragon_Knight2, Imperial_Guard, Imperial_Guard2, Royal_Guard, Royal_Guard2, Royal_Guard_T, Royal_Guard_T2, Rune_Knight, Rune_Knight2, Rune_Knight_T, Rune_Knight_T2 | specialist.class_mounts, ruleset.transcendence_rebirth |
| Mage lineage | Mage, Wizard, Sage, Mage_High, High_Wizard, Professor, Baby_Mage, Baby_Wizard, Baby_Sage | Arch_Mage, Baby_Sorcerer, Baby_Warlock, Elemental_Master, Sorcerer, Sorcerer_T, Warlock, Warlock_T | specialist.skill_menus, specialist.elemental_and_later_companions |
| Archer lineage | Archer, Hunter, Bard, Dancer, Archer_High, Sniper, Clown, Gypsy, Baby_Archer, Baby_Hunter, Baby_Bard, Baby_Dancer | Baby_Minstrel, Baby_Ranger, Baby_Ranger2, Baby_Wanderer, Minstrel, Minstrel_T, Ranger, Ranger2, Ranger_T, Ranger_T2, Troubadour, Trouvere, Wanderer, Wanderer_T, Windhawk, Windhawk2 | specialist.falcon, specialist.traps_ground_units, specialist.performances_duets |
| Acolyte lineage | Acolyte, Priest, Monk, Acolyte_High, High_Priest, Champion, Baby_Acolyte, Baby_Priest, Baby_Monk | Arch_Bishop, Arch_Bishop_T, Baby_Arch_Bishop, Baby_Sura, Cardinal, Inquisitor, Sura, Sura_T | ruleset.native_class_acceptance, ruleset.transcendence_rebirth |
| Merchant lineage | Merchant, Blacksmith, Alchemist, Merchant_High, Whitesmith, Creator, Baby_Merchant, Baby_Blacksmith, Baby_Alchemist | Baby_Genetic, Baby_Mechanic, Baby_Mechanic2, Biolo, Genetic, Genetic_T, Mechanic, Mechanic2, Mechanic_T, Mechanic_T2, Meister, Meister2 | specialist.cart, specialist.class_craft_interfaces, specialist.homunculus_lifecycle, specialist.companion_control, specialist.class_mounts |
| Thief lineage | Thief, Assassin, Rogue, Thief_High, Assassin_Cross, Stalker, Baby_Thief, Baby_Assassin, Baby_Rogue | Abyss_Chaser, Baby_Guillotine_Cross, Baby_Shadow_Chaser, Guillotine_Cross, Guillotine_Cross_T, Shadow_Chaser, Shadow_Chaser_T, Shadow_Cross | specialist.skill_menus, specialist.class_craft_interfaces |
| Gunslinger lineage | Gunslinger | Baby_Gunslinger, Baby_Rebellion, Night_Watch, Rebellion | specialist.expanded_class_resources |
| Ninja lineage | Ninja | Baby_Kagerou, Baby_Ninja, Baby_Oboro, Kagerou, Oboro, Shinkiro, Shiranui | specialist.expanded_class_resources |
| Taekwon and linker | Taekwon, Star_Gladiator, Star_Gladiator2, Soul_Linker | Baby_Soul_Linker, Baby_Soul_Reaper, Baby_Star_Emperor, Baby_Star_Emperor2, Baby_Star_Gladiator, Baby_Star_Gladiator2, Baby_Taekwon, Sky_Emperor, Sky_Emperor2, Soul_Ascetic, Soul_Reaper, Star_Emperor, Star_Emperor2 | specialist.expanded_class_resources |
| Unproven special/experimental keys | Gangsi, Death_Knight, Dark_Collector | no extra keys in this group | ruleset.profile_class_frontier |
| Summoner lineage | none | Baby_Summoner, Spirit_Handler, Summoner | ruleset.profile_class_frontier |

Each raw key is reconciled to its cached `Job:` line in JSON. First jobs do not inherit second/trans specialist prerequisites automatically; high/baby/appearance aliases remain stage-specific. Renewal-only descendants, including current guide fourth/expanded jobs, are a frontier, not active enablement. Acolyte/Thief/Novice grouping does not pretend their skill-state exceptions are exhaustively audited.

## Feature catalogue

### specialist.pet_lifecycle — Pet capture, egg hatch/return, hunger/intimacy, equipment and menus

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** all eligible player classes; item acquisition onward.
**Pre-re:** candidate classic system; actual pet DB/config enablement unknown. **Renewal:** candidate; later auto-feed/evolution differs. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Owned pet ID/species, received hunger/intimacy/status, tame item/egg/food indices, observed target.
**Legal commands:** Use legal tame/egg item; received target selection; feed/info/performance/equipment/return menu.
**Prerequisites:** Correct tame item/target and egg/food; one owned pet; freshness; do not hardcode guide timers.
**Required native positive receipt (future, not executed):** Capture result + egg inventory delta; owned pet spawn/status; feed ACK and food delta; egg return/despawn.
**Negative acceptance cases (future, not executed):** wrong tame species; no food; foreign pet; invalid menu; duplicate hatch; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S2] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-02.txt:1214-1354`; `[S2] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-02.txt:1422-1455`; `[S2] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-02.txt:1634-1683`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:14714-14755`; `[S14] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-17.txt:1-1`.

### specialist.homunculus_lifecycle — Create/call/vaporize/resurrect/feed/evolve homunculus

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Alchemist, Creator, Genetic (Renewal only); learned homunculus skills and lawful acquisition.
**Pre-re:** classic Alchemist/Creator candidate. **Renewal:** Genetic/Homunculus S is separate gated expansion. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Owner/summon ID, class, HP/SP, life/vapor state, hunger/intimacy, skills, food/item consumption.
**Legal commands:** Learned summon/call/rest/resurrect skill; owned feed/info menu; legal evolution via item/NPC.
**Prerequisites:** Pinned tree prerequisites, lawful embryo/food, required intimacy/item/NPC observed; no guide-only mutation permission.
**Required native positive receipt (future, not executed):** Owned creation/status; vapor/despawn and later same ownership call; food ACK; class-change and updated skill tree.
**Negative acceptance cases (future, not executed):** absent embryo; dead vs vapor confusion; no food; insufficient evolution prerequisites; invalid mutation class; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S3] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-03.txt:259-283`; `[S3] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-03.txt:595-685`; `[S3] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-03.txt:846-971`; `[S3] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-03.txt:1114-1155`; `[S15] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-18.txt:1-2`.

### specialist.companion_control — Separate homunculus/mercenary movement, attack and skill actor

**Tier / priority:** `missing` / P0. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Alchemist/Creator, mercenary-eligible classes; active owned summon.
**Pre-re:** candidate owned-unit command family. **Renewal:** candidate, requires distinct per-unit state. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received own unit ID, position, HP/SP, learned unit skills, target/range and owner epoch.
**Legal commands:** Recall/move owned unit; attack observed legal target; use its skill not SELF skill.
**Prerequisites:** Active owned unit; correct routing/class/skill/target; separate cooldown/arrival checks.
**Required native positive receipt (future, not executed):** Unit movement arrival or unit-attributed damage/skill result, not SELF action ACK.
**Negative acceptance cases (future, not executed):** foreign unit; expired/despawned unit; SELF skill ID sent as unit skill; stale target; owner change; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:15699-15780`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:12762-12865`.

### specialist.mercenary_contract — Mercenary hiring, contract lifetime, loyalty and termination

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** eligible classes subject to scroll/NPC restrictions; legal contract acquisition.
**Pre-re:** classic candidate; availability unknown. **Renewal:** candidate; guide version not config. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Owned mercenary ID/class, HP/SP, skills, lifetime, loyalty and kill-count if actually received.
**Legal commands:** Use eligible contract scroll/NPC; owned commands; legal heal/dismiss.
**Prerequisites:** Contract item, required level/loyalty, one active mercenary, actual supplier enabled.
**Required native positive receipt (future, not executed):** Scroll consumed + owned info/skill list; contract end/death messages and unit removal.
**Negative acceptance cases (future, not executed):** below eligibility; duplicate contract; expired commands; no scroll; death mistaken for normal expiry; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S4] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-04.txt:56-80`; `[S4] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-04.txt:270-330`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:18283-18350`; `[S17] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-20.txt:1-1`.

### specialist.class_mounts — Peco riding and separate dragon/gryphon/warg/mado states

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Knight/Crusader, Lord Knight/Paladin, Renewal mounted branches; learned riding/license and enabled rental.
**Pre-re:** Peco candidate; third/fourth mount branches not automatically applicable. **Renewal:** dragon/gryphon/warg/mado gated by actual class, skill and NPC. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received actual job, riding option, skills, equipment and NPC rental dialogue; SELF movement/state.
**Legal commands:** Received lawful rental/dismount interaction or learned mount skill; no invoking server script APIs.
**Prerequisites:** KN_RIDING for Peco; distinct later class/license constraints; actual NPC availability.
**Required native positive receipt (future, not executed):** Updated SELF mount option/class appearance and lawful inventory/fee state; movement effects observed.
**Negative acceptance cases (future, not executed):** no riding skill; wrong class; all-riding conflict; cannot use unavailable later-class rental; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/domain/build_templates.py:1-36`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:11321-11349`; `[S41] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-script.cpp:10726-10743`; `[S41] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-script.cpp:22815-22855`; `[S9] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-09.txt:3724-3794`.

### specialist.falcon — Falcon acquisition/dismissal and learned/auto attack

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Hunter, Sniper, eligible baby variants; HT_FALCON and lawful rental.
**Pre-re:** classic candidate. **Renewal:** Ranger/warg/bird coexistence must be separately checked. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received falcon option, actual class and HT skills, target and ammo/weapon; autoattack outcomes.
**Legal commands:** Received NPC rental; legal dismissal; learned Blitz Beat on observed target.
**Prerequisites:** HT_FALCON and enabled supplier; correct skill/cost; auto-proc not controllable guaranteed action.
**Required native positive receipt (future, not executed):** SELF falcon-option update; skill/auto-proc damage attributed to actual received event.
**Negative acceptance cases (future, not executed):** no falcon skill; wrong class; impossible coexistence assumption; proc absence not fabricated success; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:11308-11315`; `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:665-764`; `[S18] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-21.txt:1-1`.

### specialist.cart — Cart ownership/options, capacity and cart-linked skills

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Merchant, Blacksmith/Whitesmith, Alchemist/Creator, Renewal descendants; MC_PUSHCART acquired.
**Pre-re:** candidate; NEW_CARTS changes wire/state representation. **Renewal:** candidate; do not equate mado and cart. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Cart state/list, weight/capacity, eligible skill, inventory indices and SELF status.
**Legal commands:** Legal cart rental/select/dismiss and item transfer; learned cart combat with prerequisites.
**Prerequisites:** MC_PUSHCART; public conditional NEW_CARTS branch does not identify compiled active flag; no hidden inventory.
**Required native positive receipt (future, not executed):** Cart list/state/weight update, correlated transfers; cart skill effect with lawful cost.
**Negative acceptance cases (future, not executed):** no pushcart; invalid cart type; over capacity; stale item index; nonexistent cart; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:11260-11302`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:12660-12710`; `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:233-275`.

### specialist.traps_ground_units — Traps placement, footprint, lifetime, activation and recovery

**Tier / priority:** `missing` / P0. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Hunter/Sniper, other learned ground-unit classes, Ranger separately; ground skill and materials acquired.
**Pre-re:** classic trap candidate. **Renewal:** Ranger trap rules not classic substitutions. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received own/visible ground units, tiles/path legality, target, skills/materials, lifetime/removal.
**Legal commands:** Place eligible ground skill; legal trap removal/recovery skill, safe path and placement.
**Prerequisites:** Skill/level/cost plus map/unit overlap, NPC proximity and placement restrictions.
**Required native positive receipt (future, not executed):** Received unit spawn/owner/tile followed by actual trigger/damage/status or removal and item deltas.
**Negative acceptance cases (future, not executed):** illegal tile; overlap/reiteration; missing trap item; enemy trap ownership; stale unit recovery; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:475-505`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:3352-3520`; `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:665-764`; `[S18] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-21.txt:1-1`.

### specialist.performances_duets — Songs/dances, stop/encore, ensemble partner and Renewal chorus

**Tier / priority:** `missing` / P0. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Bard/Dancer, Clown/Gypsy, Minstrel/Wanderer separately; trained skill and eligible partner/equipment.
**Pre-re:** classic performances/duets; distinct #ifndef RENEWAL behavior. **Renewal:** chorus and modern performance rules separate. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Actual jobs/sex where required, partner presence/range/skill, equipped instrument/whip, SP and active performance.
**Legal commands:** Start learned performance; lawful duet coordination; stop/adaptation/encore only legal current state.
**Prerequisites:** Pinned skill partner checks, weapon/skill/status/cost; not merely being in party.
**Required native positive receipt (future, not executed):** Observed performer/partner state and ground/status effect; legal stop/encore transition and SP consumption.
**Negative acceptance cases (future, not executed):** no partner; partner out of range; wrong weapon; unlearned ensemble; stop cooldown; mix Renewal duration rules; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:8005-8080`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:8347-8358`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:8525-8558`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:9606-9630`; `[S21] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-24.txt:1-1`; `[S22] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-25.txt:1-2`.

### specialist.skill_menus — Skill-specific selection menus: Hindsight, spellbooks/release, copied/autoshadow choices

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Sage/Professor, Warlock and Shadow Chaser separately; learned menu skill and received menu.
**Pre-re:** Sage Hindsight candidate. **Renewal:** later selection/spellbook interfaces only corresponding classes. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received menu ID/options and generation, learned candidate skills, pending skill context, SP/status.
**Legal commands:** Open lawful learned skill menu then choose only received eligible entry; cancel safely.
**Prerequisites:** Actual pending server menuskill context and learned prerequisite; NPC menu protocol is not skill menu.
**Required native positive receipt (future, not executed):** Correct resulting status/selected skill or stored/released spell state and cost; menu cleared.
**Negative acceptance cases (future, not executed):** unsolicited choice; unlearned candidate; wrong menu family; replay after clear; fabricated spellbook availability; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_npc_dialogue.py:1-177`; `src/robots/ports/mechanics.py:14-26`.
**Cached source:** `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:10706-10749`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:13490-13520`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:19847-19870`.

### specialist.class_craft_interfaces — Forge/brew and class-special production/repair menus

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Blacksmith/Whitesmith, Alchemist/Creator, Renewal rune/poison/material producers; recipe, skill, tools and materials acquired.
**Pre-re:** classic forge/brew candidate. **Renewal:** runemaking/new poison and later recipes separate. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received production/repair menu, recipe candidates, skill/stats, materials/tools, relevant party status and result.
**Legal commands:** Select lawful received forge/brew/repair entry; production is not generic NPC menu.
**Prerequisites:** Pinned eligible recipe/tool/materials/learned skill; no trading conflict; transaction economy audited elsewhere.
**Required native positive receipt (future, not executed):** Server production/repair result plus exact material consumption and inventory outcome; failed RNG attempt is not success.
**Negative acceptance cases (future, not executed):** not in production menu; unavailable recipe; missing tool/materials; trading; replay; outcome probability treated as certainty; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:13195-13223`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:13267-13310`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:12844-13055`; `[S19] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-22.txt:1-1`; `[S20] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-23.txt:1-1`.

### specialist.expanded_class_resources — Expanded class specialist states: ninja/gunslinger resources and Taekwon/link restrictions

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Ninja, Gunslinger, Taekwon, Star Gladiator, Soul Linker; actual expanded job and learned skills.
**Pre-re:** tree candidates present; jobchanger/flags unknown. **Renewal:** Kagerou/Oboro/Rebellion/Star Emperor/Soul Reaper distinct gated branches. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Observed ammo/weapon, coin/spirit/charm counters where supplied, stance/combo/link status, map/target constraints.
**Legal commands:** Learned legal skill/resource generation; choose valid target; legal stance/combo sequence.
**Prerequisites:** Exact branch and learned skills; ammunition/catalyst; link recipient/class restrictions; no Renewal guide-only extras.
**Required native positive receipt (future, not executed):** Received counter/stance/status change and skill effect/cost; branch/map/target-specific result.
**Negative acceptance cases (future, not executed):** Soul Linker using banned kicks; Taekwon Mission wrong class; combo not ready/repeat; absent ammo/coins; unsupported charms; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:1727-1971`; `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:2972-3253`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:8416-8435`; `[S5] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt:8478-8524`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:19874-19886`; `[S30] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-33.txt:1-2`; `[S31] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-34.txt:1-1`; `[S32] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-35.txt:1-1`; `[S33] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-36.txt:1-1`.

### specialist.elemental_and_later_companions — Sorcerer elementals and later-class summon/machine frontier

**Tier / priority:** `missing` / P2. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** Sorcerer, Elemental Master and later summon classes separately; eligible later job and learned summon/control skill.
**Pre-re:** not automatically applicable; no Sorcerer tree in cached pre-re tree. **Renewal:** candidate elemental lifecycle/modes; later features require separate evidence. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Owned elemental ID/class, HP/SP, lifetime/mode, owner state/skills and catalysts.
**Legal commands:** Learned summon/control/dismiss skill; target/control only supported owned mode.
**Prerequisites:** Actual enabled job/tree, catalyst/skill/level, separate elemental mode contracts; do not recycle homunculus IDs.
**Required native positive receipt (future, not executed):** Owned elemental info/status; observed mode and lawful skill effect; timeout/dismiss removal.
**Negative acceptance cases (future, not executed):** wrong owner; invalid mode/class; summon timeout; missing catalyst; unsupported newer companion interface; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S36] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-elemental.cpp:42-136`; `[S36] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-elemental.cpp:184-220`; `[S36] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-elemental.cpp:378-435`; `[S36] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-elemental.cpp:493-535`; `[S9] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-09.txt:4595-4761`; `[S28] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-31.txt:1-1`.

### ruleset.marriage — Marriage, spouse skills and divorce interfaces

**Tier / priority:** `missing` / P2. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** eligible adult player characters; consenting partner plus ceremony.
**Pre-re:** candidate official script; fee/sex/VIP/map policy unknown. **Renewal:** candidate; current guides not active marriage policy. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received ceremony NPC dialogue, partner identity/consent/presence, eligible items/fee and spouse skills.
**Legal commands:** Both parties consent through received NPC ceremony; lawful spouse skill; explicit divorce only with authorization.
**Prerequisites:** Enabled script and its branch conditions; adult eligibility, actual items/fees; never automatic human relationships.
**Required native positive receipt (future, not executed):** Ceremony success + received relationship/skill/item changes; spouse-target effect; lawful divorce removal.
**Negative acceptance cases (future, not executed):** missing partner/consent; wrong eligibility/items/fees; partner offline; stale ceremony; guide overrides local script; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S13] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-15.txt:1-85`; `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:12811-12860`; `[S23] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-26.txt:1-1`.

### ruleset.adoption_baby — Adoption handshake, baby conversion and family skills

**Tier / priority:** `missing` / P2. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** eligible Novice/first jobs/Supernovice, married eligible parents; parents and eligible child; constrained new stage.
**Pre-re:** candidate; special expanded baby availability not inferred. **Renewal:** additional baby branches require actual policy. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Observed parents/child IDs, reciprocal spouse relation, same party, rings equipped, levels/class and invitation.
**Legal commands:** Explicit consensual adopt request/reply; valid family skills; never SQL/class replacement.
**Prerequisites:** Pin requires parents married/in same party, equipped rings, level >=70, no existing child; child unmarried and eligible class.
**Required native positive receipt (future, not executed):** Adoption response plus received baby job/family skill changes and both parent links if protocol exposes them.
**Negative acceptance cases (future, not executed):** parents below70; no rings; mismatched spouse/party; child married/already adopted; stale invitation; declined adoption; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_progression.py:87-103`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:1672-1757`; `[S6] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt:17599-17655`; `[S24] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-27.txt:1-1`.

### ruleset.transcendence_rebirth — Transcendent rebirth/reset and high-job stage invalidation

**Tier / priority:** `missing` / P1. No specialist action in current action union; generic NPC source readiness does not accept this family natively.
**Class/stage:** eligible classic second jobs, high novice/first/trans second families; legal rebirth quest then renewed stage progression.
**Pre-re:** classic candidate; cached guide is not proof quest script enabled. **Renewal:** third/fourth transition is separate, not generic rebirth. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Actual class/stage/base-job levels and observed quest dialogue/items/fee; post-transition points/skill/equipment reset.
**Legal commands:** Follow received lawful rebirth quest; refresh actual class/stats/skills/build stage afterward.
**Prerequisites:** Guide describes base99 eligible second classes; exact enabled NPC and additional requirements unverified; inspect legal quest before action.
**Required native positive receipt (future, not executed):** Actual received job/level/skill/points reset and inventory/equipment snapshot; refresh identity/capability epoch.
**Negative acceptance cases (future, not executed):** ineligible expanded/baby job; missing quest requirement; reset inferred from dialogue; pre-rebuild skill actions using stale state; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/adapters/native_progression.py:87-103`; `src/robots/domain/build_templates.py:1-36`; `src/robots/domain/actions.py:1-94`; `src/robots/adapters/native_npc_dialogue.py:1-177`.
**Cached source:** `[S25] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-28.txt:1-1`; `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:9237-9290`; `[S1] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt:10846-10920`; `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:1972-2002`.

### ruleset.profile_class_frontier — Enabled-class authority, aliases, special actors and version/ruleset frontier

**Tier / priority:** `offline_model` / P0. Bounded offline catalogs/plans or codec evidence only; no class-wide native acceptance.
**Class/stage:** all cached job keys; NPC/companion/appearance roles are not player jobs; every stage.
**Pre-re:** 77 cached tree keys, not 77 proven playable enabled classes. **Renewal:** 175 cached tree keys, not 175 proven enabled classes; MAIN20180704 cannot automatically expose later UI. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Actual received raw job/class, authoritative public profile/version, observed jobchanger and feature availability; unknown flags explicit.
**Legal commands:** Allow only verified actual class/stage and supported interface; block unknown/disabled/version mismatch.
**Prerequisites:** Active MAIN20180704/pre-re supplied by scope; compile profile and scripts/features need independent current public evidence; no enum/count-based allowlist.
**Required native positive receipt (future, not executed):** Authorized future observed class/job change and actual supported feature receipt; DB existence alone fails acceptance.
**Negative acceptance cases (future, not executed):** mounted alias counted as distinct progression; Gangsi/Death_Knight/Dark_Collector assumed playable; Summoner/latest jobs inferred from enum; NPC presentation treated player job; Renewal menu under classic; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/adapters/native_progression.py:87-103`; `src/robots/ports/mechanics.py:14-26`; `src/robots/adapters/mechanics_yaml.py:528-599`; `src/robots/domain/build_templates.py:1-36`.
**Cached source:** `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:3254-3550`; `[S9] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-09.txt:6162-6398`; `[S9] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-09.txt:6646-8760`; `[S40] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-config-renewal.hpp:7-24`.

### ruleset.native_class_acceptance — Class-wide acceptance gate across actual skill/stat/equipment and special actions

**Tier / priority:** `offline_pipeline` / P0. Bounded offline catalogs/plans or codec evidence only; no class-wide native acceptance.
**Class/stage:** every enabled player class; current actual job/stage, not chosen persona template.
**Pre-re:** offline catalogs/stat plans do not establish native class play. **Renewal:** Renewal catalogs have same acceptance boundary. **Flags:** unknown; public code/DB presence is not enablement.
**Visible observations:** Received actual job/levels, learned skills/free points, complete gear/state, specialist observations and costs.
**Legal commands:** Only supported gated native commands; add class capabilities only after real receipts and policy.
**Prerequisites:** Current selected native progression explicitly supports only JOB_NOVICE=0; NPC reviewed source only; equipment representation codec only.
**Required native positive receipt (future, not executed):** Future end-to-end legally equipped/trained class loop with actual skill and specialist effects; negative cases exercised on exact profile.
**Negative acceptance cases (future, not executed):** template name authorizes raw job; guide becomes telemetry; codec becomes equip acceptance; offline success becomes gameplay; enabled class lacks special capability; stale session/map/owner identity or receive-frame gap: fail closed; no inferred success from send.
**Implementation:** `src/robots/adapters/native_progression.py:87-103`; `src/robots/domain/actions.py:1-94`; `src/robots/domain/build_templates.py:1-36`; `src/robots/adapters/native_equipment.py:1-71`; `wiki/guides/goals-ledger.md:50-63`.
**Cached source:** `[S8] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt:44-87`; `[S40] /home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-config-renewal.hpp:7-24`.

## Omission and unsupported-evidence checklist

- Enabled jobchanger/NPC script inventory and compiled class-specific flags were not read; every enablement verdict remains unknown.
- Per-skill exhaustive catalog is out of scope: ordinary combat, skill/stat spending and job progression belong to combat-progression; transaction/crafting economics belong to economy-inventory.
- Supernovice angel/death-count and spirit exceptions, Monk spheres/combo, Rogue copying/plagiarism, Sage endow/land effects, party-sacrament/devotion and class quest skills need individual skill-state follow-ups; family grouping is not per-skill acceptance.
- Taekwon celestial map/day/hate assignments, mission/ranker policies and Soul Linker recipient/Ka/Es targeting need pin-specific restriction extraction beyond the covered stance/mission checks.
- Warlock spellbook/release full menu framing, Ranger warg coexistence, Mechanic fuel/overheat/repair, Genetic homunculus-S mutation quest and consumable producers lack complete active-profile interface evidence here.
- Doram/Summoner and third/fourth/expanded successor interfaces, newer pets/homunculus AI changes and later UI require explicit compiled/version/ruleset authority; modern guides are not active MAIN20180704 configuration.
- Special event/costume/wedding sprites, mounted aliases, NPC presentations and experimental keys are not independently playable classes without legal transition evidence.
- Rebirth NPC script and adoption script fetch are not complete: adoption is instead grounded in pc.cpp/clif.cpp; exact rebirth quest fees/weight/skills prerequisites remain unverified.
- No native gameplay, protocol registration/layout exercise, compilers or tests ran in this recovery. Future acceptance must use actual authorized server receipts, not guide claims or fabricated results.

## Failed fetches

- `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/job_db.yml` — HTTP Error 404: Not Found. Not supporting evidence.
- `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/job_db.yml` — HTTP Error 404: Not Found. Not supporting evidence.
- `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/other/adoption.txt` — HTTP Error 404: Not Found. Not supporting evidence.

## Cached source register

- **S1** pc.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-01.txt` (16169 lines); SHA256 `d12704c1ef7f8321c255175b6f61aa396209b931e2b1687fbbd16963d1def652`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pc.cpp`.
- **S2** pet.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-02.txt` (2504 lines); SHA256 `43ee63394f4e5301e032ad006fb4c3dd87f717e0efb935ab33d4fa9758b85065`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pet.cpp`.
- **S3** homunculus.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-03.txt` (2063 lines); SHA256 `d5ec4874e6a6aaf0acb76063489ee00f38b96bde51327f55022b862f2d176c61`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/homunculus.cpp`.
- **S4** mercenary.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-04.txt` (955 lines); SHA256 `bca5adbbe2f475b777bfac092c521d9ce86419f4f0f3064898427462801d3d70`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/mercenary.cpp`.
- **S5** skill.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-05.txt` (16344 lines); SHA256 `aad3c2f3968e0ddf38b89aff953d77a4cae66a0aa54b539a47723dd5f25b6c04`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/skill.cpp`.
- **S6** clif.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-06.txt` (25900 lines); SHA256 `0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/clif.cpp`.
- **S7** npc.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-07.txt` (6384 lines); SHA256 `90d582661668e5cb8567de5a7b92d067e5d0db479963b00bab340af9fe477534`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/npc.cpp`.
- **S8** skill_tree.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-08.txt` (3579 lines); SHA256 `fafe80390ac7c4ad79b4fb258614684250ccc9b72155d9218ea4ee7c063c7f54`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/skill_tree.yml`.
- **S9** skill_tree.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-09.txt` (8760 lines); SHA256 `9f093dad42651580b9c349dabed68e2cf13e46dbec3d4ada79d326661d863f09`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/skill_tree.yml`.
- **S10** pet_db.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-12.txt` (63 lines); SHA256 `514589d92172940a6d50459c593e297ac49bfd001272bf3ff94dcd724e67ff8f`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pet_db.yml`.
- **S11** homunculus_db.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-13.txt` (65 lines); SHA256 `55741451ace5e8628d2c3a9f406143c648500a4f2e5f09be0f479e4d52b20846`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/homunculus_db.yml`.
- **S12** mercenary_db.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-14.txt` (1438 lines); SHA256 `bb9870b40a5e332a4a184cbf310f90f7589513cc12f508de138998d432a62e61`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/mercenary_db.yml`.
- **S13** marriage.txt — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-15.txt` (1000 lines); SHA256 `d89d49495e6136c1addd3c3b09d05a088788fd9d2f35e9dae45d7d85f494dec5`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/other/marriage.txt`.
- **S14** Pet_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-17.txt` (1 lines); SHA256 `5134db907e586bbc5f6fbb536b344d5c947d9fec627fb3b23eb5966586c2fb7c`; origin `https://irowiki.org/classic/Pet_System`.
- **S15** Homunculus_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-18.txt` (2 lines); SHA256 `79d04f80fe8a1e033489c4ddb0ef0dc0451d829bfaacc4f23a2a4bd12639bc5a`; origin `https://irowiki.org/classic/Homunculus_System`.
- **S16** Homunculus_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-19.txt` (1 lines); SHA256 `8cf5d85828f324c8680e8576455816425078e2d652b106d3a48381521cb43515`; origin `https://irowiki.org/wiki/Homunculus_System`.
- **S17** Mercenary_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-20.txt` (1 lines); SHA256 `4190706fba28e24755da8c6533bf227a1ab0b7bb7361a27a4aecaaf9868a96aa`; origin `https://irowiki.org/classic/Mercenary_System`.
- **S18** Hunter — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-21.txt` (1 lines); SHA256 `e0de07ba87c88bca2e318f952f16f1a0041f475c4814d39b593f0f93d9f5772a`; origin `https://irowiki.org/classic/Hunter`.
- **S19** Blacksmith — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-22.txt` (1 lines); SHA256 `a1fef31317dec15323f4e14b84ee7efef1b745954daac47fb66ab545067d5e66`; origin `https://irowiki.org/classic/Blacksmith`.
- **S20** Alchemist — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-23.txt` (1 lines); SHA256 `2b5c62cf1168f61dbfa943ad1210a340a1a606f3d939a68c6f756c4d680c5f22`; origin `https://irowiki.org/classic/Alchemist`.
- **S21** Bard — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-24.txt` (1 lines); SHA256 `05983623b6e9da11c861a5d6f55fa1eec263c8b5654921e6367c00d36f696a40`; origin `https://irowiki.org/classic/Bard`.
- **S22** Dancer — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-25.txt` (2 lines); SHA256 `d54cce57d0a9f02fbe251337419e83576767aa974e30c49362bbf17ce3f80f16`; origin `https://irowiki.org/classic/Dancer`.
- **S23** Marriage_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-26.txt` (1 lines); SHA256 `be29270d9ad12509f4e3064765638c2e1f736071a949f2de6b6c8a326fab0161`; origin `https://irowiki.org/classic/Marriage_System`.
- **S24** Adoption_System — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-27.txt` (1 lines); SHA256 `482a3569cbb18e430f7bbd38d488263360b66aee9ed55759e45a08c4ea9efc3b`; origin `https://irowiki.org/classic/Adoption_System`.
- **S25** Transcendent — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-28.txt` (1 lines); SHA256 `cfc22fde238505e1f88c1c97b25278e53e0982390a1ec93dc725f4b2fe3933a0`; origin `https://irowiki.org/classic/Transcendent`.
- **S26** Ranger — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-29.txt` (3 lines); SHA256 `e6e0e342b28390f898ddfc113694e4c0b8080121e7f0ca78c9d4a39878ff1dd5`; origin `https://irowiki.org/wiki/Ranger`.
- **S27** Mechanic — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-30.txt` (2 lines); SHA256 `4e896adb738a038e66250f66b6be97a0cd915370129f6f362e96114c7d235552`; origin `https://irowiki.org/wiki/Mechanic`.
- **S28** Sorcerer — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-31.txt` (5 lines); SHA256 `4a55395a448aed7cbf35f39c98a2adbe108e6bcdc2ecf76472f7e81f842d044f`; origin `https://irowiki.org/wiki/Sorcerer`.
- **S29** Rune_Knight — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-32.txt` (4 lines); SHA256 `34d716f8b107ea35aad778cb964a144920aa4036bd11ace33fa0280815cb7d1f`; origin `https://irowiki.org/wiki/Rune_Knight`.
- **S30** TaeKwon_Master — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-33.txt` (2 lines); SHA256 `f1d127ace6091c8fbd77712a12be103302af07897e2633dec21559df8b8fccc0`; origin `https://irowiki.org/wiki/TaeKwon_Master`.
- **S31** Soul_Linker — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-34.txt` (7 lines); SHA256 `be7340ae511b1ba1fb0da301ab1890586bf8a80c9485b5508e785aae4dd72e58`; origin `https://irowiki.org/wiki/Soul_Linker`.
- **S32** Ninja — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-35.txt` (1 lines); SHA256 `1e35001e8fe1fa80050a5a5133e1ab48e1438017205e01912362ba0d68fcb2fa`; origin `https://irowiki.org/wiki/Ninja`.
- **S33** Gunslinger — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-36.txt` (1 lines); SHA256 `2361f995d995148d6df730be7f7753f7eff4e47dcd4df7e6ff36810291ed58db`; origin `https://irowiki.org/wiki/Gunslinger`.
- **S34** Doram — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-37.txt` (1 lines); SHA256 `13355db7bb79500ba8c0557d437041ff39176b8e366db1b7d6ea03543f8471e6`; origin `https://irowiki.org/wiki/Doram`.
- **S35** Classes — public_guide_advice_only; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/source-38.txt` (1 lines); SHA256 `0173f3a267e30c8a8eb406287dd8283d9a4929f9b9c22edb6a264a30bba1c783`; origin `https://irowiki.org/wiki/Classes`.
- **S36** src/map/elemental.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-elemental.cpp` (1161 lines); SHA256 `cfa0e8dddd61f4f2e4d2cb161d501c6abacba983a5dc9e80b2b802b0f75e72dd`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/elemental.cpp`.
- **S37** src/map/pc.hpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-pc.hpp` (1798 lines); SHA256 `e9ad34a7661c061804328ad486f97a19100f1068e2836e4037d474fc4e469b58`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pc.hpp`.
- **S38** db/elemental_db.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-db-elemental_db.yml` (67 lines); SHA256 `0f067999c81556ab4792d2b9f92cd2a13b109a5c012acac80f6b1291f4e8cfe5`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/elemental_db.yml`.
- **S39** db/re/elemental_db.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-db-re-elemental_db.yml` (312 lines); SHA256 `13652d92209ba9d8df691106ac30f28c8d93cf6bd2843a2c24c8be221676fdb5`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/elemental_db.yml`.
- **S40** src/config/renewal.hpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-config-renewal.hpp` (78 lines); SHA256 `22b15dfb9151bf59f52ea5f319b9d34e66ced204c441d320c8cd2c14fccb61b7`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/config/renewal.hpp`.
- **S41** src/map/script.cpp — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/extra-src-map-script.cpp` (28660 lines); SHA256 `e5554910bef9448542ebd19b7e6e9db529c8e75d6077b0770c8a9ce05c7034c0`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/script.cpp`.
- **S42** db/pre-re/job_stats.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/db-pre-re-job_stats.yml` (2930 lines); SHA256 `fbdec3205fa96c364f6f7fcced30fc0322d5f933878f88734e96bd89e01a3f76`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/job_stats.yml`.
- **S43** db/re/job_stats.yml — pinned_public_server_source; accessed 2026-10-08; `/home/otto/.hermes/cache/scratch/ro-gameplay-audit/class-specials-rulesets/db-re-job_stats.yml` (7817 lines); SHA256 `02a29a58966bf6427036278cb4f4cd729fb5fd1ddc4fdd6debd6569274df708d`; origin `https://raw.githubusercontent.com/rathena/rathena/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/job_stats.yml`.

## Verification

Both report artifacts were parsed/reconciled after creation. Only artifact checks and cache integrity checks ran; no project tests, compilers, live effects or milestone promotion. All receipt/negative cases above are future acceptance requirements. The old batch remains interrupted.
