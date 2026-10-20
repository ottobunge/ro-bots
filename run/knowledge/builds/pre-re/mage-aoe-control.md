# Mage — Evasive/Lethal (fire-wall kiter) (pre-renewal)

Structured twin: `mage-aoe-control.json`. Axis: **evasive/lethal** (kill at range, walls keep contact impossible).

## Role
Field-control caster: Fire Wall channels mobs into a kill-corridor with knockback, Safety Wall pockets a cell against melee. Never touched; higher skill ceiling than the bolt build, best in dense passive fields.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | INT 40 / DEX 30 / AGI 10 / VIT 10 / rest 1 | 263 | 42 |
| job 50 | 50 | 420 | INT 50 / DEX 40 / VIT 10 / AGI 10 / rest 1 | 371 | 49 |

Keep pouring the leftovers into INT (damage + MaxSP) then DEX (cast speed).

## Skill order (job 40 = 40 pts; server tree)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Fire Bolt 4 | 4 | — | Fire Ball prereq |
| 2 | Fire Ball 5 | 5 | Fire Bolt 4 | splash fire; Fire Wall prereq |
| 3 | Sight 1 | 1 | — | Fire Wall prereq |
| 4 | Fire Wall 10 | 10 | Fire Ball 5 + Sight 1 | 50% fire MATK per contact + 2-cell knockback; 40 SP |
| 5 | Napalm Beat 7 | 7 | — | Safety Wall prereq + cheap AoE |
| 6 | Soul Strike 5 | 5 | Napalm Beat 4 | Safety Wall prereq; +vs Undead |
| 7 | Safety Wall 3 | 3 | Napalm 7 + Soul Strike 5 | blocks melee at one cell; 1 Blue Gemstone, SP 30+ |
| 8 | Increase SP Recovery 5 | 5 | — | sustain the wall loop |
Job 41–50 (10): Safety Wall →5–10, Soul Strike →7–10, Increase SP Recovery →8–10.

## Equipment
1. Rod [3] 1601 — 50z (MATK 30)
2. Jacket 2303 — 200z
3. Sandals 2401 — 400z
4. Red Potions — 10z/50z (see sources; mistake insurance)
5. Blue Gemstone 718 — Safety Wall catalyst, 1/cast

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 20–50 | prt_fild08 & dense passive fields | Fabre 1007 | 6/72 | 54/41 | wall-channeled groups |
| | | Thief Bug 1050 | 10/89 | 72/54 | Fire 1 → Fire Ball/Fire Wall 150% |
| | | Thief Bug Egg 1051 | 21/354 | 126/143 | immobile, assists |

Wall math: Fire Wall lv 10 hits each crossing mob repeatedly (50% MATK per contact); with INT 40 (65–104 MATK) a Thief Bug (89 HP, Fire 1) takes ~100–156 fire per touch → 2–3 touches.

## Do not waste points on
Thunderstorm before Wizard (SP pool + long pre-re cast), Frost Nova chain (level-hungry: Cold Bolt 5 + Frost Diver), DEX beyond cast comfort before INT is done.

## Renewal differences
Same era split as the bolt build (variable-only cast, no equip-MATK layer), plus renewal rebalanced Safety Wall durability and Fire Wall hit counts; the corpus pages show the current numbers, the server runs `db/pre-re/skill_db.yml`.

## Sources
- iRO wiki corpus: *Fire Wall*, *Fire Ball*, *Safety Wall*, *Soul Strike*, *Napalm Beat*, *Sight*.
- iRO DB corpus: monsters 1007/1050/1051; item 718.
- rAthena: `db/pre-re/skill_tree.yml` (MG_FIREWALL needs MG_FIREBALL 5 + MG_SIGHT 1; MG_SAFETYWALL needs MG_NAPALMBEAT 7 + MG_SOULSTRIKE 5).
