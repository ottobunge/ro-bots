---
title: Renewal build research — separate ruleset catalog
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, architecture, testing, ops]
---

# Renewal build research

Research input for [[goals-ledger]] and [[adr-009-character-builds-item-cognition]], **not executable templates or initialization approval**. The existing native world remains **20180704 MAIN / pre-Renewal**; this page does not change it. Twelve archetypes cover tank/healer/mage/hunter/support/melee, two each. Some guide mechanics conflict with the pinned database; those gaps are explicit below.

## Evidence and ruleset boundary

- **Verified local (V):** read-only examination of `rathena/db/re/{item_db_equip,skill_db,skill_tree,job_stats}.yml`, checkout `e985006171d2eb320ee512a653f4c83aea3d81b6`. Skill existence, maximum levels, immediate tree prerequisites, item identifiers and declared equip restrictions were checked.[11][12][13]
- **Verified local jobs:** class families occur in `job_stats`.[14] This is database evidence, not proof of running Renewal mechanics.
- **Guide advice (G):** original collaborative iRO Wiki build sections, retrieved 2026-10-05. This establishes what their authors recommend, not an official guarantee. Historical Royal Guard/Sorcerer/Maestro revision contents were retrieved through the site's own MediaWiki API; their revision dates are preserved in Sources. Search snippets alone were not used to fill builds.
- **Unverified (U):** aggregate stat affordability at a particular level, complete skill-point budgets, gear combinations/refines/enchants, loot/quest availability, formulas, encounter viability and live performance. Stat bands are alternatives/milestone recommendations, **never all upper bounds simultaneously**. A `+` means an open guide recommendation, not permission to exceed the target world's cap.
- Third-job plans require Renewal with third jobs (often called Episode 13.2-era third-job rules). **Exact episode alone is insufficient:** choose the rebalance, base/job caps, stat caps, regional item implementation and quest availability. Below, `R175` means third-job Renewal with a 175-cap progression; `R-late` means later rebalanced iRO advice, potentially 200+/fourth-job-era equipment. Neither implies the current native server supports it. Historical guides do not certify an exact episode release.
- Every path below starts at Novice and uses rebirth: second job → rebirth/High Novice → high first job → transcendent second → third. Stop at third job unless the profile expressly says otherwise. Do not substitute a classic level-99 endpoint or skip rebirth where transcendent skills are required. The local trees contain the relevant inherited jobs; allocation after rebirth must be rebuilt, not added onto the original character's points.[13][14]
- No player-market prices researched or asserted. Database `Buy` fields are not market prices. No server/DB writes, bot initialization, dependency installation or classic-template changes belong to this catalog.

## Tank

### T1 — Royal Guard Banding off-tank, optional Devotion

- **Scope/source:** historical iRO `R175`, coordinated multi-Royal-Guard party, not a solo universal tank. Revision 61749 (2020-05-20) supports Banding's defense/party role and stat bands; it does **not** supply a complete Devotion-focused tank allocation.[1]
- **Path:** Swordman → Crusader → rebirth → High Swordman → Paladin → Royal Guard. **G stats:** STR 120; AGI 90–100; VIT 90–100; INT 1–80; DEX 100–120; LUK 1.[1]
- **V skill core / editorial target levels:** `LG_BANDING` 5 (requires `LG_PINPOINTATTACK` 3 + `LG_RAGEBURST` 1); `LG_PRESTIGE` 5 (`LG_TRAMPLE` 3); `CR_TRUST` 10; optional `CR_DEVOTION` 5 (`CR_REFLECTSHIELD` 5 + `CR_GRANDCROSS` 4). These names/levels/prerequisites exist locally; total budget is U.[12][13]
- **Gear goals:** shield-based reductions/HP before offensive luxury gear (editorial advice). V candidates: `2115 / Valkyrja's_Shield` level 65; `2153 / Imperial_Guard` shield level 102; `1433 / Imperial_Spear` one-hand spear level 102. Imperial pieces require Crusader-family third/fourth classes; a two-handed weapon cannot share the shield slots.[11]
- **Progression priorities (editorial/U):** Swordman damage/recovery for early quests → Crusader survivability → rebirth and Paladin prerequisite routing → level 102 spear/shield → coordinated Banding. **Gap:** no fully evidenced pure-Devotion stat plan or complete party/skill budget; do not instantiate this as a validated full tank template.

