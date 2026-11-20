# Leg-117 farm-arm admission probe (2026-11-20)

Offline sources: `run/plain_host_receipts/population-receipt-117-1795160588.json`,
`run/reviews/leg117-verdict.md`, and the parent checkout's
`.work/runtime/population-live/traces/*.jsonl`. Trace rows were filtered by
`2026-11-20T08:00:00 <= t < 2026-11-20T09:30:00` UTC
(09:00–10:30 Madrid). Historical rows in these append-only files were excluded.
No runner, world connection, SQL probe, or server operation was used.

## Findings

* zeny_hunter (`pop_0069_g02m01`) had 475 `decide_request` rows, all with
  `bot.goal=grind`. Its successful `next_action` choices included 193 `grind`;
  281 response rows had no action because of decision errors. The
  08:02:06.421387 `goal_review` kept grind with `trigger=heartbeat`.
  The first drained request is 08:02:27.490936: inventory `1201x1`, goal grind,
  with grind/travel options still available. `state_tick` at 08:03:07.544953
  records `(prt_in,172,128)`, inventory `1201x1`, zeny 35; by 08:04:15.720649
  it is `(170,128)` and stays there. Across the receipt samples its gate
  counters include `admission.no_stock_below_zeny_floor` and
  `approach.counter_released:completed`.
* RinceSong (`pop_0069_g04m00`) had 466 requests, all grind; 190 successful
  grind choices and 275 responses without an action. Its drained request is
  08:03:31.228443. At 08:04:24.500533 `state_tick` records `(prt_in,173,129)`,
  `1201x1`, zeny 40. The receipt records completed/no_sellables counter
  releases, but no field departure.
* `pop_0069_s02` is already empty at 08:04:26.641141:
  `(prt_in,169,126)`, `1201x1`, zeny 8. All 427 requests retain grind;
  146 successful grind choices do not get it out of the room. Its receipt
  samples repeatedly name `admission.no_stock_below_zeny_floor`.
* Empty-stock cooldown cycling does exist, but the clearest sampled agent
  (`pop_0003_g00m00`) has **zeny 203**, so its buy arm remains admissible.
  It carries only `1201x1` throughout the window, has 452 grind requests and
  159 successful grind choices, and stays at `(167,127)` for most of it.
  Receipt samples alternate growing `trip.retry_cooldown`,
  `admission.merchant_trip_retry_cooldown`, and allocation/counter gates.
  This is not proof that the no-stock/below-floor conjunct re-admits.
* Across all 29 trace files, request/review goals are grind, farm_item or
  social; none is sell. The domain `Goal` enum also has no sell member.
  There is no evidence for adding a forced goal flip or goal_review trigger.

## Supported mechanism and change

`merchant_admission_refusal` already evaluates the stock/budget want before
retry cooldown. However, the drained trip record survives until the old
cooldown expires; `_merchant_step` returns early during that cooldown;
`merchant_return_cell` rejects the worn knife unless a previous runtime
return flag survives; and the independent merchant pump only advances
outbound admission. An empty counter refusal also chooses temporary queue
parking rather than the return route. Successful grind decisions therefore
do not guarantee a field return, particularly across transport rebuilds.

Release the old trip immediately when known bag plus collectible in-flight
stock is zero and there is no affordable buy budget. Name the transition
`merchant_arm_released_drained`, allow the existing return route despite a
worn weapon, and advance that route on the existing host pump under its
movement, dialogue, poison and cancel barriers. A released drained counter
uses the same body-aware exit as a completed sale. No goal is rewritten;
stocked sellers, collectible pickups and affordable buyers retain their
existing admission/retry rules. Received new stock can admit a fresh trip.

The receipt gate totals are sums of cumulative sampled counters, not counts
of independent trips. This slice addresses drained agents without a buy
want; it does not claim to fix stocked queue congestion or affordable-buy
cycles, or establish live combat recovery without a later scheduled run.
