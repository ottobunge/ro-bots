---
title: Classic Paladin legality and progression evidence
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, testing, ops]
---

# Verdict and boundary

**The 57-point Crusader diagnostic is a declaring-class accounting error for the reborn final build, not proof of illegality.** Its closure needs 57 inherited Crusader points and 10 Paladin points: 67 of the Paladin job-70 pool's 69 points. It would be illegal to require the 57-point closure while still a nontrans Crusader (49-point cap). Native `pc_skillup` subtracts from one `status.skill_point`, not a separate declaring-class wallet (`src/map/pc.cpp:9129–9164`); job caps are `db/pre-re/job_exp.yml:565–603,737,841,870,988`.[5][6][7]

This is independent **public pinned-source candidate evidence**, not approved executable progression, native gameplay, damage simulation, private-import equivalence, or whole-class coverage. Related acceptance remains in [[goals-ledger]] and [[adr-009-character-builds-item-cognition]]. No existing source, tests, templates, root flakes, clients, shared ledger, index or logs were edited.

Machine-readable full closures, per-point acquisition sequences, equipment rows, drop/shop evidence and SHA-256s: `run/reviews/classic-paladin-build-evidence.json`. Reproduce with `nix develop --offline -c uv run --offline --no-sync python /home/otto/.hermes/cache/scratch/paladin-evidence/finalize.py`; the owned report must not already exist (intentional new-file guard).

The public source is revision `e985006171d2eb320ee512a653f4c83aea3d81b6`, `/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source`; an actual `nix hash path` returned `sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`. Only pre-re data and native code were used. All selected skill levels fit the native maximum of 13; source inheritance uses each parent's own Tree, ordered parent precedence, own overrides, exclusion of inherited `Exclude`, zero max removal and zero prerequisite removal (`pc.cpp:13422–13701`).[5][6][20]

# Read web research, not URL-only provenance

Live HTML was fetched and read on 2026-10-05 for iRO Wiki Classic Paladin, Martyr's Reckoning, Rapid Smiting and Sacrifice. Full HTML/text captures and an isolated citation ledger are in `/home/otto/.hermes/cache/scratch/paladin-evidence/`; direct Python retrieval had a CA-certificate error, while dev-shell curl fetched the actual pages successfully. No archive, credential or paywall bypass was used.

Classic Paladin's Battle MR/RS section describes a high-VIT shield/Martyr hybrid, with Sacrifice and Defending Aura optional. Its stat ranges are alternatives, not a promise their maxima fit together. Its support sections describe protecting caster allies; these inform the two candidate playstyles below, not their mechanical proof.[1][4]

These are live reads of historically scoped Classic documentation, not proof of a currently running iRO ruleset or a specific episode match. The pinned pre-re source includes Morocc gear/spawns, so earlier-episode servers may exclude that acquisition route.[1][9][18]

Naming matters: iRO **Sacrifice** is `CR_DEVOTION`; **Martyr's Reckoning** is `PA_SACRIFICE`; **Rapid Smiting/Shield Chain** is `PA_SHIELDCHAIN`. Do not accidentally substitute the offensive skill for party protection. No Royal Guard/Renewal tree was merged.[2][3][5]

# Stage-aware allocations

Both lives start with Basic Skill `NV_BASIC 9` at Novice job10. Spend the following complete 49-point first-job allocation before changing at job50: Sword Mastery10, Increase HP Recovery10, Bash10, Magnum Break5, Provoke9, Endure5. Endure requires Provoke5 and Magnum Break requires Bash5; the report includes a verified prerequisite-first point sequence.[5][7]

**Provisional nontrans leveling route:** Crusader job50 allocation: Faith10, Guard5, Smite3, Shield Boomerang5, Shield Reflect5, Holy Cross6, Grand Cross4, Sacrifice5, Peco Peco Ride1, Cavalier Mastery5 =49. This is a candidate route, not proven efficient solo leveling. It deliberately omits Heal, Martyr and Rapid Smiting. The first-job points are already spent independently; Riding's Endure1 requirement is already met.[5][7]

**Rebirth resets the old allocation.** Crusader must reach base99/job50, spend remaining skills, satisfy Valkyrie's inventory/zeny/pet/cart conditions and the rebirth quest; `valkyrie.txt:148–155` changes to High Novice and calls `resetlvl(1)`. Native `pc.cpp:9243–9273` clears skill points, returns base/job to1, resets stats and assigns 100 initial stat points. Old Crusader points are not carried into Paladin.[6][12]

Then relearn Novice9 and the same first-job49 as High Swordsman. Source permits second change at job40+, but this candidate deliberately waits for job50; `Paladin.txt:36–63` also requires `ADVJOB=Paladin`, Upper1 and no unspent skill points. No fixed base70 can replace the pre-re base99 rebirth requirement.[7][13][14]