### T2 — Sura Mental Strength party/MVP tank

- **Scope/source:** third-job Renewal, `R175`; current Sura page retains a tank section that supports its bands, reduction-oriented equipment advice and vulnerability to Dispel. Its exact balance vintage is not specified.[2]
- **Path:** Acolyte → Monk → rebirth → High Acolyte → Champion → Sura. **G stats:** STR 80+; AGI 1+; VIT 94–120; INT 60–96; DEX 60–80; LUK 20–40.[2]
- **V core:** `MO_STEELBODY` 5 (`MO_COMBOFINISH` 3); `SR_GENTLETOUCH_REVITALIZE` 5 (Quiet 1, Cure 1, Energy Gain 3); `SR_RAISINGDRAGON` 10 (`MO_CALLSPIRITS` 5 + `SR_POWERVELOCITY` 1). Guide's “Rising Dragon” maps to local **Raising** Dragon, not an invented `SR_RISINGDRAGON` identifier.[12][13]
- **Gear goals:** G prioritizes reductions and healing consumables over simply maximizing VIT. V candidate shield `2115 / Valkyrja's_Shield` 65; HP/SP armor `2374 / Diabolus_Robe` 60, upper/third/fourth Acolyte family. Weapon choice is secondary to survival here.[2][11]
- **Progression priorities (editorial/U):** quest/party Acolyte → Monk combo prerequisites plus Mental Strength → rebirth → acquire reduction shield and potion reserve → add Sura upkeep buffs. Guide's 94 base/+6 job VIT immunity claim is **not** accepted without the selected server's job bonuses/status formula; Dispel encounters need an explicit fallback.[2]

## Healer

### H1 — Arch Bishop full support

- **Scope/source:** iRO third-job Renewal FS section, `R175`; **not** the same page's separate 2025 Adoramus/fourth-job talent build. Source supports heal/support priorities and bands, including alternative LUK choices.[3]
- **Path:** Acolyte → Priest → rebirth → High Acolyte → High Priest → Arch Bishop. **G stats:** STR 1; AGI variable; VIT 95+; INT 92–120; DEX 120; LUK 1 **or** 77 **or** 60–100. Unspecified AGI is a source gap, not a fabricated range.[3]
- **V core:** `AL_HEAL` 10; `AL_BLESSING` 10 (`AL_DP` 5); `AL_INCAGI` 10 (Heal 3); `AB_CHEAL` 3 (Heal 1); `AB_HIGHNESSHEAL` 5 (`AB_RENOVATIO` 1, itself Coluceo Heal 3); `AB_PRAEFATIO` 10 (`PR_KYRIE` 1). Further full-support allocation/budget is U.[12][13]
- **Gear goals (editorial):** heal effectiveness, SP sustainability and survival before damage. V `1625 / Healing_Staff` 55, Acolyte family; `2374 / Diabolus_Robe` 60 upper/third/fourth; shield `2115 / Valkyrja's_Shield` 65. Staff/robe scripts contain heal-power bonuses; no optimal-combination claim.[11]
- **Progression priorities (editorial/U):** party Heal/Blessing → Priest SP/recovery toolkit → rebirth for High Priest skills → group-heal/Praefatio core → refine support cooldown/cast priorities against the actual server. **Conflict:** guide calls Sacrament defining, but no Sacrament entry/`AB_SACRAMENT` exists in the inspected `db/re/skill_db.yml` or tree. Must resolve rebalance before adoption; do not silently fabricate it.[3][12][13]

### H2 — Arch Bishop hybrid support / Duple Light

