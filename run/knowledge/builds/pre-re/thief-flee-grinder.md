# Thief — Grinder (flee-tank dagger sprint) (pre-renewal)

Structured twin: `thief-flee-grinder.json`. Axis: **grinder**.

## Role
Max kill-speed dagger thief: AGI/STR with Double Attack autos and Envenom burst; tanks by missing (+30 flee). Lowest gear requirement of the melee classes — best zeny/hour at equal investment.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | AGI 50 / DEX 24 / STR 20 / rest 1 | 303 | 2 |
| job 50 | 50 | 420 | AGI 60 / STR 30 / DEX 26 / rest 1 | 419 | 1 |

## Skill order (job 40 = 40 pts)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Double Attack 10 | 10 | — | the DPS (70% double, +10 HIT) |
| 2 | Improve Dodge 10 | 10 | — | +30 flee = miss-tank |
| 3 | Envenom 10 | 10 | — | +150 poison dmg/proc, 50% poison; 12 SP |
| 4 | Steal 5 | 5 | — | Hiding prereq + loot |
| 5 | Hiding 5 | 5 | Steal 5 | panic button |
Job 41–50 (10): Steal →10, Hiding →10, Detoxify 1.

## Equipment
1. Knife [3] 1201 — 50z
2. Cutter [3] 1204 — 1,250z (ATK 30)
3. Jacket 2303 — 200z
4. Sandals 2401 — 400z
5. Main Gauche [3] 1207 — 2,400z (ATK 43)

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 12–35 | prt_fild08 | Drops 1113 | 2/45 | 27/20 | passive |
| | | Rocker 1052 | 15/185 | 99/74 | |
| | | Spore 1014 | 18/280 | 117/87 | Water 1; Mushroom Spore 90% sells |

## Do not waste points on
Steal past 5 before job 50 (DPS first), Hiding in early levels, INT.

## Renewal differences
Same era splits as the stealth variant (Improve Dodge ×3 flee branch, renewal ASPD); daggers' renewal-only +0.5%/STR weapon layer would slightly boost this build there.

## Sources
- iRO wiki corpus: *Double Attack*, *Envenom*, *Improve Dodge*, *Steal*.
- iRO DB corpus: monsters 1113/1052/1014; items 1201/1204/1207.
- rAthena: `status.cpp:4517` (TF_MISS), `db/pre-re/skill_tree.yml`.
