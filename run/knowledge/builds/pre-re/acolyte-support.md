# Acolyte — Support/Party (full buffer) (pre-renewal)

Structured twin: `acolyte-support.json`. Axis: **support/party**. Job bonus at job 40/50: STR+1/3, AGI+2/2, VIT+2/3, INT+2/3, DEX+2/3, LUK+3/4.

## Role
Heal/Blessing/AGI-Up bot. Makes any melee partner potion-free and roughly doubles their output. Pre-re Heal: `floor((BLv+INT)/8) × (4+8×lv)` (rathena skill.cpp:70 — the corpus page shows the renewal `/5×30` variant).

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | INT 40 / DEX 40 / VIT 9 / rest 1 | 286 | 19 |
| job 50 | 50 | 420 | INT 50 / DEX 40 / VIT 20 / rest 1 | 376 | 44 |

Heal throughput: BLv 45 / INT 30+2 (bonus) → Heal 7 restores (75/8)×60 ≈ 540 HP; BLv 50 / INT 50+3 Heal 10 → (103/8)×84 ≈ 1,080 HP.

## Skill order (job 40 = 40 pts; server tree: Blessing needs Divine Protection **5**)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Heal 3 | 3 | — | unlocks Increase AGI; SP 10+3lv |
| 2 | Divine Protection 5 | 5 | — | Blessing prereq (+reduce undead/demon dmg) |
| 3 | Blessing 5 | 5 | Divine Protection 5 | +STR/DEX/INT = lv (rAthena SC_BLESSING); SP 24+4lv |
| 4 | Increase AGI 10 | 10 | Heal 3 | +AGI (2+lv) + walk speed; SP 15+3lv, 15 HP |
| 5 | Heal 10 | 5 | — | max throughput |
| 6 | Blessing 10 | 5 | — | +10/10/10 party-wide |
| 7 | Ruwach 1 / Aqua Benedicta 1 | 2 | — | reveal + craft Holy Water |
| 8 | Teleport 2 | 2 | Ruwach 1 | escape + Warp Portal prereq |
| 9 | Angelus 1 →5 | 1 (→5) | Divine Protection 3 | party soft DEF +5%/lv (pre-re) |
Job 41–50 (10): Warp Portal 4 → Pneuma 1 (anti-ranged pocket), Cure 1 (Heal 2 done), Angelus →5. Holy Light quest skill (no tree prereq server-side) is a free pickup.

## Equipment
1. Club [3] 1501 — 120z (ATK 23; acolyte mace ASPD −5)
2. Jacket 2303 — 200z
3. Sandals 2401 — 400z
4. Guard 2101 — 500z
5. Mace [3] 1504 — 1,600z (ATK 37)
6. Hood 2501 — 1,000z

## Grinding
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| all (party) | any field | Poring 1002 | 1/60 | 27/20 | carry spot |
| 20+ | culverts/graveyards | Zombie 1015 | 17/234 | 117/87 | aggressive Undead 1: **Heal-bomb** deals Holy dmg = half the heal amount |

## Do not waste points on
Decrease AGI (needs IncAgi 1; PvP tool), Signum Crucis chain (Demon Bane 3; undead-only screen debuff), Holy Light before job 50.

## Renewal differences
Heal is the big split: pre-re `/8 × (4+8lv)` vs renewal `(BLv+INT)/5×30×lv/10` (the formula the corpus page prints). Pre-re Angelus raises soft DEF by 5%/lv; renewal reworked it toward %HP. Blessing/Increase AGI magnitudes are era-stable (+lv and +2+lv).

## Sources
- iRO wiki corpus: *Acolyte*, *Heal*, *Blessing*, *Increase AGI*, *Angelus*, *Divine Protection*, *Ruwach*, *Aqua Benedicta*, *Teleport*, *Warp Portal*, *Pneuma*, *Acolyte Job Change Guide*.
- rAthena: `src/map/skill.cpp:70` (pre-re Heal), `status.cpp` (SC_BLESSING val2=val1; SC_INCREASEAGI val2=2+val1; SC_ANGELUS val2=5×val1), `db/pre-re/skill_tree.yml` (AL_BLESSING needs AL_DP 5; AL_INCAGI needs AL_HEAL 3), `npc/pre-re/jobs/1-1/acolyte.txt`.
- iRO DB corpus: monsters 1002/1015; items 1501/1504.