- **Scope/source:** iRO Hybrid Support section, third-job `R175`; supports switching between healing and melee, not a pure healer with a free complete DPS tree.[3]
- **Path:** Acolyte → Priest → rebirth → High Acolyte → High Priest → Arch Bishop. **G stats:** STR 30–50; AGI 80–95; VIT 95; INT 92–100; DEX 50–80; LUK 70–100.[3]
- **V core:** `AB_DUPLELIGHT` 10 (`PR_ASPERSIO` 1); Heal 10; Coluceo Heal 3; Highness Heal 5. Healing prerequisites are H1's; Duple Light belongs to the Arch Bishop tree. Sacrament guidance has the same unresolved local conflict as H1.[12][13]
- **Gear goals:** G recommends mace/book and AGI-oriented equipment. V alternatives `1548 / Veteran_Hammer` 80 (Acolyte family mace), `1564 / Encyclopedia` 70 (Priest/Sage/StarGladiator book), and healing staff `1625 / Healing_Staff` 55 for a support weapon swap. These are alternatives, not three simultaneously equipped weapons.[3][11]
- **Progression priorities (editorial/U):** first maintain usable Heal/INT → rebirth support skills → invest AGI and a legal mace/book → Duple Light → group-heal upgrades. Test hit rate, SP and weapon switching before trading healing throughput for attack speed; complete dual-role budgets remain U.

## Mage

### M1 — Warlock all-purpose elemental AoE

- **Scope/source:** iRO's **level-162 basic all-purpose** section and 99/125/150/162/175 milestones, `R175`; excludes the page's newer 2025 Comet/talent plan. Source supports stat milestones and Temporal boot alternatives.[4]
- **Path:** Mage → Wizard → rebirth → High Mage → High Wizard → Warlock. **G stats at 162:** STR 1, AGI 70, VIT 80, INT 120, DEX 120, LUK 1; 125–162 progression spans AGI 1–70, VIT 54–80, INT 100–120, DEX 120. Extra post-162 points are choices, not a combined maximum.[4]
- **V core:** `HW_MAGICPOWER` 10; `WL_CRIMSONROCK` 5 (`WL_SUMMONFB` 1); `WL_JACKFROST` 5 (`WL_FROSTMISTY` 2); `WL_RADIUS` 3; optional `WL_RECOGNIZEDSPELL` 5 (White Imprison 1, Stasis 1, Release 2). Every branch's remaining ancestors/budget must be allocated.[12][13]
- **Gear goals:** V early `1619 / Survival_Rod2` 24; `2000 / Destruction_Rod` 80, Wizard upper/third/fourth **two-handed** staff; `22001 / Temporal_Int_Boots` and `22004 / Temporal_Dex_Boots` 99, third/fourth. G recommends choosing between Temporal boots, not equipping both.[4][11]
- **Progression priorities (editorial/U):** cheap elemental spells and quest gear → Wizard AoE → rebirth/Mystical Amplification → first elemental Warlock AoE → INT/DEX milestones → Temporal option if its content exists. Staff of Destruction prevents a shield; two-hand damage versus one-hand survival is an actual gear decision, not free defense.[11]

### M2 — Sorcerer offensive Psychic Wave / elemental AoE

- **Scope/source:** original iRO revision 61887, **2020-05-28** offensive-caster section, third-job `R175`; deliberately excludes the current 2025 Psychic Wave section's fourth-job talents and post-rebalance formula claims.[5]
- **Path:** Mage → Sage → rebirth → High Mage → Scholar (local `Professor`) → Sorcerer. **G stats:** STR 1–50; AGI 1–50; VIT 95+; INT 100–120; DEX 100–120; LUK 1–30.[5]
- **V core:** `SO_PSYCHIC_WAVE` 5 (`SA_DISPELL` 2); `SO_DIAMONDDUST` 5 (`SA_DELUGE` 3); `SO_EARTHGRAVE` 5 (`WZ_EARTHSPIKE` 5). Historical Varetyr Spear cap is not authoritative: local `SO_VARETYR_SPEAR` now has max 10.[12][13]
- **Gear goals:** G suggests Mental Stick as a Psychic Wave weapon. V `1654 / Mental_Stick` 102, Sage third/fourth; `1619 / Survival_Rod2` 24 for early stages; `22004 / Temporal_Dex_Boots` 99 third/fourth, only if later content is enabled. **Do not** transfer Wizard-only `2000 / Destruction_Rod` to Sorcerer.[5][11]
- **Progression priorities (editorial/U):** Mage bolt/quest route → Sage support or single-target leveling → rebirth for Scholar utilities → Psychic Wave and element coverage → SP/cast survivability before luxury enchants. No claim that 2020 damage/cast formulas equal this newer local DB or a 2018 server.

