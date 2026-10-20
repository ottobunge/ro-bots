# Swordman — Tank (VIT sword-and-board) (pre-renewal)

Structured twin: `swordman-tank.json`. Axis: **tank**. Job bonus at job 40/50: STR+4/7, VIT+3/4, DEX+3/3, AGI+1/2, LUK+1/2 (iRO wiki *Swordman* job-bonus table).

## Role
1H sword + Guard. STR for damage, VIT for HP pool (+1% MaxHP/pt), stun/poison resist and potion efficiency (+2%/pt). Holds mobs for Magnum Break AoE clears or party-mate grinding.

## Stat progression (budget = 48 + Σ floor(X/5)+3)
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| early | 30 | 210 | STR 30 / VIT 20 / DEX 10 / rest 1 | 151 | 59 |
| job change | 40 | 305 | STR 40 / VIT 30 / DEX 20 / rest 1 | 268 | 37 |
| job 50 | 50 | 420 | STR 50 / VIT 40 / DEX 20 / INT 9 / rest 1 | 392 | 28 |

Costs used: stat→40 = 135, →50 = 194 pts (iRO wiki cumulative table). Job bonuses stack on top (VIT 40 + 4 = 44 total at job 50).
Melee status ATK (pre-re, `status.cpp status_base_atk`): STR + (STR/10)² + DEX/5 + LUK/5 → STR 50/DEX 20 = 100 status ATK before weapon.

## Skill order (job 40 = 40 pts; server tree: `db/pre-re/skill_tree.yml`)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Bash 5 | 5 | — | 130–190% ATK, +acc; SP 8 |
| 2 | Provoke 5 | 5 | — | −DEF 10–30% on target (amplifies your hits); Endure prereq; SP lv+3 |
| 3 | Endure 1 | 1 | Provoke 5 | no-flinch walk-off + MDEF while active |
| 4 | Bash 10 | 5 | — | 400% finisher (SP 15) |
| 5 | Magnum Break 10 | 10 | Bash 5 | 5×5 fire AoE 120–300%, knockback 2, +20% fire 10s; 30 SP + ~15 HP |
| 6 | Increase HP Recovery 4 | 4 | — | +20 HP/10s tick, +40% potion effect |
| 7 | Sword Mastery 10 | 10 | — | +4 ATK/lv on 1H swords & daggers (fill to job 45) |
Quest (free, job 30+): Fatal Blow (Bash 6), Berserk (Provoke 5), HP Recovery While Moving.

## Equipment (acquisition order, server NPC prices from db/pre-re item_db / iro-db)
1. Knife [3] 1201 — 50z (starter; ATK 17)
2. Sword [3] 1101 — 100z (ATK 25; mastery applies)
3. Jacket 2303 — 200z (DEF 2)
4. Sandals 2401 — 400z (DEF 1)
5. Guard 2101 — 500z (shield, DEF 3; −5 ASPD)
6. Falchion [3] 1104 — 1,500z (ATK 39)
7. Hood 2501 — 1,000z (garment DEF 2)
8. Blade [3] 1107 — 2,900z (ATK 53; last cheap 1H NPC step)
Note: db.irowiki.org displays renewal-scaled DEF (Cotton Shirt 10 vs server 1); server item_db values are authoritative for gameplay.

## Grinding (HP/EXP from iro-db; classic spawn maps — confirm live spawns on the server)
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| 10–25 | prt_fild08 (established loop) | Pupa 1008 | 4/66 | 36/27 | immobile, safe |
| | | Poring 1002 | 1/60 | 27/20 | passive |
| | | Fabre 1007 | 6/72 | 54/41 | passive, Earth 1 |
| 25–50 | prontera S fields / culverts | Rocker 1052 | 15/185 | 99/74 | passive |
| | | Zombie 1015 | 17/234 | 117/87 | aggressive, Undead 1 — Magnum Break (fire) shines |
| 40–50 | payon fields | Wolf 1013 | 45/1219 | 342/386 | passive, assists; needs the VIT pool |

## Do not waste points on
Two-Handed Sword Mastery (shield build), Endure beyond 1, INT beyond ~9 (Magnum SP only), AGI, LUK.

## Renewal differences (one paragraph)
Skill numbers (Bash/Provoke/Magnum/Endure tables above) are era-stable, but the stat layer changes in renewal: STR additionally grants +0.5% weapon ATK per point, MaxHP uses a different job-base formula, Angelus-type soft-DEF effects were reworked, and the wiki corpus's per-point stat descriptions (its *Stats* page) reflect current iRO — the formulas cited here are the `#ifndef RENEWAL` branches in `rathena/src/map/status.cpp` / `skill.cpp` that this server actually runs.

## Sources
- iRO wiki corpus: *Swordman* (builds, job bonuses, ASPD weapon table: 1H sword −7), *Bash*, *Provoke*, *Magnum Break*, *Endure*, *Sword Mastery*, *Increase HP Recovery*, *Swordman Skill Quest*, *Swordman Job Change Guide*.
- iRO DB corpus: monsters 1008/1002/1007/1052/1015/1013; items 1101/1104/1107/2101/2303/2401/2501.
- rAthena: `db/pre-re/skill_tree.yml` (SM_MAGNUM needs SM_BASH 5; SM_ENDURE needs SM_PROVOKE 5), `npc/pre-re/jobs/1-1/swordman.txt`.
