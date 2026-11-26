# LEG-134 VERDICT (Thu 2026-11-26, [[3,20.0,21.5]] 20:00-21:30 Madrid)

Receipt: run/plain_host_receipts/population-receipt-134-1795718339.json (written 21:30 during unit lifetime — 11th consecutive close-write proof)
Unit: leg134-runner, launch 19:38:54 CET (one minute ahead of the 19:40-19:55 slot; schedule gate held agents offline until 20:00), natural drain DONE 21:34:00 CET (exit 0, Result=success, `DONE: steps 20796, errors 0`); RuntimeMaxSec 7200 never fired. NOT killed.
Population: 29/29 personas; receipt steps 20,198 (DONE total incl. drain 20,796); step_errors 0; offline_agents [] at close.

## PREFLIGHT (hard gate, 19:38 — all PASS)
- DECIDE-OK http://192.168.1.156:8091/v1/systemone 0.71s answers=10 (warm bar <3s: PASS; early probe 0.65s at 16:03)
- :8092 /health 200 (PASS)
- Weekday verified: jeudi, Python weekday() 3 = schedule [[3,20.0,21.5]] (PASS)
- e2e world up (login/char/map/mariadb all Up); no stale runner unit pre-launch.
- Baselines read FRESH pre-window (19:40, double-read certified identical): picklog M424/L325/P238/S219 (max time 14:25:15Z), zenylog 142 (max 14:25:15Z), per-char zeny == seed-zeny.json exactly, fleet 3,567.

## BAR VERDICTS: 4/5 PASS

### BAR 1 — BOTH-ARM HOLD (attackers >=15 AND sellers >=12): PASS (22 + 16, 14 both-lists)
- Attackers 22/29 (attacks_authored>=1 or swings_sent>=1; fleet 546 authored, 367 swings sent) — above the 15 bar and up from leg-133's 19.
- Sellers 16/29 distinct (DB zeny delta vs seed, zenylog-reconciled): RinceNyan, zeny_wing, PipinWalker, xXLunasongXx, PoringMuffin14, xXDoramrinXx, xXAerofyXx, SoraSama22, misu_drop, KafraMuffin52, zeny_hunter, rince_ko, TalonWind, ZenySong, xXHyupunchXx, VelRin85.
- 14 agents on BOTH lists (leg-133: 12) — strongest single-window both-arm overlap recorded; the rotation trades arms without losing either.

### BAR 2 — kills vs 41: PASS (73 kill_credits, new peak)
- swing_conversion_v1 fleet: attacks_authored 546, swings_sent 367, damage_events 322, damage 7,196, kill_credits 73, exp +282 base/+126 job, 22 distinct killers (top: pop_0069_g02m02 12, pop_0069_g04m01 11, pop_0069_g03m01 and pop_0003_g01m02 8 each).
- 73 > 56 (leg-133 peak) and > 41 bar. Combat scaled with the participation chain rather than rotating down.

### BAR 3 — fleet zeny vs 3,567: PASS (3,819, +252, exact zenylog reconciliation)
- In-window: 20 S-rows summing +214 across 15 sellers; ONE further S-row at 20:30:15Z (PoringMuffin14 +38, a sell session completing seconds after nominal close in the drain) brings the new-row total to 21 rows = +252 = the fleet delta EXACTLY. Zero unlogged movement; all 21 new rows type S (no buys this window).
- Top earner rince_ko +73 (3 sessions, 76→149z); xXAerofyXx +43 (3 sessions). PoringMuffin14 924→967z (+43 incl. the drain row) — still 283z short of the 1,250z 1204 knife at live prices.
- 16 sellers is a new seller-arm peak (leg-133: 16; leg-132: 5-era) and fleet zeny velocity +252 vs +349 last window on a deeper seller base.

### BAR 4 — DROP-COVERAGE RESOLUTION (new instrument, 0bb034c0): FAIL on UNKNOWN share; fleet-attempted WATCH first-time PASS
- The reason classes ran live. Full distribution over 39 unattempted sightings (118 nearby, 50 cohort-attempted, 29 fleet-credited, 4 attempts outside cohort, 35 legacy residual): out_of_approach_range_owned 0, spawn_timeout_far_kill 0, map_transition_blindness 0, despawn_before_observation 3, **unknown 36**.
- UNKNOWN 36/39 = 92% — the bar was <50% of uncovered (leg-133 replay: 31/36 = 86%). The classifier did NOT shrink unknown; every unattempted row still carries per-drop evidence (last_gate authored_action/combat_priority/walk_arrival_gate, outcome 'deferred') but the top-level class assignment defaults to 'unknown'. Named-next below.
- WATCH (>=70% era target): fleet-attempted 83/118 = **70.3%** — first window at/over the era target (leg-133: 65.5%). fleet_success 82/83 = 98.8%; agent_attempted 54/118 = 45.8%, agent success 53/54 = 98.1%. Coverage moved without any loot-arm code change — the seller-arm depth (16 sellers) left fewer agents parked on drops.

### BAR 5 — receipt close-write 11th consecutive: PASS
- Receipt mtime 21:30 with leg134-runner ActiveState=active (verified 21:31:06); unit exited naturally Result=success exit 0 at 21:34:00 (journal: "Consumed 44min 24.054s CPU over 1h 55min wall"). Kill-safety law held.

## DECIDE HEALTH (window-filtered 18:38→20:35 UTC, error-field split)
- Attempts 4,493: OK 4,463; CAPPED (error) 30 = **0.67%** capped share; 0 unpaired teardown rows.
- TRUE p50 **1.16s**, p90 3.55s, max 13.81s (leg-133: 0.2% / 0.94s — slightly deeper share, still sub-1% healthy band).
- Runner-log Tracebacks 32 vs 30 capped decide rows — the 2 extra are transport-side, not decide.
- Per-agent attempts min 104 / median 132 / max 321 — no decide starvation anywhere.

## TRANSPORT / STUCK CELLS
- TRANSPORT DOWN: 29 one-shot runner-log events (leg-133 cadence); transport_recovery 296 attempts across 29 agents, exhausted=false for every agent, offline_agents [] at close; online 28-29/29 across the whole window (29/29 by 20:12, brief 28/29 dips only).
- Stuck cells: 5 named bots (YuffieFy81 (169,374)/(169,373), AeroSong25 (206,359), zeny_wing + zeny_hunter (170,375), PoringMuffin14 prt_fild06 (30,200)), 1 escalation (zeny_hunter), all self-recovered; no fleet stall.
- Merchant drive: sell_contact_authored 20, sell_contact_hold 2,278 (the dealer-ring conversation-slot holds; 16 conversions landed through it anyway), attack_refused log lines 215 (cooldown class per receipt).

## NAMED NEXT
1. Drop-coverage classifier (bar 4): the tap now records per-drop gate evidence (authored_action / combat_priority / walk_arrival_gate, deferred outcomes) but assigns 'unknown' at the top level. The class assignment must consume that evidence — e.g. combat-priority-deferred-then-expired is a named class, not unknown. Only then can fleet-attempted >=70% become a stable bar instead of a watch.
2. Buy-leg reach: PoringMuffin14 967z vs the 1,250z knife — at this window's +43 rate it needs ~6-7 more selling windows solo; a funded agent (rince_ko 149z is far off; the fleet's zeny is diffuse) or a higher-rate grind species is the lever for the first in-window purchase.
3. No buys again (zenylog all S, 21/21): the buy arm proved live at leg-111 but the fleet never pools 1,250z on one char — consider a designated purchaser persona receiving the grind allocation.
