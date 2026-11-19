# LEG-114 VERDICT (2026-11-19, Thu 09:00-10:30 CET / 08:00-09:30 UTC)

Commit under test: 37e7deae (merchant talk-funnel validation stage; funnel fix 59e8a631).
Runner: population_host_runner, 29 personas [[3,9.0,10.5]], duration 9000 s, receipt
`population-receipt-114-1795074256.json`. 29,608 steps, **0 step errors**. Log: /tmp/population_leg114.log.

## T1 HEADLINE — merchant talk funnel: PARTIAL (first population sell, ring saturation is the remaining wall)

- **First population-wide sell conversion since the economy era began**: `pop_0069_s02` (HyuStar71)
  executed a complete sell chain — TalkToNpc 09:32:14 UTC -> NpcShopSellOpen 09:32:16 -> NpcShopSell
  09:32:18 — matching the zenylog row (char 300120, +8 z, 09:32:18 UTC). Fleet zeny **1522 -> 1530**.
  Sold Clover (705) + Jellopy (909): carried inventory from previous legs' loot.
- `sell_contact_authored` (the 59e8a631 decide-independent pump path): **1** event fleet-wide
  (bot=xXDoramrinXx, action=TalkToNpc, ~09:05 CET). Its contact did NOT convert (its zeny stayed 0).
- 3 agents authored TalkToNpc in-window (pop_0003_g00m00 x1, pop_0003_g00m01 x2, pop_0069_s02 x1);
  only pop_0069_s02 completed the shop exchange.
- **THE DOMINANT REMAINING WALL = dealer adjacency ring saturation.** The funnel converged most of the
  fleet into prt_in and then held it in a queue: `dealer_ring_saturated` 743, `dealer_outer_fallback` 87,
  `dealer_queue_yield` 21, `merchant_trip_released_no_progress` / `merchant_trip_retry` 673 each.
  `preferred_chebyshev<=1=unavailable` persisted for hours (8 free cells at the dealer shared by a
  converged fleet; agents parked at best_distance 2). HyuStar71's sale only landed at 10:32 CET —
  AFTER window close — because the drain cleared the ring and it then reached adjacency.
- **Parking fix VERIFIED**: `single_cell_path` holds = 0 all window; movement progressed while agents
  queued (queue-yield lines name cells changing, e.g. HyuStar71 (172,128) -> (168,125)). No agent froze
  on a peer body cell.
- Context from DB: in-window kills rolled 3 drops (picklog M 74->77), which were MONSTER-looted before
  any agent picked them up (L 21->26 are mob-gid rows; agent pickup_success stayed 0) — loot-side
  pickup competition is a separate gap. Picklog S 17->19 (the two sold items), zenylog 10->11.

## T2 decide health (split on decide_response.error — the INSTRUMENT LAW)

- attempts 13,243 / answered 5,318 / errors 7,925 -> **capped 59.8%** (leg-113 57.0%: ~flat, slightly worse).
- TRUE success p50 **1.96 s** (leg-113 2.01 s: stable), p90 3.72 s, max 14.92 s, 0 responses > 60 s.
- Time lost to caps ~1,981 agent-minutes. The :8091 backend answers correctly when it accepts; the
  saturation is admission-side, not latency-side.

## T3 cadence band (75-305 decides, receipt last-sample)

- **27/29 in band** (leg-113: 26/29). Below band: pop_0069_s01 (35 decides), pop_0069_g00m02
  (the window's only fighter — it worked on script steps). None above.

## T4 clean health

- 0 step errors; 26 transport rebuilds, **0 exhausted**; **29/29 clean offline**; final_online_count 0.

## T5 economy context

- No agent approached the 1250 z buy class (fleet max 222 + this window's +8 = 230 for the richest;
  HyuStar71 now 8). The sell->buy ladder now has a PROVEN first rung (sell) at population scale, but
  ring saturation caps conversion volume far below what accumulation needs.

## Combat context (single-agent)

All authored combat came from pop_0069_g00m02: 67 attacks authored / 59 swings / 57 damage events /
1,548 damage / **4 kill credits** / exp +8 base +13 job / 3 drops seen / 0 pickups. The rest of the
fleet was merchant-locked (selling or queued) — the funnel's goal forcing works fleet-wide.

## Verdict

VALIDATED (partial): the decide-independent funnel minted contacts and completed the first population
sell; the parking fix holds (0 single_cell_path). NOT YET: conversion volume — the dealer ring admits
~one seller per window. NEXT lever: adjacency rotation at the dealer (admit queue heads to the ring one
at a time with a bounded conversation slot), so trips convert DURING the window instead of in the drain.