## Hunter

### R1 — Ranger Arrow Storm AoE leveling

- **Scope/source:** explicitly **OUTDATED** iRO third-job Arrow Storm milestone section, `R175`, not its separate 2025 build. It supports historical 125–175 priorities and Camouflage; old AoE/formula claims are not asserted as current.[6]
- **Path:** Archer → Hunter → rebirth → High Archer → Sniper → Ranger. **G 125–175 bands:** STR 1–33; AGI 1; VIT 90–120; INT 57–100; DEX 120; LUK 30–80. These summarize separate milestone columns, not an optimized new allocation.[6]
- **V core:** `RA_ARROWSTORM` 10 (`RA_AIMEDBOLT` 5, itself `HT_ANKLESNARE` 5); `RA_CAMOUFLAGE` 5 (`RA_RANGERMAIN` 1). Target skill levels are editorial within the checked local maxima, not a complete tree.[12][13]
- **Gear goals:** V `1746 / Elven_Bow` 100; White Wing pieces `15042 / White_Wing_Suits`, `2479 / White_Wing_Boots`, `2580 / White_Wing_Manteau`, `2890 / White_Wing_Brooch`, all 100, Hunter third/fourth. Higher weapon candidate `18110 / Big_CrossBow` 110. Set-combo efficacy requires `item_combos`/runtime validation, not item-name presence.[11]
- **Progression priorities (editorial/U):** Archer DEX/ranged safety → Hunter/Sniper quest/AoE options → rebirth → prerequisite trap chain → Arrow Storm/Camouflage → level-100 White Wing gear if Mora is enabled. Current 2025 guide recommends a different stat/leveling approach; do not merge the two eras.[6]

### R2 — Ranger auto-Warg / critical single-target

- **Scope/source:** same page's explicitly outdated **Auto Warg Strike, @CloudSeeker** section, third-job `R175`; supports ASPD/LUK equipment priorities and an MVP orientation rather than efficient mass leveling.[6]
- **Path:** Archer → Hunter → rebirth → High Archer → Sniper → Ranger. **G 125–175 bands:** STR 1–40; AGI 100; VIT 50–100; INT 10–50; DEX 100–120; LUK 60–120.[6]
- **V core:** `RA_WUGMASTERY` 1; `RA_TOOTHOFWUG` 10 (Warg Mastery 1); `RA_WUGSTRIKE` 5 (Tooth of Warg 1). Guide effect/proc formulas are U until matched to selected mechanics.[12][13]
- **Gear goals (editorial):** bow/ASPD/critical improvements while keeping survival. V `1746 / Elven_Bow` 100, Hunter or BardDancer third/fourth; `22002 / Temporal_Agi_Boots` 99 or `22005 / Temporal_Luk_Boots` 99, not both. Their local scripts require **120 base AGI/LUK** for their specific threshold bonus; this profile's AGI 100 does not satisfy the AGI threshold.[11]
- **Progression priorities (editorial/U):** ordinary Archer/Hunter leveling → rebirth → obtain Warg core → build attack speed and hit/critical reliability → test single-target uptime. Do not label the level-99 source column a completed Renewal endgame plan or assume a 193-ASPD target is achieved by stats alone.

## Support

### S1 — Maestro Magic Strings / Severe Rainstorm hybrid

