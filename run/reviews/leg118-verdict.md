# Leg-118 verdict (2026-11-20 Fri 14:00-15:30 CET, 29 personas) — farm-arm release fires but does not sustain; zeny flat

Runner: population-receipt-118-1795171741.json, 59,311 steps, 0 step errors.
Launch note: the brief's template duration (9000 s) would have killed the runner at
14:17 CET (deadline is wall-clock from launch — the leg-117 receipt/journal prove the
shape), so the leg was launched at 11:49 with duration 16500 / RuntimeMaxSec 16800
(same duration+300 law), covering hold + full window + post-close drain. Runner exited
cleanly at its own deadline at 16:24 CET.

## T1 zeny conversion — FAIL

Fleet zeny 1580 == seed 1580, delta 0, zero changed personas (DB readback of all 29
chars). sell_contact_authored 0, TalkToNpc actions 0, picklog S +0, zenylog +0. No
seller contact was minted all window. Leg-117's opening conversions (2 sellers, first
3 min) did not recur because nothing was looted into inventory this window to sell.

## T2 decide health

ok 5,284 / capped 7,431 = **58.4% capped**; TRUE success p50 **2.01 s**, p90 **3.92 s**
(error-field split, window-scoped). Saturation continues its window-variable band
(leg-112 49.1% → leg-113 57.0% → leg-118 58.4%) while success latency stays flat at
~2 s — admission-side shaping, not a wedge.

## T3 cadence band

25/29 agents in the 75–305 successful-decide band. The 4 below are
pop_0069_s01 (34), pop_0069_g02m01 (55), pop_0069_g00m02 (47), pop_0069_s02 (65) —
3 of the 4 are the window's only attackers (combat-busy between decides, not starved).
None above band. Per-agent ok min/max 34/238.

## T4 transport health

23 transport drops, 23 rebuilds, **0 exhausted** — every drop recovered via the connect
backoff. Churn higher than recent legs but no agent was lost.

## T5 combat/feed — PARTIAL: the release tap works, the sustain does not

- attacks_authored **69** by **3/29** agents (leg-117: 1/29, and leg-117's 28-zero-attack
  signature is improved but nowhere near fleet-wide). swings 60, damage events 58,
  damage 1,493, kill_credits **6**, base exp +15 / job exp +16, unattributed 2.
- drops_seen **5** (> 0 bar met) but **pickup_attempts 0** — the drop chain died on the
  floor: nobody authored a Loot action all window (picklog P +0).
- merchant_arm_released_drained **8** — all early-window (5 by 14:05, 8 by 14:37, flat
  thereafter). The released arms produced the only farming; after 14:37 the fleet
  re-parked: prt_in carried ~75% of decide volume, field decides were a trickle.
- Merchant gates (last-sample fleet sum): admission.merchant_trip_retry_cooldown 568 +
  trip.retry_cooldown 95 = 663 cooldown gates, admission.no_stock_below_zeny_floor 283,
  contact.dealer_not_adjacent 215, allocation gates 300, contact.no_sellables 66.
  npc_stage chains all clean at close (no held dialogues).
- Picklog delta vs leg-117 cumulative (M77/P43/L26/S21, zenylog 13): **M+4, P+0, L+1,
  S+0, zenylog +0** — consistent with 6 kills, 0 pickups, 0 sales.

## Next hop (named from the taps)

1. **The drained-release is one-shot, not a mode.** The return leg after
   no_stock_below_zeny_floor (283 refusals) re-enters the trip cycle through the retry
   cooldown (663 gates) instead of re-arming the farm arm — released_drained froze at 8
   at 14:37 while trips kept cycling for the last hour. The release needs to fire on the
   post-trip return path, or the cooldown needs to carry a farm-mode lease.
2. **Drops are never picked up.** drops_seen 5 → pickup_attempts 0 with attackers ON the
   field: the loot arm never owned the pickups (approach.pickup_required fired only 3
   times). The kill→pickup→stock link is the next breakage in the conversion chain —
   without pickups there is no stock, and without stock T1 can never move.
3. Inventory note: agents hold sellable misc (e.g. Empty Bottle, sellable 200z per the
   decide knowledge line) while contact.no_sellables fired 66 times — worth checking
   what the merchant-drive admission counts as a sellable.

Bar verdict: **NOT MET** (sells did not sustain — there were none; fresh stock did not
flow — nothing was picked up; farmers left the dealer only 3-strong, once, early).
The farm-arm admission release (ae048b77) is mechanically live (tap fires, releases
produce real kills) but does not yet sustain farming beyond the opening half hour.