## Final original goals retained — no skill-goal deletion needed

| Allocated pool | Full allocation | Paid / cap |
|---|---|---|
| First life Novice | Basic9 | 9/9 |
| First life Swordsman | Sword10, Recovery10, Bash10, Magnum5, Provoke9, Endure5 | 49/49 |
| First life Crusader | Nontrans route above | 49/49 |
| Reborn High Novice | Basic9, learned anew | 9/9 |
| Reborn High Swordsman | Same first-job allocation, learned anew | 49/49 |
| Paladin shared inherited/trans pool | Faith10, Guard5, Smite3, Boomerang5, Reflect5, Holy Cross6, Grand Cross4, Devotion5, Cure1, Divine Protection3, Demon Bane5, Heal5, Martyr5, Rapid Smiting5 | 67/69 |

The final Paladin allocation is complete at **Paladin job68**; at job70 it leaves two discretionary points unspent. The goals-only first-job prerequisite closure is Provoke5 + Endure5 =10, but the candidate spends all49 to satisfy actual job-change gating. Minimum declared BaseLevel/JobLevel on these tree entries is zero; job68 is calculated acquisition, not a declared tree level. Progression is indexed by `(life, class, base level, job level)`, not the template's ambiguous base milestones45/70/99.[5][6][7]

**Party Devotion variant:** same final allocation, remove Martyr5 and add Defending Aura5. All other entries unchanged: 67/69, job68. This prioritizes maintaining Devotion5 and Heal5 with ranged defense; it is a source-supported design candidate, not a measured survivability claim.[1][4][5]

**Solo shield/Martyr variant:** starting from original final allocation, remove Cure1, Divine Protection3, Demon Bane5, Heal5; reduce Devotion5 to3; raise Guard5 to10; add Defender5, Riding1, Cavalier5. Retain Faith10, Smite3, Boomerang5, Reflect5, Holy Cross6, Grand Cross4, Martyr5 and Rapid Smiting5: 67/69, job68. Devotion3 remains required for Martyr. Neither variant claims every optional guide skill fits simultaneously.[1][2][5]

Quest skills are not paid fillers: native counting excludes quest skills with default `quest_skill_learn:no` (`pc.cpp:2524–2535`). High Swordsman NPC grants Moving HP Recovery, Fatal Blow and Auto Berserk; Shrink remains quest-dependent and is not in these paid closures. No skill reset item or quest completion was performed.[6][14][17]

# Class identifiers and remaining adapter gap

Native IDs parsed from `mmo.hpp:887–943`: Novice0, Swordman1, Crusader14, Novice_High4001, Swordman_High4002, Paladin4015.[16]
These are legal source transitions when their quests and requirements are met; Paladin is the upper Crusader branch, not a third job.[12][13][19]

Current adapter `mechanics_yaml.py:585–586` aliases only `Swordsman` to `Swordman`. Literal `High Novice` and `High Swordsman` do **not** resolve there; candidate explicit mappings would be `Novice_High` and `Swordman_High`. They are reported as unresolved adapter literals, not quietly repaired or patched. The source class path is valid; the literal template is still not executable as-is.

# Nonlinear stats

Treat omitted AGI/LUK as base1. At base99 the source curve provides1273 normal points; rebirth starts with100 instead of48, giving1325. Pre-re cost from value `low` to `low+1` is `1 + (low+9)//10` (`pc.cpp:8802–8828`), and the normal/upper base cap is99.[6][8][17]

STR60/VIT90/INT20/DEX40 costs975 (263+530+47+135), leaving350 reborn points, or298 normal. This is legal, not a complete spending prescription. A bounded alternative STR60/VIT99/INT30/DEX60/AGI1/LUK1 costs1240, leaving85. STR80/VIT99/INT30/DEX70 already costs1487 even at AGI1: illegal against1325. Raising one axis does not license independently maximizing the rest.[6][8][17]

# Equipment identity and acquisition

Six of seven template display names are ambiguous and must fail closed; only Cross Shield is unique. The table lists **all** exact matches, not silently chosen replacements. Slots are card slots. Gender defaults Both and omitted Classes defaults All, including upper; job masks still apply. Native item-mask loading is `itemdb.cpp:330–442`, and native equip checks are `pc.cpp:1755–1825,1900–1965`.[9][15][6]

