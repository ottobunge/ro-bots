# Acolyte — Grinder (blessed mace brawler) (pre-renewal)

Structured twin: `acolyte-battle.json`. Axis: **grinder**.

## Role
Self-buffered melee: Blessing 10 (+10 STR/DEX/INT on yourself), AGI-Up (+12 AGI = ASPD + flee), mace swings with Demon Bane vs undead/demon. Free self-healing closes the loop without potion costs.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | STR 40 / DEX 30 / INT 20 / rest 1 | 268 | 37 |
| job 50 | 50 | 420 | STR 50 / DEX 30 / INT 30 / rest 1 | 366 | 54 |

Leftovers: STR →45+ first, then INT (SP pool for Heal spam). Status ATK at STR 50: 50+25+DEX/5 ≈ 81.

## Skill order (job 40 = 40 pts)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Heal 3 | 3 | — | IncAgi unlock |
| 2 | Divine Protection 5 | 5 | — | Blessing prereq |
| 3 | Blessing 5 →10 | 10 | DP 5 | self +10 STR/DEX/INT at 10 |
| 4 | Increase AGI 10 | 10 | Heal 3 | self +12 AGI |
| 5 | Heal 8 | 5 | — | sustain |
| 6 | Demon Bane 5 | 5 | Divine Protection 3 | +15 ATK vs Demon/Undead races (+3/lv) |
| 7 | Ruwach 1 / Aqua Benedicta 1 | 2 | — | holy poke / water |
Job 41–50 (10): Demon Bane →10 (+30 undead ATK), Heal →10, Teleport 2, Cure 1.

## Equipment
1. Club [3] 1501 — 120z (ATK 23)
2. Sandals 2401 — 400z
3. Guard 2101 — 500z
4. Mace [3] 1504 — 1,600z (ATK 37)
5. Jacket 2303 — 200z
6. Smasher [2] 1507 — 9,000z (ATK 54, weapon lv 2, base-req 14) — late first-class goal

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 12–30 (safe) | prt_fild08 | Rocker 1052 | 15/185 | 99/74 | passive |
| 30–50 | prontera culverts (classic spawns) | Thief Bug 1050 | 10/89 | 72/54 | |
| | | Male Thief Bug 1054 | 30/595 | 198/224 | aggressive; hit-req 243 vs BLv40+DEX30 ≈ 245 → 100% |
| | | Zombie 1015 | 17/234 | 117/87 | Undead 1: Demon Bane + optional Heal-bomb |

## Do not waste points on
Angelus (no party; % soft-DEF is small), Warp Portal chain (utility not DPS), Decrease AGI.

## Renewal differences
Blessing is flat +lv STR/DEX/INT pre-re (rAthena SC_BLESSING); renewal's Heal rework and the renewal-only +0.5%/STR weapon-ATK layer are the material changes. Demon Bane values are era-stable.

## Sources
- iRO wiki corpus: *Demon Bane*, *Divine Protection*, *Blessing*, *Increase AGI*, *Heal*.
- iRO DB corpus: monsters 1050/1054/1015/1052; items 1501/1504/1507.
- rAthena: `status.cpp` SC_BLESSING/SC_INCREASEAGI derivations, `db/pre-re/skill_tree.yml`.