- **Scope/source:** original iRO revision 61751, **2020-05-20**, third-job `R175` Severe Rainstorm/Support section. Supports hybrid party utility and survivability/SP priorities, not current 2025 fourth-job equipment.[7]
- **Path:** Archer → Bard → rebirth → High Archer → Minstrel (transcendent/iRO name) → Maestro (**third-job local key `Minstrel`**). **G stats:** STR 1; AGI 60–100; VIT 95+; INT 91+; DEX 100+; LUK 1–50+. The guide's total-INT performance thresholds are advice, not base-stat caps.[7][13][14]
- **V core:** `BA_POEMBRAGI` 10 (`BA_DISSONANCE` 3); `BA_MUSICALLESSON` 10; `WM_SEVERE_RAINSTORM` 5 (`BA_MUSICALSTRIKE` 5 on Minstrel tree); `MI_RUSH_WINDMILL` 5 (`WM_LULLABY_DEEPSLEEP` 1). Do not confuse trans/third class names across regional clients.[12][13]
- **Gear goals:** G suggests support instruments and a separate bow. V `1926 / Harp_Of_Nepenthes` 60, upper/third/fourth male BardDancer; `1930 / Green_Whistle` 102, third/fourth male BardDancer; `1746 / Elven_Bow` 100 two-handed. No shield while bow-equipped.[7][11]
- **Progression priorities (editorial/U):** Archer ranged leveling → Bard Strings → rebirth → instrument/bow swaps and SP sustain → Rainstorm prerequisites → utility upgrades. Historical “bow required” performance limitations must be matched to rebalance; newer local/guide weapon support may differ. No automatic spell-delay threshold inference from the old guide.

### S2 — Wanderer Gypsy's Kiss / party support

- **Scope/source:** iRO Party Support (PVM/WoE) third-job 99–175 section, `R175`, not the page's adjacent 2025 damage/talent builds. Supports SP/song uptime priorities and INT/VIT emphasis.[8]
- **Path:** Archer → Dancer → rebirth → High Archer → Gypsy → Wanderer. **G 125–175 bands:** AGI 25–80; VIT 100–122; INT 81–93; DEX 100; LUK 41–89. **STR source is malformed `0~10` to `0~16`: preserve as rejected source data**, not a legal zero-stat plan; no verified STR band supplied.[8]
- **V core:** `DC_SERVICEFORYOU` 10 (`DC_UGLYDANCE` 3); `DC_DANCINGLESSON` 10; `WA_SWING_DANCE` 5 (`WM_LULLABY_DEEPSLEEP` 1); `WM_FRIGG_SONG` 5 (`WM_LESSON` 2). Chorus requirements and consumables need separate validation.[12][13]
- **Gear goals (editorial):** SP/INT, HP/reductions and an actual performance weapon before offense. V `1950 / Rope` 3 or `1951 / Rope_` 3, female BardDancer whips; `2374 / Diabolus_Robe` 60 upper/third/fourth BardDancer; `2115 / Valkyrja's_Shield` 65 while using a one-hand whip.[11]
- **Progression priorities (editorial/U):** Archer solo/party quests → Dancer SP song → rebirth → survivable whip support → Swing Dance/Frigg uptime. **Gap:** clean sourced/legal STR allocation and stage budgets are unresolved; the 122 VIT target also requires an appropriate later stat cap. Do not clamp the guide's malformed values silently.

## Melee

### D1 — Guillotine Cross Rolling Cutter / Cross Ripper Slasher

- **Scope/source:** iRO Rolling Cutter/Cross Ripper Slasher section, `R-late`, mixed older backpack advice and newer stat alternatives. Supports AoE leveling focus, HIT needs and the katar route; exact episode not specified.[9]
- **Path:** Thief → Assassin → rebirth → High Thief → Assassin Cross → Guillotine Cross. **G bands/options:** STR 90–125; AGI 90–125; VIT 80–100 **or** 125; INT 1 **or** 120; DEX approximately 60 **or** 90–100 **or** 120; LUK approximately 60 **or** 72/90/108/126 **or** 120. These are incompatible equipment-dependent alternatives, not a finished allocation.[9]
- **V core:** `GC_ROLLINGCUTTER` 5 (`AS_SONICBLOW` 10); `GC_CROSSRIPPERSLASHER` 5 (Rolling Cutter 1); `ASC_EDP` 5 (`ASC_CDP` 1). Exact poison cost/sustainability and full ancestors need validation.[12][13]
- **Gear goals (editorial):** legal katar, HIT and sustain before expensive critical/threshold packages. V early `1250 / Jur` 18, two slots, or `1251 / Jur_` 18, three slots, Assassin family **two-handed** katars; `22002 / Temporal_Agi_Boots` 99 if 120-AGI route/content chosen. Cannot retain a shield with the katar.[11]
- **Progression priorities (editorial/U):** Thief damage/accuracy → Assassin katar/Sonic Blow → rebirth/EDP → Rolling Cutter core → SP/HP sustain → optional ranged finisher. G prioritizes Rolling Cutter for leveling; maxing costly stat/gear alternatives without a budget is not accepted.[9]

