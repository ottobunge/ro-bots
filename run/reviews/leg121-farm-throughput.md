# Farm combat throughput: leg-121 offline diagnosis

Source base: `ae6e66ef`. Window: **2026-11-23 19:00:00–20:30:00 UTC**, half-open, 29 personas. Read-only reconstruction from `.work/runtime/population-live/traces/` in the main checkout and receipt `run/plain_host_receipts/population-receipt-121-1795447364.json`; no live probes or database operations.

## Dominant loss and fix

**Decision-blocked combat cadence dominates.** Successful next-action choices are already 90.1% grind; goal reviews are 87.2% grind/farm. Completed synchronous decides consume **125,971.525 agent-seconds** (80.44% of the 29 × 5,400 = 156,600 scheduled agent-second budget), including **108,292.081 seconds on chat events** (69.15% of that budget). This is time spent awaiting decisions, including capped failures, not evidence that agents chose chat as their goal. Calls still in flight at the window end are omitted; this is a lower bound. The script runs after event delivery, so slow calls delay approaches and finishing hits. The 18 positive own hits total 427 damage (mean 23.72, median 24, range 19–27). The pinned Poring has 50 HP (the brief uses ~60); either needs about three such hits; a 427-HP Pupa needs roughly 18. Only three own Pupa hits (74 damage) landed, with no kill. One same-target follow-up gap was 16.389 seconds; the normal same-target median is 2.004 seconds.

The implementation continues only an already-authored farm/grind target on the existing keepalive daemon, every two seconds, for at most 30 wall-clock seconds per authorization. Fresh native state, received walk completion, shared melee intercept, survival, standing, NPC, merchant and pickup gates still apply. Pump work never renews the lease or selects a replacement target. New goals/actions, target disappearance, map/epoch changes and expiry revoke it. This addresses combat cadence without changing decision prompts or forcing social goals into grind. Field discovery, travel and plant/species policy remain future levers if the next leg still lacks targets.

## Quantified loss table

| Step | Observed | Attribution |
|---|---:|---|
| Decide choices | 6050 successful / 8,963 completed | 5451 grind; 349 chat; 164 travel; 73 party choices; 13 loot; 2,913 errors |
| Goal reviews | 686 | 157 grind + 441 farm; 88 social; zero town/wander |
| Decision wait → script opportunity | 125,971.525 s blocked | **Dominant: 80.44% of scheduled agent wall time**; chat-event waits account for 108,292.081 s |
| Authored → swing | 34 → 20 (58.8%) | 12 pending_walk, 1 target_not_visible, 1 disengage_active; all 14 named. No cooldown/rest/dead/survival gate in this window |
| Out-of-range / approach failure among those 14 | 0 separately established | No historical range tap existed. Pending_walk refusals precede the visibility/range checks, so cannot prove those attempts were also in range. Approach MoveTo actions are upstream of the 34-attack denominator |
| Swing → own positive damage | 20 → 18 (90%) | Two sends without an own positive hit in the trace; wire send is not server acceptance |
| Damage → kill credit | 18 hits / 427 damage → 5 credits | Normal weapon-scale damage; limited follow-ups and split/co-attacked targets. Receipt: 5 exp-backed credits. Verdict DB readback: 6 mob drops and 6 pickups (distinct authorities) |
| Weapon status | seed Knife 1201 for all 29 | Existing NOVICE_WANTED_WEAPONS=(1201,1202,1204) equip path retained. Historical traces lack explicit worn-ack snapshots; 19–27 damage supports weapon-scale hits, not a proven per-agent worn receipt |

The receipt aggregates the entire runner session (15:22:44–20:45:09 UTC), not just the requested 90 minutes. Its **34/20/18/427/5** combat totals match the window reconstruction. Do not sum repeated bounded `samples[*].attack_gates` tails. No original exact approach-intent tap existed, so a unique approach→attack conversion rate cannot honestly be reconstructed. Sampled script_step rows (10-second throttle): FarmScript 1,105 MoveTo / 9 Attack, GrindScript 151 MoveTo / 4 Attack; these are sampled observations, not counts of unique combat approaches. The full move stream includes travel/patrol: 2,680 pending sends and 2,453 escalated_target_dead refusals (609 g00m01, 1,844 s01), which cannot be labeled as combat losses without a target-bound tap.

## Per-agent decisions and attack loss