| Literal | Exact ID/AegisName (card slots) | Minimum base / location |
|---|---|---|
| Blade | 1107 Blade(3), 1108 Blade_(4), 1109 Blade__(0) | 2 / Right_Hand, 1hSword |
| Cross Shield | 2130 Cross_Shield(1) | 80 / Left_Hand; Crusader branch only |
| Helm | 2228 Helm(0), 2229 Helm_(1) | 0 / Head_Top |
| Full Plate | 2316 Plate_Armor(0), 2317 Plate_Armor_(1) | 40 / Armor |
| Manteau | 2505 Manteau(0), 2506 Manteau_(1) | 0 / Garment |
| Boots | 2405 Boots(0), 2406 Boots_(1) | 0 / Shoes |
| Rosary | 2608 Rosary(0), 2626 Rosary_(1), 2694 Rosary_C(0) | 20,90,1 respectively / one accessory position |

All candidates allow the Paladin job branch and upper class. Cross Shield is not equipable by High Swordsman, and none of the final armor/accessory landmarks except Blade are Novice-compatible. Blade is one-handed, so it does not conflict with Cross Shield. Source omissions mean no maximum equip level here. Rosary_C has explicit nontrade restrictions and is not treated as a normal market item.[9][15][6]

Source-backed acquisition **options**, conditional on explicitly choosing the identity:
- Blade1107: Izlude weapon dealer `shops.txt:140`, Alberta weapon dealer:53, or Prontera:255.[11]
- Helm2228, Plate_Armor2316, Manteau2505 and Boots2405: Izlude armor dealer:141 or Aldebaran:59.[11]
- Rosary2608: Prontera church Nun:251. Rosary_2626 instead needs base90 and has Mimic1191 drop Rate1; Rosary_C2694 acquisition remains unverified.[9][10][11]
- Cross_Shield2130: Incarnation of Morocc1919 drop Rate15 in pre-re mob DB; source spawns include `moc_fild21` (`npc/pre-re/mobs/fields/morocc.txt:314`). This is late-game acquisition, not a starting grant. Map-access quests, combat feasibility and actual world import availability remain unverified.[10][18]
- Slotted alternatives have separate drop evidence: Blade_ from female Thief Bug1053 Rate15; Helm_ from Bloody Knight1268 Rate45; Plate_Armor_ from Doppelganger1046 Rate250; Manteau_ from Wraith1192 Rate2; Boots_ from Argiope1099 Rate5. The report retains all matching drop rows.[10]

Drop `Rate` is retained as source data, not promised live probability or time-to-acquire; server drop multipliers, luck, limits, spawns and quest accessibility can change effective availability. NPC `-1` prices delegate to the database; Buy values are not market evidence. No invented price tier, item grant, farm result, character creation, SQL, server launch or script execution occurred.[10][11]

Raw Cross Shield/Rosary script text is captured but not evaluated. Base attack/defense and restrictions are known; full script, refine, card, combo, battle-context HP/damage and performance effects remain unverified. The remaining frontier is explicit class alias/identity integration, progression representation, private import validation and separately authorized gameplay—not a Crusader57 budget rejection.[9]

## Sources

[1] https://irowiki.org/classic/Paladin — Paladin
[2] https://irowiki.org/classic/Martyr%27s_Reckoning — Martyr%27s_Reckoning
[3] https://irowiki.org/classic/Rapid_Smiting — Rapid_Smiting
[4] https://irowiki.org/classic/Sacrifice — Sacrifice
[5] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/skill_tree.yml — db/pre-re/skill_tree.yml
[6] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/pc.cpp — src/map/pc.cpp
[7] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/job_exp.yml — db/pre-re/job_exp.yml
[8] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/statpoint.yml — db/pre-re/statpoint.yml
[9] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/item_db_equip.yml — db/pre-re/item_db_equip.yml
[10] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/db/pre-re/mob_db.yml — db/pre-re/mob_db.yml
[11] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/merchants/shops.txt — npc/merchants/shops.txt
[12] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/jobs/valkyrie.txt — npc/jobs/valkyrie.txt
[13] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/jobs/2-2a/Paladin.txt — npc/jobs/2-2a/Paladin.txt
[14] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/pre-re/jobs/1-1/swordman.txt — npc/pre-re/jobs/1-1/swordman.txt
[15] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/itemdb.cpp — src/map/itemdb.cpp
[16] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/src/common/mmo.hpp — src/common/mmo.hpp
[17] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/conf/battle/player.conf — conf/battle/player.conf
[18] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/pre-re/mobs/fields/morocc.txt — npc/pre-re/mobs/fields/morocc.txt
[19] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/npc/jobs/2-2/crusader.txt — npc/jobs/2-2/crusader.txt
[20] https://github.com/rathena/rathena/blob/e985006171d2eb320ee512a653f4c83aea3d81b6/src/map/skill.hpp — src/map/skill.hpp
