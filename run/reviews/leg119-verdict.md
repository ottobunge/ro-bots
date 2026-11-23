# Leg-119 verdict (2026-11-23 Mon 08:15–10:40 CET, 29 personas) — loot fix lands 3/3 pickups, farm re-arm persists; sell contact never authors, zeny flat

Receipt: population-receipt-119-reconstructed.json. The ORIGINAL receipt was lost:
the runner's own t=8400 exit was starved by a blocking host.step() (backend-stall
PlayingBackendError storm) and RuntimeMaxSec killed the unit at 10:40:05 CET
mid-step, before the receipt write. The receipt was reconstructed from the
2.83 GB of surviving window-filtered traces + the runner log + a fresh DB
readback (provenance inside; lost fields: steps, per-sample gate finals,
transport_recovery map). Launch 08:15:05, schedule [[0,9.0,10.5]] (window
09:00–10:30), duration 8400 / RuntimeMaxSec 8700 per the duration+300 law.

## T1 zeny conversion — FAIL

DB readback: fleet zeny 1580 == seed 1580, delta 0, zero changed personas (all
29 chars match seed per-char). sell_contact_authored 0, picklog S +0, zenylog +0
(13 rows, all type S, unchanged). The 3 pickups created real inventory stock but
no sell was ever admitted — the chain now dies at contact authorship, not loot.

## T2 decide health

ok 7,951 / capped 1,981 = **19.9% capped** (window-scoped error-field split;
leg-112 49.1 → leg-113 57.0 → leg-118 58.4 → leg-119 19.9). The regime inverted
its shape: the backend stopped rejecting and started queueing — ok p50 ≈ 13.6 s,
p90 ≈ 14.6 s (timeout-adjacent; leg-118: 2.01/3.92 s). Same load, moved from
cap-rejection to latency. 9,932 decide responses in-window.

## T3 cadence band

At the close sample (t=8099.1): 28/29 online, 27/29 in the 75–305 band, median
276, min 73 (pop_0069_s01), max 312 (pop_0003_g01m01; pop_0003_g00m02 309).
Healthiest spread of the recent legs; leg-118's 4-laggard tail is gone.

## T4 transport

24 TRANSPORT DOWN distinct-reason lines (leg-118: 23 drops/rebuilds, 0
exhausted). Per-agent rebuild finals were lost with the kill, but 28/29 still
online and all 29 deciding at the last full sample — nobody was dropped
permanently. 0 host.step raises (first-3 alarm never fired).

## T5 combat/feed — the loot fix works end to end (into inventory)

- attacks_authored **32** by **4/29** agents (leg-118: 69 by 3/29); swings 18,
  damage events 10, damage 219, kill_credits **3**, base exp +3 / job exp +3,
  unattributed 0, telemetry_dropped 0, coverage wire_observations on all 29.
- drops_seen **3** → pickup_attempts **3** → pickup_success **3**: **100%
  drop→pickup conversion** (leg-118: 5 drops, 0 pickups). DB cross-check:
  picklog M+3/P+3 — each trace pickup has its picklog pair. **Bar (1) MET**
  (the eefb95c4 loot-ownership fix).
- farm<->sell alternation: farm_arm_rearmed_post_trip fired **30×**
  (PipinWalker, YuffieFy81, RinceNyan, PoringMuffin14, …), first at t=2780.9
  (~80 s after open) and last at t=8099.1 — the final sample of the window.
  merchant_arm_released_drained only 5 all window. The re-arm is a persistent
  mode, not leg-118's one-shot (frozen at 8 by 14:37). **Bar (3) MET.**
- Merchant gates: contact.no_sellables **15** vs leg-118's 66 — and all 15
  fired in the opening 25 s (t=2687.7–2724.3); the flood is gone. Dominant
  holds are now contact-motion: pending_walk **2216**, merchant_post_trip_return
  65, retry_cooldown 22, no_stock_below_zeny_floor 21 taps (16 as hold reasons)
  — window-long (last at t=7608.4). Dealer churn otherwise normal
  (outer_fallback 29, queue yields 8, one ring handover).
- **Bar (2) NOT MET on the outcome**: the gate dropped as asked (66→15) but
  zero sells were admitted — sell_contact_authored 0, S +0, zenylog +0. Stock
  exists (3 pickups); the sell arm holds forever on pending_walk and never
  mints the contact.

Bar verdict: **PARTIAL** — bars (1) and (3) met, bar (2) not, zeny unmoved.

## Next hop (named from the taps)

1. **The contact attempt never completes its walk.** pending_walk 2216 holds vs
   0 authored contacts: the sell arm raises "contact" then waits on motion that
   never reaches dealer adjacency (dealer_not_adjacent taps died out by t≈2998 —
   after minute 5 nobody is even re-evaluated at the dealer). The sell leg needs
   a walk-completion escalation (timeout → route retry / counter fallback) where
   the merchant trip legs already have one.
2. **Post-pickup stock may not read as sellable.** 16 no_stock_below_zeny_floor
   contact-holds fired across the window even after 3 pickups landed (agents
   hold sellable misc, Empty Bottle 200z per the decide knowledge). Check what
   admission counts as stock post-pickup — the new inventory rows may not be in
   the known-stock set.
3. Decide-regime watch: 13.6 s p50 queue latency at 19.9% capped is a different
   saturation shape from legs 112–118 (~2 s p50 at 50–60% capped). Cooldown math
   calibrated on 2 s decides (retry_s=120, trip bounds) is now pacing against
   14 s decides.

The conversion chain is now one hop short: kill → pickup → stock all work;
**contact authorship** is the next breakage before a sale can move zeny.
