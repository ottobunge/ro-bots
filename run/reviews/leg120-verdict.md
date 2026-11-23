# LEG-120 VERDICT — sell-contact authorship validated LIVE (2026-11-23)

Window: Mon 2026-11-23 14:00-15:30 CET, 29 personas `[[0,14.0,15.5]]` (schedule-leg120.json), main 44c188c6.
Runner: systemd-run `leg120-runner`, launched 12:10:27 CET detached, duration 12873s
(launch->close + 900s margin per the leg-119 receipt-loss law), RuntimeMaxSec 13173s.
Preflight (hard gate): DECIDE-OK 0.72s answers=10 warm against heavengraph :8091; :8092 health 200.

## Receipt landed BEFORE unit exit (duration law held)

`POPULATION-RUNNER[120] DONE: steps 33361, errors 0, receipt run/plain_host_receipts/population-receipt-120-1795432234.json`
— the unit reached `inactive` naturally at ~15:45 (last sample t=12817.7 < duration 12873).
No RuntimeMaxSec kill, no receipt reconstruction needed this leg.

## HEADLINE — all four bars MET (f188bf46 escalation ladder validated live)

| Bar | leg-119 | leg-120 | verdict |
|---|---|---|---|
| sell_contact_authored > 0 | 0 all window | 4 | MET |
| zeny movement vs fleet seed 1580 | flat at 1580 | 1580 -> 1741 (**+161**) | MET |
| escalations fire but recover, not exhaust | taps died by t~2998 | escalated 70, released_farm 21, ladder cycling | MET (with caveat below) |
| pickup_attempts > 0 | 3/3 | 2 attempts / 2 success (100%) | MET |

## Economy ground truth (DB readback)

- zenylog 13 -> 26: **13 in-window S transactions** at prt_in from **13 distinct sellers**
  (13:03:56-14:11:49 UTC; first-time sellers LunaHunter +39z, doram_hunter +38z from 0 seed).
- picklog M 84 -> 86 (+2), P 46 -> 48 (+2), L 27 (0), S 21 -> 43 (**+22 sell rows**).
- Char table: 29/29 found; top holders YuffieFy81 395, RinceNyan 222, NyxSong 203,
  PipinWalker 164, zeny_wing 147, xXLunasongXx 145, PoringMuffin14 134.
- seed-zeny.json updated in the same commit (fleet 1741).

## Combat / loot (receipt swing_conversion)

21 attacks authored -> 14 swings -> 11 damage events -> 253 damage -> **5 kill credits**
(Drops x3, Poring x2) across 6 attacking agents; base_exp +8, job_exp +5;
xXLunasongXx reached base_level 11 (first level-up this era's windows).

## Decide regime (split per the instrument law: decide_response rows on the `error` field)

n=283,897 rows: OK 205,934 (p50 **1.34s**, p90 6.08s, mean 2.57s) / capped 77,963
(**27.5%**, capped p50 15.02s). The leg-119 queue-latency regime (ok p50 13.6s at 19.9%
capped) is GONE — successes are fast again; capped share is admission-side.

## Transport / health

27 TRANSPORT DOWN events during the login stagger; by 14:17 they were 14 distinct agents
at 1 bounce each (single-bounce shape, backoff recovered all; final transport_recovery
`exhausted: false` for every agent). 29/29 online through the window body. 0 step errors.

## Named next signature: dealer-ring approach convergence, not authorship

Authorship (4) still lags realized sales (13) — the pump contact path is no longer the
only conversion route (sell_batch trips convert), so the funnel's remaining friction is
UPSTREAM of the talk: 2,299 `sell_contact_hold` lines dominated by `pending_walk`
(1,968) and dealer-ring occupancy gates reading `reachable=0/8 walkable_free=0/8
preferred_chebyshev<=1=unavailable` while one peer holds the single walkable ring cell
(35 `dealer_talk_out_of_range` at chebyshev 3-4). The ladder correctly releases stalled
walkers to farming (21 releases, farm arm re-armed), which converts but costs trips.
Admission-side holds also significant: no_stock_below_zeny_floor 654,
merchant_stock_below_trip_minimum 295 — a third of the fleet simply has nothing to sell.
Next leg lever: ring-approach convergence / faster counter handover for stocked agents,
plus faster stock accumulation (kills -> drops) for the stockless majority.

Raw evidence: /tmp/population_leg120.log, traces under .work/runtime/population-live/traces/
(2.7 GB, decide split computed from all 29 agent files).
