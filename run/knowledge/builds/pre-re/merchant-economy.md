# Merchant — Merchant-Economy (discount/overcharge/vending trader) (pre-renewal)

Structured twin: `merchant-economy.json`. Axis: **merchant-economy**. Job bonus at job 40/50: STR+3/5, AGI+4/5, VIT+3/4, INT+4/6, DEX+3/5, LUK+1/2.

## Role
The economy specialist: every NPC purchase −24% (Discount 10), every sale +24% (Overcharge 10), 8,000-weight pushcart, then Vending 10 for player shops. Fights with a basic axe + Mammonite burst only when the math favors it.

## Stat progression
| Phase | BLv | Budget | Allocation | Spent | Left |
|---|---|---|---|---|---|
| job change | 40 | 305 | STR 40 / VIT 30 / DEX 20 / rest 1 | 268 | 37 |
| job 50 | 50 | 420 | STR 50 / VIT 40 / DEX 20 / rest 1 | 376 | 44 |

## Skill order (job 40 = 40 pts; server tree `db/pre-re/skill_tree.yml`)
| # | Skill (lv) | Pts | Prereq chain | Why |
|---|---|---|---|---|
| 1 | Enlarge Weight Limit 3 | 3 | — | Discount prereq (+600 weight) |
| 2 | Discount 10 | 10 | EWL 3 | −24% NPC prices: Knife 50→38z, Red Potion 10→7.6z |
| 3 | Overcharge 10 | 10 | Discount 3 | +24% sells: Sticky Mucus 35→43z |
| 4 | Enlarge Weight Limit 5 | 2 | — | Pushcart prereq (+1,000 weight) |
| 5 | Pushcart 10 | 10 | EWL 5 | 8,000-weight cart; Vending prereq at 3 |
| 6 | Mammonite 5 | 5 | — | 350% ATK for 500z+5SP burst |
Job 41–50 (10): Vending 10 (Pushcart 3 met) — player shops; Mammonite →10; Change Cart (quest). Server-side note: Item Appraisal has **no** tree prereq (wiki lists Pushcart 3 — the server `db/pre-re/skill_tree.yml` wins).

## Economy math (prices from iro-db; parenthetical = max merchant rate)
- Discount 10: 50z Knife → 38z; 500z Axe → 380z; every Red Potion cheaper.
- Overcharge 10: Jellopy 3z → 3.7z (floors to 3), Sticky Mucus 35 → 43z, Feather 10 → 12z, Clover 5 → 6z.
- The margin stack (buy −24%, sell +24%) makes NPC-flipping + loot-running strictly better than any other class's loot runs.

## Equipment (order, server prices)
1. Knife [3] 1201 — 50z (38z at Discount 10)
2. Axe [3] 1301 — 500z (ATK 38; merchant 1H axe ASPD −15)
3. Jacket 2303 — 200z
4. Sandals 2401 — 400z
5. Guard 2101 — 500z
6. Battle Axe [3] 1351 — 5,400z (ATK 80)

## Grinding (loot route)
| Phase | Map | Mob (id) | Lv/HP | EXP | Notes |
|---|---|---|---|---|---|
| all | prt_fild08 (established loop) | Poring 1002 | 1/60 | 27/20 | Jellopy 70% |
| | | Lunatic 1063 | 3/55 | 36/27 | Feather 10% |
| | | Rocker 1052 | 15/185 | 99/74 | Grasshopper's Leg 90% — full-cart sell runs |

## Do not waste points on
Item Appraisal (1 pt at most), Vending before holding surplus stock, Open Buying Store (renewal-era skill; exists server-side as ALL_BUYING_STORE needing Vending 1, useless solo), Crazy Uproar quest (STR+4/30s, 8 SP — fun, not core).

## Renewal differences
Discount/Overcharge/Pushcart/Vending numbers are era-stable. The wiki *Merchant* page's extras (Open Buying Store, Cart Decoration, offline vending) are later additions — present in this 2018 PACKETVER build but not part of the classic pre-re kit; treat as optional.

## Sources
- iRO wiki corpus: *Merchant*, *Discount*, *Overcharge*, *Pushcart*, *Vending*, *Enlarge Weight Limit*, *Mammonite*, *Merchant Job Change Guide*.
- iRO DB corpus: items 1201/1301/1351/2303/2401/2101/909/938/949/705 (buy/sell incl. merchant-rate parentheticals); monsters 1002/1063/1052.
- rAthena: `db/pre-re/skill_tree.yml` (MC_DISCOUNT needs MC_INCCARRY 3; MC_OVERCHARGE needs MC_DISCOUNT 3; MC_PUSHCART needs MC_INCCARRY 5; MC_VENDING needs MC_PUSHCART 3), `npc/pre-re/jobs/1-1/merchant.txt` (delivery quest).
- Project receipt: `run/reviews/knife-purchase-mechanics.json`.
