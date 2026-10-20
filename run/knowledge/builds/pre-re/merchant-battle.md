# Merchant — Grinder (Mammonite brawler) (pre-renewal)

Structured twin: `merchant-battle.json`. Axis: **grinder** (fight-first; tank-adjacent with VIT).

## Role
Fight-first merchant: Mammonite 10 is the hardest single hit in the first-class tier (600% ATK for 1,000z + 5 SP), axe in hand, VIT-backed. Trade skills are second priority and finish at job 45–50.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | STR 40 / AGI 30 / DEX 20 / rest 1 | 268 | 37 |
| job 50 | 50 | 420 | STR 50 / AGI 40 / DEX 20 / rest 1 | 376 | 44 |

Status ATK at STR 50 (pre-re): 50 + 25 + 4 = 79 + axe ATK; Mammonite 10 multiplies the lot by 600%.

## Skill order (job 40 = 40 pts)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Mammonite 10 | 10 | — | 150–600% ATK, 100–1,000z/cast (corpus table); 5 SP |
| 2 | Enlarge Weight Limit 3 →5 | 5 | — | cart prereq + hauling |
| 3 | Discount 3 →5 | 3 | EWL 3 | cut resupply costs (−11..13%) |
| 4 | Overcharge 3 →5 | 3 | Discount 3 | loot +11..13% |
| 5 | Pushcart 10 | 10 | EWL 5 | fewer town trips |
| 6 | Enlarge Weight Limit 10 (fill) | 5 | — | +2,000 weight |
| 7 | Discount →10 / Overcharge →10 | 4 | — | complete rates at job 45+ |
Quest skills: Crazy Uproar (STR+4, 30 s, 8 SP — rAthena SC_LOUD), Change Cart.

## Equipment
1. Knife [3] 1201 — 50z
2. Axe [3] 1301 — 500z (ATK 38)
3. Jacket 2303 — 200z
4. Sandals 2401 — 400z
5. Battle Axe [3] 1351 — 5,400z (ATK 80)
6. Guard 2101 — 500z (shield variant when not two-handing)

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 15–50 | prt_fild08 → Rocker fields | Rocker 1052 | 15/185 | 99/74 | Mammonite 5 (350%) one-shots |
| 40+ | payon fields (classic spawns) | Wolf 1013 | 45/1219 | 342/386 | Mammonite 10 bursts; 1,000z/cast vs ~342 base exp + loot — count the zeny |

## Do not waste points on
Mammonite on trash below its zeny cost, Vending/Change Cart before Pushcart 3+, Item Appraisal.

## Renewal differences
Mammonite's zeny/damage table is era-stable; renewal's +0.5%/STR weapon-ATK layer would boost axe builds there, and the wiki page's buying-store extras are optional server-side additions (see the economy build digest).

## Sources
- iRO wiki corpus: *Mammonite*, *Enlarge Weight Limit*, *Discount*, *Overcharge*, *Pushcart*.
- iRO DB corpus: items 1301/1351; monsters 1052/1013.
- rAthena: `status.cpp` SC_LOUD (STR+4), `db/pre-re/skill_tree.yml`.
