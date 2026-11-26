# LEG-133 VERDICT (Thu 2026-11-26, [[3,14.0,15.5]] 14:00-15:30 Madrid)

Receipt: run/plain_host_receipts/population-receipt-133-1795696821.json (written 15:30 during unit lifetime — 10th consecutive close-write proof)
Unit: leg133-runner, launch 13:40:07 CET (inside the 13:40-13:55 slot), natural drain DONE 15:35:48 CET (exit 0, Result=success). NOT killed.
Population: 29/29 personas; receipt steps 20,615 (runner DONE total incl. drain 21,622); step_errors 0; offline_agents [] at close.

## PREFLIGHT (hard gate, 13:28 — re-verified through the wait)
- DECIDE-OK http://192.168.1.156:8091/v1/systemone 0.56s answers=10 (warm bar <3s: PASS; earlier probes 0.57/0.82s at 12:17/12:47)
- :8092 /health 200 (PASS, stable every poll 11:06→13:40)
- Weekday verified: jueves, Python weekday() 3 = schedule [[3,14.0,15.5]] (PASS)
- e2e world up (login/char/map/mariadb all Up); no stale runner or leg13 unit pre-launch.

## BAR VERDICTS

### BAR 1 — BOTH-ARM SUSTAINED (attackers >=15 AND sellers >=15): PASS (19 + 16)
- Attackers 19/29 (attacks_authored>=1 or swings_sent>=1; 414 authored, 312 swings sent) — above the 15 bar, though down from leg-132's 27 (rotation + dealer trips, not a stall: decide cadence and movement stayed healthy all window).
- Sellers 16/29 distinct (DB zeny delta > 0 vs seed, zenylog-reconciled): NyxSong, zeny_wing, PipinWalker, PoringMuffin14, YuffieFy81, NyxNyan18, xXAerofyXx, AeroSong25, rince_ko, aero_song, xXHyubladeXx, RinceSong, sora_sama, rune_walker, doram_hunter, HyuStar71.
- Both arms held TOGETHER in one window for the first time: 12 agents appear on BOTH lists (attack-and-sell rotation live).

### BAR 2 — kills vs 41: PASS (56 kill_credits, new peak)
- swing_conversion_v1 fleet: attacks_authored 414, swings_sent 312, damage_events 290, damage 6,068, kill_credits 56, exp +179 base/+98 job, 18 distinct killers.
- 56 > 41 (leg-132) and > 48 (leg-131 prior peak). The piecewise shape holds: combat AND economy peaked together this window.

### BAR 3 — fleet zeny vs 3,218: PASS (3,567, +349)
- Per-char DB readback matched seed-zeny.json EXACTLY pre-window (fc66d97e rebasing confirmed live: all 29 chars at seed values, fleet 3,218).
- In-window: +349 across 16 chars; zenylog +20 rows, ALL type S, 13:02:26→14:25:15 UTC, summing exactly +349 — every zeny gain is a logged sell (full reconciliation, no unlogged movement).
- Largest single-window zeny gain recorded (prior best +78, leg-132). Top earner PoringMuffin14 +93 (924z total — still short of the 1,250z 1204 knife at live prices; buy leg not reached yet). No buys this window (zenylog all S).

### BAR 4 — FLEET pickup denominator (NEW, bf232dc0): FAIL on attempted (65.5% < 70%), success PASS
- fleet_attempted 57/87 drops = **65.5%** (bar >=70%: MISS by 4.5pp; leg-132 replay was 74.5%)
- fleet_success 57/57 = **100%** (bar >=70%: PASS)
- agent_attempted 43/87 = 49.4% (leg-132: 45.1%), agent success 43/43 = 100%.
- 14 drops were fleet-credited (cedes/peer-consumed confirmed by the new pickup_funnel accounting — the denominator works as merged). The miss is the 30 drops neither attempted nor credited: attempted coverage REGRESSED vs the leg-132 replay. Named-next: split this window's drop_unattempted_reason mix (cede/expiry vs true unattempted) before touching any loot-arm code.

### BAR 5 — receipt close-write 10th consecutive: PASS
- Receipt mtime 15:30 with leg133-runner ActiveState=active (verified 15:31:41); unit exited naturally Result=success at 15:35:48. Kill-safety law held.

## DECIDE HEALTH (window-filtered 12:40→14:30 UTC, error-field split)
- OK 3,829: TRUE p50 **0.94s**, p90 2.19s; naive p50 0.94s (identical — honest split)
- CAPPED (error) 9: capped share **0.2%** — best-ever band (leg-132 0.4%, leg-128 0.7%). The 9 runner-log tracebacks are exactly these 9 PlayingBackendError decides; fleet continued through all of them.
- The :8091 slot saturation seen in legs 110-116 did NOT approach recurrence.

## TRANSPORT / STUCK CELLS
- TRANSPORT DOWN: ~29 one-shot runner-log events; transport_recovery 337 total attempts across 29 agents, exhausted=false for every agent, offline_agents [] at close. Recurring one-shot pattern, absorbed by connect backoff; online 28-29/29 all window (29/29 by 14:26).
- Stuck cells: 11 stuck_cell_resets in the last sample; escalations named and self-recovered (zeny_wing, LunaHunter at prt_fild08 (170,375), HyuStar71 at (208,358)) — no fleet stall; dealer trips and roaming continued.

## LAUNCH/BOOKKEEPING
- Launched 13:40:07 CET via systemd-run --user --unit=leg133-runner --property=RuntimeMaxSec=7200; window opened 14:00 (28/29 online by 14:06, 29/29 by 14:26; last stagger pair pop_0069_s03).
- Baselines read FRESH pre-window (never stale): picklog M373/P194/L266/S183, zenylog 122, per-char zeny == seed sidecar exactly.
- Deltas: picklog M+51 / P+44 / L+59 / S+36; zenylog +20 (all S).
- Readout note: the 13:28 baseline parse initially reported zenylog 183 — a parser artifact (tab-less count line dropped, picklog-S row read instead). The fresh direct read (122) and the close reconciliation (122+20=142, sums exact) settle it; no anomaly in the log tables.

## NAMED NEXT
1. Pickup attempted coverage (bar 4): split drop_unattempted_reason for leg-133's 30 uncovered drops; only then decide whether the loot-arm needs a change. Success is not the problem (100% both levels).
2. Buy leg reach: PoringMuffin14 924z vs the 1,250z knife — one more selling window at this earn rate reaches it; the first in-window purchase remains the milestone.
3. Attack-arm rotation: 19 attackers vs 27 (leg-132) with kills at a record 56 — verify the dip is rotation (dealer trips) and not a plan-quality regression when the next schedule stages.