### D2 — Rune Knight Wind Cutter / Peuz starter

- **Scope/source:** iRO **Wind Cutter Build (2025)**, `R-late` rebalance; source explicitly extends leveling to 200+ and mixes newer weapons. This is not certified for an early 2018 Renewal configuration; fourth-only weapons/talents are excluded from the local starter candidates.[10]
- **Path:** Swordman → Knight → rebirth → High Swordman → Lord Knight → Rune Knight. **G bands/options:** STR 120–125; AGI 90–100; VIT 90–120; INT 1 **or** 12–18; DEX 100–110; LUK 30–60 **or** 100.[10]
- **V core:** `RK_WINDCUTTER` 5 (`RK_ENCHANTBLADE` 5); `RK_ENCHANTBLADE` prerequisite requires `RK_RUNEMASTERY` 2; proposed Rune Mastery 10 for the wider rune toolkit. Optional `RK_IGNITIONBREAK` 5 requires Sonic Wave 2 + Death Bound 5 + Wind Cutter 3; Death Bound itself requires `KN_AUTOCOUNTER` 1 + Enchant Blade 2.[12][13]
- **Gear goals:** G recommends Peuz set. V `15037 / Peuz_Plate`, `2476 / Peuz_Greave`, `2575 / Peuz_Manteau`, `2884 / Peuz_Seal`, all level 100, Knight third/fourth; starter two-hand sword `1188 / Veteran_Sword` 80, Swordman family. Peuz set bonuses and current weapon-dependent Wind Cutter behavior require additional mechanics validation.[10][11]
- **Progression priorities (editorial/U):** Swordman quests → Knight AoE → rebirth/Lord Knight → Enchant Blade prerequisites/Wind Cutter → farm Mora gear **only if quests are enabled** → rune material supply and upgrades. Do not assume current iRO weapon behavior, “F2P” availability, or 200+ performance on another episode/server.

## Acceptance gaps and research count

**12 researched archetypes, 2 per requested playstyle; 0 executable/fully validated builds.** T1 lacks a complete dedicated Devotion variant; H1/H2 retain a material Sacrament mismatch; S2's source STR values are rejected, not repaired. These are real gaps, not silently filled templates. All other stat bands remain guide advice with aggregate level budgets unverified.

Before any Renewal agent initialization: select and persist an explicit ruleset/episode/rebalance profile; re-research against that profile; expand all prerequisite ancestors and inherited trees; solve level-specific stat and job-point budgets; check level/class/gender/slot legality, set-combo scripts and gear acquisition; exercise skills/equipment in an isolated **Renewal** world. Item presence or URL-present tests are not build validity or live acceptance. Keep pre-Renewal research and initialization on their own path.

This single-page delivery intentionally leaves index/log unchanged per the task's exclusive file ownership, despite the general schema's log convention. No prices, market availability or gameplay success claims were invented. Retrieval backend extraction was unavailable; public HTTPS `curl` and the primary site's MediaWiki revision API supplied the actual guide contents. Historical revision URLs may be WAF-blocked in a browser even though the site's API returned their contents.

## Sources

[1] https://irowiki.org/w/index.php?title=Royal_Guard&oldid=61749
[2] https://irowiki.org/wiki/Sura
[3] https://irowiki.org/wiki/Arch_Bishop
[4] https://irowiki.org/wiki/Warlock
[5] https://irowiki.org/w/index.php?title=Sorcerer&oldid=61887
[6] https://irowiki.org/wiki/Ranger
[7] https://irowiki.org/w/index.php?title=Maestro&oldid=61751
[8] https://irowiki.org/wiki/Wanderer
[9] https://irowiki.org/wiki/Guillotine_Cross
[10] https://irowiki.org/wiki/Rune_Knight
[11] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/item_db_equip.yml
[12] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/skill_db.yml
[13] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/skill_tree.yml
[14] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/re/job_stats.yml
