# Pre-Renewal Build Digests (first jobs + Novice bootstrap)

Mechanically-accurate build digests for the private rAthena server (PACKETVER 20180704, **PRE-RENEWAL**, `db/pre-re/`). Each build has a markdown digest (`*.md`) and a structured JSON sidecar (`*.json`, same stem) for machine consumption (agents' build context / CLEF decision context).

## Coverage matrix (class × playstyle axis)

| File | Class | Playstyle | Axis |
|---|---|---|---|
| novice-bootstrap | Novice | shared 0-zeny bootstrap | all |
| swordman-tank | Swordman | VIT sword-and-board | tank |
| swordman-grinder | Swordman | STR/AGI bash | grinder |
| mage-grinder | Mage | bolt nuker | grinder |
| mage-aoe-control | Mage | fire-wall kiter | evasive/lethal |
| archer-ds-kiter | Archer | Double Strafe kiter | evasive/lethal |
| archer-range-grinder | Archer | ICC range farmer + Arrow Crafting | grinder |
| acolyte-support | Acolyte | full buffer | support/party |
| acolyte-battle | Acolyte | blessed mace brawler | grinder |
| thief-stealth-lethal | Thief | steal-and-vanish | evasive/lethal |
| thief-flee-grinder | Thief | flee-tank dagger sprint | grinder |
| merchant-economy | Merchant | discount/overcharge/vending trader | merchant-economy |
| merchant-battle | Merchant | Mammonite brawler | grinder |

13 digests = Novice bootstrap + 6 first jobs × 2 playstyles.

## Shared mechanical constants (verified)
- **Stat raise cost** X→X+1 = `floor((X−1)/10)+2`; cumulative: →10:18, →20:47, →30:86, →40:135, →50:194, →60:263, →99:628 (wiki *Stats* / *Total stat point requirement*).
- **Stat points**: 48 at BLv 1, +`floor(X/5)+3` per level-up → 80 @BLv10, 210 @30, **305 @40**, 360 @45, **420 @50**, 1273 @99. Points carry across job change.
- **HIT** = 175+BLv+DEX+LUK/3; **FLEE** = 100+BLv+AGI+LUK/5; monster hit-req = 200+lvl+agi, flee-req = 170+lvl+dex (the iro-db `hit`/`flee` columns); dodge caps at 95%.
- **Pre-re status ATK** (rathena `status.cpp status_base_atk`): melee `STR+(STR/10)²+DEX/5+LUK/5`; ranged `DEX+(DEX/10)²+STR/5+LUK/5`. **MATK** min `INT+(INT/7)²`, max `INT+(INT/5)²`.
- **Pre-re Heal** = `floor((BLv+INT)/8) × (4+8×lv)` (rathena `skill.cpp:70`). Blessing +STR/DEX/INT = lv; Increase AGI +AGI = 2+lv; Improve Concentration +2+lv AGI/DEX; Angelus soft DEF +5%/lv; Improve Dodge +3 flee/lv (first-class Thief); Crazy Uproar STR+4.
- **ASPD**: AGI/DEX-driven, cap 190 (non-3rd); per-class weapon modifiers in each class digest (e.g. Swordman 1H sword −7, Thief dagger −8, Mage rod −5, Merchant axe −15).
- **Skill points**: 1 per job level; Novice job 10 = 10 pts (Basic Skill 9 + 1 spare); first class job 40 = 40, job 50 = 50.
- **Prices**: server truth is `rathena/db/pre-re/item_db*.yml` (`Buy:` field); iro-db `buying_price` shows the iRO NPC price with the max-merchant-rate value in parentheses (e.g. Knife "50 Z (38 Z)"). Notable divergence: Red Potion (iRO 10z vs server Buy 50z) — verify live.

## How the digests were grounded
1. Local corpora first: `run/knowledge/iro-wiki/` (FTS via `query_iro_wiki.py`) for mechanics/class/skill pages; `run/knowledge/iro-db/` (via `query_iro_db.py --id N --section monsters|items`) for mob HP/exp/elements/drops and item prices.
2. Server truth: `rathena/db/pre-re/skill_tree.yml` (authoritative prereqs — where it differs from the wiki, the server tree wins and the digest says so), `db/pre-re/skill_db.yml` (SP/cast), `db/pre-re/item_db*.yml` (prices), `db/pre-re/mob_db.yml` (base exp/HP before live rates), `npc/pre-re/jobs/1-1/*.txt` (classic job-change tests), `src/map/status.cpp` / `skill.cpp` (pre-re formula branches).
3. Established economy loop: prt_fild08 → Prontera sell → Knife 1201 @50z (`run/reviews/knife-purchase-mechanics.json`, `run/reviews/playing-mvp-npc-earned-equipment-route.json`).

## Known gaps / caveats
- Map spawn tables are not in the corpora; digests cite mob stats from iro-db and mark non-prt_fild08 maps as "classic iRO spawns — confirm live on the server".
- Live server exp/zeny rate multipliers are unknown here; iro-db exp values are reference points for relative grind pacing only.
- The iRO wiki corpus is current-iRO (renewal-flavored) — every era-divergent formula used here was verified against the `#ifndef RENEWAL` branches in rAthena source and flagged in each digest's renewal-differences paragraph.
