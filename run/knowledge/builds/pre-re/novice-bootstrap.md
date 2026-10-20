# Novice — shared 0-zeny bootstrap (pre-renewal)

Structured twin: `novice-bootstrap.json`. Axis: all (shared entry phase).
Server context: private rAthena, PACKETVER 20180704, db/pre-re. Established loop: kill on prt_fild08 → sell at Prontera (prt_in Weapon Dealer) → buy Knife [3] 1201 for 50z.

## Goal
Novice Base Lv ~10 / Job 10, Basic Skill 9, ~500z bank, Knife + a few Red Potions, then pick one of the six first classes. Every point and zeny earned — no handouts exist pre-renewal.

## Stat points (with arithmetic)
- You start with **48 stat points** and gain `floor(X/5)+3` per base level-up: **80 points by BLv 10**, 135 by 20 (iRO wiki *Stats* + *Total stat point requirement*).
- Raise cost from X→X+1 is `floor((X-1)/10)+2` (2 pts each 1→10, 3 each 11→20, …).
- Bootstrap allocation (melee flavor): STR 9 (16), DEX 9 (16), rest 1 → 32+ spent of 80. Caster flavor: INT 9 / DEX 9. Flee flavor: AGI 9 / DEX 9.
- **Points carry over to the first class — do not feel obliged to spend them.** Keep the pool for the real build.

## Skills
| Order | Skill | Lv | Why |
|---|---|---|---|
| 1 | Basic Skill | 9 | Hard gate for every job change (checked by all `npc/pre-re/jobs/1-1/*` scripts). 1 pt per job lv 1–9. |
| 2 | First Aid (quest) | 1 | +5 HP / 3 SP; free, marginal. |
| 3 | Play Dead (quest) | 1 | Emergency disengage. |
Job 10 grants 10 points; Basic Skill costs 9 → 1 spare point into the first class.

## Earning loop (0 zeny start)
| Mob (iro-db id) | Lv | HP | Base/Job EXP | Passive? | Loot that pays |
|---|---|---|---|---|---|
| Poring 1002 | 1 | 60 | 27/20 | yes (Looter) | Jellopy 70% (3z), Sticky Mucus 4% (35z), Apple 10% |
| Drops 1113 | 2 | 45 | 27/20 | yes | Jellopy 75%, Rod [4] 0.81% |
| Lunatic 1063 | 3 | 55 | 36/27 | yes | Clover 65% (5z), Feather 10% (10z) |
| Pupa 1008 | 4 | 66 | 36/27 | immobile | Chrysalis 55%, Sticky Mucus 6% |

- Sell Jellopy/Fluff/Clover/Chrysalis piles at Prontera tool/weapon NPCs; Sticky Mucus (35z) and Feathers (10z) are the real moneymakers at this stage.
- Buy **Knife [3] 1201 (50z)** at the prt_in Weapon Dealer. Only then a handful of Red Potions (iRO NPC price 10z; server `db/pre-re/item_db_usable.yml` Buy is 50z — verify the live tool dealer).
- Server `db/pre-re/mob_db.yml` lists Poring as Hp 50 / BaseExp 2 / JobExp 1 — the live rate multiplier is configured separately; the numbers above are iRO-db reference values for *relative* difficulty.

## Job change (all require Novice Job 10 + Basic Skill 9)
| Class | Where | Classic pre-re test (npc/pre-re/jobs/1-1/) |
|---|---|---|
| Swordman | Izlude guild (izlude_in) | registration + short test course |
| Mage | Geffen Tower | reagent mixing quiz (Jellopy/Fluff etc., small fee) |
| Archer | Payon village | ≥25 points of World Tree Trunks (S=5/A=3/B=2/C=1) from Willows |
| Acolyte | Prontera church | pilgrimage errand |
| Thief | Morocc pyramid | maze run, ≥25 mushroom points (3/1 pts) |
| Merchant | Alberta guild | delivery quest with a parcel |

## Do not waste
- Points on LUK (+0.3% crit/pt is nothing now), or on deep stat raises before the class pick.
- Zeny on anything but Knife + potions; keep ~450z for the class's first weapon step.

## Renewal differences
Novice-phase mechanics (stat costs, Basic Skill, job level 10 gate) are identical across eras. The academy-style instant changes, free novice gear and the Novice Falchion reward shown on the current-iRO wiki job guides are renewal-era services — this db/pre-re server runs the classic quests tabled above instead.

## Sources
- iRO wiki corpus (`run/knowledge/iro-wiki/`, via query_iro_wiki.py): pages *Stats*, *Total stat point requirement*, *Levels*, *Novice*, *Basic Skill*, *First Aid*, *Play Dead*, per-class *Job Change Guide*.
- iRO DB corpus (`run/knowledge/iro-db/`, via query_iro_db.py): monsters 1002/1113/1063/1008; items 1201/2302/501/909/938/705/949.
- rAthena: `db/pre-re/mob_db.yml`, `db/pre-re/item_db*.yml` (server prices), `npc/pre-re/jobs/1-1/*.txt` (classic job tests).
- Project receipts: `run/reviews/knife-purchase-mechanics.json`, `run/reviews/playing-mvp-npc-earned-equipment-route.json` (established prt_fild08 → prt_in → Knife 50z loop).
