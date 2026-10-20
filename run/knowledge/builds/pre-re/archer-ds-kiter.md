# Archer — Evasive/Lethal (Double Strafe kiter) (pre-renewal)

Structured twin: `archer-ds-kiter.json`. Axis: **evasive/lethal**. Job bonus at job 40/50: INT+6/9, DEX+5/7, STR+3/3, AGI+2/4, VIT+1/1, LUK+1/2.

## Role
Never-melee: bow range 5 base + Vulture's Eye +1/lv (→15 at lv10) while mobs melee only under 4 cells. DEX is the ranged status-ATK stat (pre-re: `DEX+(DEX/10)²+STR/5+LUK/5`) and HIT.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | DEX 50 / AGI 30 / rest 1 | 280 | 25 |
| job 50 | 50 | 420 | DEX 60 / AGI 40 / rest 1 | 398 | 22 |

DEX 50 + 5 job bonus + 10 Owl's Eye = 65 effective → ranged status ATK ≈ 65 + 42 = 107 + arrow ATK 25: one-shots Poring (60 HP) with normal attacks.

## Skill order (job 40 = 40 pts; server tree: AC_DOUBLE has **no** prereq)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Double Strafe 5 | 5 | — | 2 bolts ×140% (corpus per-bolt table 100%+10%/lv); 12 SP; 1 arrow |
| 2 | Owl's Eye 3 | 3 | — | Vulture prereq (+DEX later) |
| 3 | Vulture's Eye 10 | 10 | Owl's Eye 3 | +1 range & +1 HIT per lv with bows |
| 4 | Double Strafe 10 | 5 | — | 2×190% finisher |
| 5 | Improve Concentration 5 | 5 | Vulture's Eye 1 | pre-re flat +AGI/DEX (2+lv → +7); reveals Hiding |
| 6 | Arrow Shower 5 | 5 | Double Strafe 5 | AoE pushback-2 for mob control |
| 7 | Owl's Eye 10 (fill) | 7 | — | +10 DEX total |
Job 41–50 (10): Improve Concentration →10 (+12 AGI/DEX flat), Owl's Eye is capped.

## Equipment (order)
1. Knife [3] 1201 — 50z (novice filler; sell after change)
2. Bow [3] 1701 — 1,000z (ATK 15; DEX scaling does the work)
3. Arrow 1750 — 1z each (ATK 25, weight 0.1; buy hundreds)
4. Jacket 2303 — 200z
5. Sandals 2401 — 400z
6. Composite Bow [3] 1704 — 2,500z (ATK 29)
7. Hood 2501 — 1,000z

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 10–30 | prt_fild08 (established loop, outranges everything) | Poring 1002 | 1/60 | 27/20 | one-shot normals at DEX 50 |
| | | Lunatic 1063 | 3/55 | 36/27 | |
| | | Rocker 1052 | 15/185 | 99/74 | flee-req 202: AGI30+BLv40 → 170 flee ≈ 65% dodge while kiting |
| 30–50 | payon fields (classic spawns) | Willow 1010 | 8/91 | 45/36 | Trunks → job quest + arrow crafting |
| | | Wolf 1013 | 45/1219 | 342/386 | hit-req 269 → BLv50+DEX60+ICC = 285+ → 100% hits |

## Do not waste points on
Arrow Repel (quest, self-knockback niche), INT, VIT early (kiting is the defense), Arrow Shower past 5.

## Renewal differences
Pre-re ranged status ATK is `DEX+(DEX/10)²+STR/5`; renewal adds a +0.5%/DEX weapon-ATK layer. Improve Concentration is flat +2+lv AGI/DEX pre-re (rAthena SC_CONCENTRATE) vs the renewal % the corpus table shows. Bow range and DS numbers are era-stable.

## Sources
- iRO wiki corpus: *Archer* (job bonuses, ASPD: bow −10), *Double Strafe*, *Owl's Eye*, *Vulture's Eye*, *Improve Concentration*, *Arrow Shower*, *Archer Job Change Guide*, *Stats* (Attack Range: bows 5 cells).
- iRO DB corpus: monsters 1002/1063/1052/1010/1013; items 1701/1750/1704.
- rAthena: `db/pre-re/skill_tree.yml` (AC_DOUBLE no prereq; AC_SHOWER needs AC_DOUBLE 5; AC_CONCENTRATION needs AC_VULTURE 1), `npc/pre-re/jobs/1-1/archer.txt` (≥25 trunk points, S5/A3/B2/C1).
