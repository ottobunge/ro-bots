# Archer — Grinder (range farmer, arrow-craft self-supply) (pre-renewal)

Structured twin: `archer-range-grinder.json`. Axis: **grinder**.

## Role
Sustained-farm variant: max range/HIT/ICC and normal-attack kite for zero-SP farming; the Arrow Crafting quest skill turns Trunks/Jellopy/etc. into free ammo, making the whole loop zeny-positive.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | DEX 40 / AGI 40 / rest 1 | 273 | 32 |
| job 50 | 50 | 420 | DEX 50 / AGI 50 / rest 1 | 391 | 29 |

Split DEX/AGI for attack speed while kiting; leftovers alternate DEX/AGI.

## Skill order (job 40 = 40 pts)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Owl's Eye 10 | 10 | — | +10 DEX |
| 2 | Vulture's Eye 10 | 10 | Owl's Eye 3 | range 15, +10 HIT |
| 3 | Improve Concentration 10 | 10 | Vulture's Eye 1 | flat +12 AGI/DEX (pre-re); 60–240s buff |
| 4 | Double Strafe 5 | 5 | — | finisher only |
| 5 | Arrow Shower 5 | 5 | Double Strafe 5 | loot-mob pull |
Quest skill: Arrow Crafting (AC_MAKINGARROW — no tree prereq server-side; turns e.g. Trunk into arrows).

## Equipment
1. Bow [3] 1701 — 1,000z
2. Arrow 1750 — 1z each
3. Jacket 2303 — 200z
4. Sandals 2401 — 400z
5. Composite Bow [3] 1704 — 2,500z

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 12–40 | prontera maze / payon (classic spawns) | Willow 1010 | 8/91 | 45/36 | Trunk 30z-sell + materials |
| | | Thief Bug 1050 | 10/89 | 72/54 | |
| | | Spore 1014 | 18/280 | 117/87 | Mushroom Spore 90% (sell / arrow-craft fodder) |

## Do not waste points on
Arrow Shower beyond 5, Double Strafe before ICC is maxed (uptime build), LUK.

## Renewal differences
Arrow Crafting recipes and Trunk drops are era-stable; the flat-vs-% Improve Concentration divergence (see kiter digest) matters most in this build since the flat +12 is a bigger low-level swing than the renewal percentage.

## Sources
- iRO wiki corpus: *Arrow Crafting*, *Archer Skill Quest*, *Improve Concentration*, *Vulture's Eye*.
- iRO DB corpus: monsters 1010/1050/1014; items 1701/1750.
- rAthena: `db/pre-re/skill_tree.yml` (AC_MAKINGARROW), `npc/pre-re/jobs/1-1/archer.txt`.
