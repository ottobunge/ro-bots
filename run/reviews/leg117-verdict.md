# LEG-117 VERDICT (2026-11-20, Fri 09:00-10:30 CET window)

Head 69598221 (merge: dialogue-opening survival — timely buffered C4 consumed before expiry).
Runner: population-receipt-117-1795160588.json — 29,730 steps, 0 errors, 29/29 online the full window.

## T1 zeny conversion — BAR MET: 2 sellers converted IN-WINDOW

| agent (persona) | seed | final | delta | proof |
|---|---|---|---|---|
| zeny_hunter (pop_0069_g02m01) | 0 | 35 | +35 | zenylog row 12, 2026-11-20 08:02:25 UTC (09:02 CET), type S, prt_in |
| RinceSong (pop_0069_g04m00) | 25 | 40 | +15 | zenylog row 13, 2026-11-20 08:03:27 UTC (09:03 CET), type S, prt_in |

Fleet 1530 -> 1580 (+50). Both sells landed 2-3 minutes after window open.
The dialogue-opening survival fix is VALIDATED: leg-116 saw 202 `opening->blocked`
stages and 0 talks; leg-117's first ring holders opened dialogues and completed sells.
Sampler caveat: npc_stage samples caught only 1 `opening` + 1 `unsupported_shop`
(30 s sampler too sparse for the fast completions) — the zenylog S rows are the ground truth.

## T2 decide health (error-field split)

Window 12,806 decide_response rows: 60.5% capped; TRUE success p50 1.96 s / p90 3.46 s.
Runner span 13,338 rows: 59.7% capped; TRUE p50 1.97 s / p90 3.56 s.
Saturation in the known load-dependent band; true latency stable.

## T3 cadence band (75-305 decides)

27/29 agents in band BY SUCCESS (159-224). By ATTEMPTS only 2/29 (451-511 — retry-inflated;
leg-116's attempts-vs-success split confirmed). Outside band: pop_0069_g00m02 (63 success /
157 attempts — the sole combat agent), pop_0069_s01 (42/101).

## T4 transport health

22 TRANSPORT DOWN events (native keepalive send failures); receipt transport_recovery:
attempts=0, exhausted=false on every agent — all rebuilt, 0 exhausted.

## T5 combat/feed health

Population swing totals: 8 attacks authored, 5 swings, 4 damage events (79 dmg),
1 kill credit, +8 base / +4 job exp — ALL from one agent (pop_0069_g00m02, alone in the
field at (147,236)). drops_seen 0, pickups 0. Picklog M77/P43/L26/S21 vs leg-116 close
M77/P43/L26/S19: S+2 only (the two sells); M/P/L unchanged. zenylog 11 -> 13.

## NEXT dominant signature (named telemetry only)

The funnel converted the first ring holders, then nothing for the remaining 87 minutes.
Gate taps (cumulative samples): admission.merchant_trip_retry_cooldown 120,642;
admission.no_stock_below_zeny_floor 53,140; allocation.counter_not_selected 42,236;
allocation.no_target 39,722; contact.dealer_not_adjacent 36,512; contact.counter_turn 35,321.
Log taps: sell_contact_authored 2, sell_contact_hold 1,527. 24/29 agents parked dealer-adjacent
(prt_in 166-173/126-134) at close. The farm->loot INPUT leg starved the sell half: 28/29
agents never attacked and drops_seen 0, so after minute 3 the fleet had no fresh stock —
no_stock_below_zeny_floor is partly a stock-input problem. Next leg: (a) why 28/29 authored
zero attacks (farm-arm admission), (b) merchant_trip_retry_cooldown semantics (120.6k
samples — the largest blocker).