| Persona | Grind next | Chat | Travel | Party | Loot | Errors | Goal grind/farm/social | Authored/swings | Refusals |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| pop_0003_g00m00 | 126 | 0 | 56 | 0 | 0 | 103 | 1/32/0 | 0/0 | — |
| pop_0003_g00m01 | 221 | 15 | 0 | 0 | 0 | 111 | 1/9/0 | 0/0 | — |
| pop_0003_g00m02 | 242 | 7 | 0 | 0 | 0 | 102 | 2/11/0 | 0/0 | — |
| pop_0003_g01m00 | 238 | 0 | 0 | 0 | 0 | 109 | 0/17/0 | 0/0 | — |
| pop_0003_g01m01 | 251 | 2 | 0 | 0 | 0 | 95 | 1/11/0 | 0/0 | — |
| pop_0003_g01m02 | 204 | 2 | 0 | 0 | 0 | 95 | 0/28/0 | 0/0 | — |
| pop_0003_s00 | 168 | 69 | 0 | 9 | 0 | 100 | 0/14/0 | 0/0 | — |
| pop_0069_g00m00 | 251 | 0 | 0 | 0 | 0 | 99 | 1/18/0 | 3/2 | pending_walk=1 |
| pop_0069_g00m01 | 108 | 7 | 0 | 1 | 1 | 64 | 3/49/0 | 5/3 | pending_walk=2 |
| pop_0069_g00m02 | 225 | 13 | 0 | 1 | 2 | 109 | 0/17/0 | 0/0 | — |
| pop_0069_g00m03 | 122 | 21 | 0 | 0 | 2 | 56 | 0/66/0 | 7/4 | pending_walk=3 |
| pop_0069_g01m00 | 226 | 0 | 0 | 1 | 0 | 113 | 0/17/0 | 1/0 | pending_walk=1 |
| pop_0069_g01m01 | 202 | 0 | 0 | 0 | 0 | 114 | 22/0/0 | 3/2 | pending_walk=1 |
| pop_0069_g01m02 | 234 | 1 | 0 | 0 | 2 | 109 | 0/20/0 | 0/0 | — |
| pop_0069_g02m00 | 111 | 0 | 104 | 0 | 0 | 119 | 1/23/0 | 4/3 | pending_walk=1 |
| pop_0069_g02m01 | 35 | 178 | 0 | 2 | 2 | 98 | 0/0/34 | 0/0 | — |
| pop_0069_g02m02 | 227 | 0 | 0 | 0 | 0 | 113 | 27/0/0 | 0/0 | — |
| pop_0069_g03m00 | 18 | 5 | 4 | 59 | 0 | 48 | 1/5/54 | 2/2 | — |
| pop_0069_g03m01 | 225 | 0 | 0 | 0 | 2 | 112 | 15/0/0 | 4/1 | pending_walk=2, target_not_visible=1 |
| pop_0069_g03m02 | 207 | 0 | 0 | 0 | 2 | 118 | 19/0/0 | 0/0 | — |
| pop_0069_g03m03 | 215 | 5 | 0 | 0 | 0 | 112 | 2/13/0 | 3/2 | pending_walk=1 |
| pop_0069_g04m00 | 225 | 0 | 0 | 0 | 0 | 115 | 0/13/0 | 0/0 | — |
| pop_0069_g04m01 | 210 | 18 | 0 | 0 | 0 | 112 | 0/11/0 | 0/0 | — |
| pop_0069_g04m02 | 211 | 0 | 0 | 0 | 0 | 110 | 26/0/0 | 2/1 | disengage_active=1 |
| pop_0069_g04m03 | 214 | 6 | 0 | 0 | 0 | 114 | 2/4/0 | 0/0 | — |
| pop_0069_s00 | 235 | 0 | 0 | 0 | 0 | 104 | 10/0/0 | 0/0 | — |
| pop_0069_s01 | 64 | 0 | 0 | 0 | 0 | 31 | 1/63/0 | 0/0 | — |
| pop_0069_s02 | 221 | 0 | 0 | 0 | 0 | 108 | 15/0/0 | 0/0 | — |
| pop_0069_s03 | 215 | 0 | 0 | 0 | 0 | 120 | 7/0/0 | 0/0 | — |

## Next-leg taps and reproducibility

- `decide_response.tap=decide_share_<choice>` with the current goal; existing answers retain change_goal and response duration/error.
- `farm_target_authored` binds a lease to target/epoch/map. `farm_approach` records the target cell, fresh intercept, ordinary runtime move outcome and monotonic time.
- `farm_pump_attack_authored` is counted by swing_funnel alongside host action_executed Attack; it is never counted twice as a host action.
- Existing `attack_refused` records now carry `attack_gate_<reason>`, including explicit `out_of_melee_range` for known geometry. `swing` adds target cell and received weapon_worn indices/locations (absence is unknown, not proof of bare hands). Existing own-source damage, death, EXP and drop observations remain the final conversions.
- End taps: `farm_intent_expired`, `farm_priority_yield`, `farm_target_not_visible`, `farm_approach_no_survivability`, `farm_pump_failed`.

Reproduce the window census with:

```sh
python scripts/analyze_farm_window.py /home/otto/dev/ro-bots/.work/runtime/population-live/traces > /tmp/leg121-farm-census.json
```

The checked-in sibling `leg121-farm-census.json` contains detached numeric counts only. The implementation is validated offline; the next population leg must establish the live kill-rate improvement.
