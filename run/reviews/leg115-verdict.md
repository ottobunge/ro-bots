# LEG-115 VERDICT (2026-11-19, window 14:00-15:30 CET, Thu)

**T1 HEADLINE (dealer adjacency rotation, merged 3a4569ad): FAIL — 0 sells fleet-wide.**
DB ground truth: fleet zeny 1530 == seed, zenylog 11 rows (no delta), picklog S19 (no delta).
The bar (>1 seller converting in-window) was not met; even leg-114's single post-close
sell did not recur.

## What the rotation fix DID achieve
- Funnel mouth opens instantly: the first head (pop_0003_g00m01 / RinceNyan) authored
  TalkToNpc at 14:00:06 — 6 s after window open — received the dealer C4
  (stage unsupported_shop) and minted NpcShopBuySelection at 14:00:08. Fastest shop
  contact of any leg.
- The leg-114 parking freeze is gone: 598 sell-arm admissions with 552 no-progress
  releases (60 s bound, rule route_distance_scaled) and 359 retries — agents CYCLE,
  none froze permanently. dealer_ring_saturated fell 743 -> 122.

## Why it still converts nobody (two stacked defects, evidence-cited)
1. **Non-seller head holds the counter all window.** RinceNyan (knife only, nothing
   sellable) took the counter at 14:00:06, browsed the BUY list, and never left:
   in-window actions = 48 Say + 1 PartyChat + the 14:00 shop pair, **0 MoveTo**, zero
   pump-driven moves. Its lease (COUNTER_LEASE_SECONDS 180) should have expired at
   ~14:03 and walked it out via `yield_target` — that never fired. Meanwhile
   `MerchantCounterQueue.admits` is False for every other agent while any received
   body occupies the counter ring, so 19 sellable-holders cycled at Chebyshev 2-5 for
   the whole 90 min. The handover contract (completion/failure) has no third path for
   "head admitted, contact refused by the no-sellables gate" — that head neither
   completes nor fails, and nothing evicts it.
2. **Sellable-holders stood AT the counter and authored no talk.** pop_0069_g00m01
   stood at (172,129) at 14:00:41 holding 705+909 (sellable) and authored
   PartyChat/MoveTo but no TalkToNpc; pop_0069_g02m01 stood there at 14:02:16 with
   938, authored only Says. `sell_contact_authored` fired 0 times fleet-wide despite
   598 admissions. The silent gate sits between the pump approach
   (`_advance_merchant_approach_on_tick`) and `_start_merchant_sell_on_tick` — the
   no-contact path is silent (no hold tap logged), so the next fix needs the
   shop_trace_probe / layer-probe treatment to name the refusing conjunct.

## T2 decide health — steady, unchanged from leg-114
capped 58.8% (leg-114 59.8%), TRUE success p50 1.95 s (1.96), p90 3.81 s. The decide
saturation is a stable platform condition, not a leg-115 regression.

## T3 cadence band — 27/29 in [75,305] decide counts (leg-114: 27/29, identical)
Outside: pop_0069_s01 (29), pop_0069_g00m02 (34) — the two field-side agents.

## T4 clean health — PASS
28,769 steps, 0 step errors; 24 TRANSPORT DOWN events, all rebuilt via the resilience
path ('rebuild scheduled' x47, sessions kept); 29/29 clean offline at envelope end.

## T5 economy context — n/a
No zeny moved; nobody approached the 1250z buy class (max holding 395z == seed).

## Next fix shape (for the next slice)
(a) A head whose sell contact is refused by the no-sellables gate must YIELD the lease
and walk out immediately (decide-independent pump path), freeing the ring for the next
FIFO head; (b) name the silent conjunct that refuses contact for sellable-holders
standing adjacent at the counter (probe before patch).

Receipt: run/plain_host_receipts/population-receipt-115-1795092137.json
Stats: run/reviews/leg115-readout-stats.json
Preflight (13:41): decide probe 0.65 s / 10 answers; :8091+:8092 health 200; 4 e2e
containers Up; baselines picklog M77/P43/L26/S19, zenylog 11, fleet 1530, HyuStar71=8.
