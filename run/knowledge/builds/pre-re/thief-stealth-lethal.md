# Thief — Evasive/Lethal (steal-and-vanish) (pre-renewal)

Structured twin: `thief-stealth-lethal.json`. Axis: **evasive/lethal**. Job bonus at job 40/50: STR+3/4, AGI+3/4, VIT+1/2, INT+1/1, DEX+2/4, LUK+2/3.

## Role
Highest flee in the first-class tier (Improve Dodge +3 flee/lv pre-re per rAthena `status.cpp:4517`, + AGI), Steal-farms every kill once, Hiding to drop aggro. Daggers with Double Attack (70% double-hit +10 HIT at lv10) + Envenom bursts.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| early | 30 | 210 | AGI 30 / DEX 20 / STR 9 / rest 1 | 149 | 61 |
| job change | 40 | 305 | AGI 50 / DEX 24 / STR 20 / rest 1 | 303 | 2 |
| job 50 | 50 | 420 | AGI 60 / STR 30 / DEX 26 / rest 1 | 419 | 1 |

Flee check (iRO wiki *Stats*): 100 + BLv + AGI + LUK/5 → BLv 40, AGI 50+3 (bonus), ID 10 (+30) = 223 flee vs Rocker flee-req 202 → 95% (cap) dodge; vs Male Thief Bug (flee-req 216) still capped.

## Skill order (job 40 = 40 pts; server tree: Hiding needs Steal 5; Double Attack has **no** prereq)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Double Attack 3 | 3 | — | early double-hit on daggers |
| 2 | Steal 5 | 5 | — | 34% base (+DEX×0.1%); Hiding prereq; 1 steal/mob, 10 SP |
| 3 | Double Attack 10 | 7 | — | 70% double + 10 HIT |
| 4 | Improve Dodge 10 | 10 | — | +30 flee |
| 5 | Steal 10 | 5 | — | 64% base; loot farming |
| 6 | Hiding 5 | 5 | Steal 5 | 30 s/lv undetectable |
| 7 | Envenom 5 | 5 | — | +75 poison dmg, 30% poison; 12 SP |
Job 41–50 (10): Hiding →10, Envenom →10 (+150 dmg / 50% poison), Detoxify 1 (Envenom 3 done). Quest skills: Back Slide, Sand Attack, Find Stone, Stone Fling.

## Equipment (order)
1. Knife [3] 1201 — 50z (starter dagger)
2. Jacket 2303 — 200z
3. Sandals 2401 — 400z
4. Cutter [3] 1204 — 1,250z (ATK 30)
5. Main Gauche [3] 1207 — 2,400z (ATK 43; daggers 100%/75%/50% vs S/M/L)
6. Hood 2501 — 1,000z

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 12–30 | prt_fild08 (established loop) | Poring 1002 | 1/60 | 27/20 | Steal Jellopy first, then kill |
| | | Fabre 1007 | 6/72 | 54/41 | |
| | | Rocker 1052 | 15/185 | 99/74 | 95% dodge at the stats above |
| 30–50 | prontera culverts (classic spawns) | Thief Bug 1050 | 10/89 | 72/54 | |
| | | Male Thief Bug 1054 | 30/595 | 198/224 | aggressive; hit-req 243 vs BLv40+DEX24 ≈ 239 → ~96%; Hiding to shed aggro |

## Do not waste points on
Detoxify before Envenom 10, quest skills before job 50, VIT/INT (flee is the defense; Envenom is 12 SP).

## Renewal differences
Steal/Double Attack/Hiding numbers are era-stable. The corpus *Improve Dodge* page shows current-iRO text; pre-re rAthena grants ×3 flee per level for first-class Thief (×4 at 2nd class in the same branch). Renewal ASPD math shifts swings/second slightly.

## Sources
- iRO wiki corpus: *Thief*, *Double Attack*, *Improve Dodge*, *Steal*, *Hiding*, *Envenom*, *Thief Job Change Guide*, *Stats* (FLEE formula).
- iRO DB corpus: monsters 1002/1007/1052/1050/1054; items 1201/1204/1207.
- rAthena: `src/map/status.cpp:4517` (TF_MISS flee), `db/pre-re/skill_tree.yml` (TF_HIDING needs TF_STEAL 5; TF_DOUBLE no prereq), `npc/pre-re/jobs/1-1/thief.txt` (≥25 mushroom points).
