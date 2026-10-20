# Swordman — Grinder (STR/AGI bash) (pre-renewal)

Structured twin: `swordman-grinder.json`. Axis: **grinder**. Job bonus at job 40/50: STR+4/7, AGI+1/2, VIT+3/4, DEX+3/3.

## Role
Solo kill-speed: STR powers Bash/auto-attack, AGI adds ASPD + flee, Magnum Break pops grouped passive mobs. Cheapest early DPS; transitions cleanly to Knight.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| early | 30 | 210 | STR 30 / AGI 20 / DEX 10 / rest 1 | 151 | 59 |
| job change | 40 | 305 | STR 40 / AGI 40 / DEX 15 / rest 1 | 302 | 3 |
| job 50 | 50 | 420 | STR 50 / AGI 50 / DEX 14 / rest 1 | 417 | 3 |

Status ATK at STR 50/DEX 14 (pre-re formula): 50 + 25 + 2 = 77; STR 50 brings (STR/10)² to 25.

## Skill order (job 40 = 40 pts)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Bash 5 | 5 | — | core nuke |
| 2 | Sword Mastery 5 | 5 | — | +20 ATK on sword/dagger |
| 3 | Bash 10 | 5 | — | 400% |
| 4 | Increase HP Recovery 5 | 5 | — | +50% potion efficiency, sustain |
| 5 | Provoke 5 | 5 | — | −30% target DEF at 5 → boosts own burst too |
| 6 | Magnum Break 10 | 10 | Bash 5 | AoE clear |
| 7 | Sword Mastery 10 (fill) | 5 | — | +40 ATK total |
Job 41–50 (10 more): Two-Handed Sword Mastery 1–10 if you switch to Katana [3] (2H, ATK 60, ASPD −14, needs Sword Mastery 1); or Endure 1 (Provoke 5 met) + Bash/utility fills.

## Equipment (order, server prices)
1. Knife [3] 1201 — 50z (starter)
2. Sword [3] 1101 — 100z (ATK 25)
3. Jacket 2303 — 200z
4. Sandals 2401 — 400z
5. Falchion [3] 1104 — 1,500z (ATK 39; 1H+shield variant)
6. Katana [3] 1116 — 2,000z (ATK 60 2H; slower, no shield)
7. Blade [3] 1107 — 2,900z (ATK 53 1H)

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 10–30 | prt_fild08 (established loop) | Fabre 1007 | 6/72 | 54/41 | passive; Fluff 65% |
| | | Pupa 1008 | 4/66 | 36/27 | immobile |
| | | Rocker 1052 | 15/185 | 99/74 | passive; Grasshopper's Leg 90% (sell 30z-class) |
| 30–50 | moc/payon fields (classic spawns) | Hornet 1004 | 11/90 | 81/60 | aggressive, fast; hit-req 235 — keep DEX ≥ 15–20 |
| | | Wolf 1013 | 45/1219 | 342/386 | passive, assists; hit-req 269 → BLv50+DEX20+LUK/3 ≈ 246 → ~70% hits, add gear/Provoke |

## Do not waste points on
Endure/Increase HP Recovery beyond the listed stops, INT, LUK; Two-Handed Sword Mastery while still on 1H weapons.

## Renewal differences
Skill tables are era-stable; renewal STR adds +0.5% weapon ATK per point and the ASPD formula changed (same 190 cap), shifting attacks/second slightly at equal AGI. Job bonuses and costs identical.

## Sources
- iRO wiki corpus: *Swordman* ("Bash & Auto-Attack" build, job bonuses, ASPD tables), *Bash*, *Magnum Break*, *Sword Mastery*, *Two-Handed Sword Mastery*.
- iRO DB corpus: monsters 1007/1008/1052/1004/1013; items 1116/1104/1107.
- rAthena: `db/pre-re/skill_tree.yml`, `db/pre-re/item_db_equip.yml` (server prices).
