# Mage — Grinder (bolt nuker) (pre-renewal)

Structured twin: `mage-grinder.json`. Axis: **grinder**. Job bonus at job 40/50: INT+5/8, DEX+3/3, AGI+3/4, LUK+1/3.

## Role
Ranged-9 artillery. Pre-re MATK is pure INT (`status.cpp`): min `INT+(INT/7)²`, max `INT+(INT/5)²` — INT 40 → 65–104 MATK per bolt; each bolt of Fire Bolt lv N deals 100% MATK with N bolts per cast. DEX cuts cast time (INT helps at half rate); AGI is only animation/survival padding.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| early | 30 | 210 | INT 30 / DEX 20 / AGI 9 / rest 1 | 149 | 61 |
| job change | 40 | 305 | INT 40 / DEX 30 / AGI 20 / rest 1 | 268 | 37 |
| job 50 | 50 | 420 | INT 50 / DEX 40 / AGI 20 / rest 1 | 376 | 44 |

INT 40/50 with job bonuses = 45/58 effective → min 69/107, max 111/150 MATK at job 50.

## Skill order (job 40 = 40 pts; server tree `db/pre-re/skill_tree.yml`)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Fire Bolt 10 | 10 | — | SP 10+2lv, N×100% fire MATK; range 9 |
| 2 | Lightning Bolt 10 | 10 | — | anti-Water: Poring/Drops are Water 1 → 150% |
| 3 | Increase SP Recovery 10 | 10 | — | +3 SP/10s tick per lv, funds bolts |
| 4 | Sight 1 | 1 | — | reveal; Fire Wall prereq later |
| 5 | Napalm Beat 9 | 9 | — | cheap Ghost AoE poke, SP 9–18 |
Job 41–50 (10): Stone Curse 1 (petrify-lock, 1 Red Gemstone, SP 26−lv), Cold Bolt 5 → Frost Diver 1 (freeze, Water), Napalm Beat 10, Cold Bolt fill.

## Element leverage on the home field (iro-db per-mob elemental tables)
- Poring 1002 / Drops 1113: **Water 1 / Fire 1** → Lightning Bolt (Poring) and Cold Bolt (Drops) at 150%.
- Pupa 1008: Earth 1, immobile → Fire Bolt 150%, zero-risk kills from level 1.

## Equipment (order)
1. Rod [3] 1601 — 50z (ATK 15/**MATK 30**; rod ASPD penalty is irrelevant to casters)
2. Jacket 2303 — 200z
3. Sandals 2401 — 400z
4. Hood 2501 — 1,000z
5. Red Potion stock — iRO NPC 10z / server Buy 50z (glass cannon: carry them)

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 1–40 (safe, element-advantaged) | prt_fild08 | Pupa 1008 | 4/66 | 36/27 | Fire Bolt 150%, immobile |
| | | Poring 1002 | 1/60 | 27/20 | Lightning 150% |
| | | Drops 1113 | 2/45 | 27/20 | Cold Bolt 150% (after job-40 plan) |
| 40+ | geffen/mjolnir fields (classic spawns) | Male Thief Bug 1054 | 30/595 | 198/224 | Shadow 1, aggressive |
| | | Poison Spore 1077 | 26/456 | 198/224 | Water 1 → Lightning 150% |

One-shot math: Fire Bolt lv 5 = 5 bolts × (65–104) = 325–520 fire MATK vs Pupa 66 HP (×1.5) — dies to one cast from INT 40.

## Do not waste points on
Safety Wall chain early (12 pts; the nuker isn't getting hit at range 9), Fire Ball/Fire Wall (that's the AoE-control build), Energy Coat quest before job 40.

## Renewal differences (one paragraph)
The corpus skill pages list renewal fixed+variable cast splits; pre-re has a single variable cast reduced by DEX (+INT/2). Pre-re MATK (min/max INT formulas above) has no renewal equip-MATK layer, and server cast values live in `db/pre-re/skill_db.yml` (e.g. AL_INCAGI CastTime 1000 ms). Element multipliers and bolt counts are era-stable.

## Sources
- iRO wiki corpus: *Mage*, *Fire Bolt*, *Lightning Bolt*, *Cold Bolt*, *Napalm Beat*, *Stone Curse*, *Frost Diver*, *Increase SP Recovery*, *Mage Job Change Guide*, *Stats*.
- iRO DB corpus: monsters 1002/1113/1008/1054/1077 (elemental_damage tables); item 1601.
- rAthena: `status.cpp status_base_matk_min/max` (pre-re MATK), `db/pre-re/skill_tree.yml` (MG_FROSTDIVER needs MG_COLDBOLT 5).
