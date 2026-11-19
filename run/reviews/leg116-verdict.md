# LEG-116 VERDICT (2026-11-19, window 20:00-21:30 CET, Thu)

**T1 HEADLINE (counter handover gate, merged cb76f27a): FAIL on conversion — 0 sells
fleet-wide (bar was >1). The gate's observability half is fully proven; the throughput
is now blocked one hop earlier, inside the NPC dialogue machine, and the fleet's stock
input is drained.**

DB ground truth: fleet zeny 1530 == seed (zero delta), zenylog 11 rows (no delta),
picklog M77/P43/L26/S19 identical to the pre-window baseline (zero rows). NpcShopSell
actions in-window: 0. `shop_offer` carried rows in 0 of all receipt samples — the C7
sell list NEVER arrived fleet-wide this window.

## What the counter handover gate DID prove (leg-115's two defects closed as designed)

1. **No silent conjunct survives.** Every refusal names itself. Receipt
   `merchant_contact_gates` (cumulative gate samples): admission.merchant_trip_retry_cooldown
   127,185; admission.no_stock_below_zeny_floor 45,512; contact.dealer_not_adjacent 45,063;
   contact.counter_turn 44,088; allocation.counter_not_selected 38,832; allocation.no_target
   36,592; trip.retry_cooldown 21,949; counter.counter_turn 20,399; contact.no_sellables
   15,219; approach.actuation_blocked 3,323 / approach.dialogue_open 3,322 /
   approach.npc_failed 3,177. The runner log carries `sell_contact_hold` taps with the same
   conjuncts per agent and stage.
2. **The counter releases on failure.** The only admitted head (zeny_hunter, stock=1,
   adjacent at (173,129)) authored TalkToNpc twice (sell_contact_authored x2); each
   contact opened the dialogue, failed, and RELEASED the counter — runner log shows
   `dealer_counter_yield` x4 ending `reason=retry_exhausted` and
   `counter_released:retry_exhausted` / `counter_released:expired` holds. The leg-115
   "head holds the counter all window" shape did not recur.
3. **Non-head FIFO blocks are named, not silent** (`counter_turn` 64.5k samples across
   counter + contact stages). `no_sellables` empty-sellers are named at contact (15.2k).
   Note: no empty-sellables head actually took the counter this window (the sole admitted
   head held stock=1), so the empty-head walk-out path fired only as named refusals, not
   as an observed end-to-end walk-out — the leg-115 RinceNyan scenario never got a live
   trial.

## The remaining defect (next slice): the sell exchange dies at dialogue OPENING

npc_stage samples across the window: `blocked` 202, `opening` 5 — nothing else. Both
authored contacts show the identical shape:
`TalkToNpc -> dialogue opening -> npc_failed -> counter released -> trip retry_cooldown`
(zeny_hunter's second contact additionally names `dialogue_open,actuation_blocked`).
The dialogue never advanced past opening: the dealer's C4 (ZC_SELECT_DEALTYPE) answer was
never consumed. Prime suspect: 27/29 agents took `NativeTelemetryUnavailableError: native
keepalive send failed` transport drops this window (all rebuilt, 0 exhausted) — a drop
between the 0x0090 click send and the C4 arrival eats the answer and the 5 s opening
deadline fails the dialogue. Probe (shop_trace_probe / layer probe on the C4 exchange
under load) before patching.

**Secondary input starvation:** the fleet stopped farming — 3 Attack actions all window
(vs MoveTo 4,019 / Say 2,653), zero picklog rows, and `no_stock_below_zeny_floor` refusals
at 45.5k: agents hold no sellables and no zeny, so admission correctly refuses them.
27/29 agents stood in prt_in the entire window (only 2 map transitions). The economy's
input side (farm -> loot -> stock) never engaged; the funnel cannot convert an empty
warehouse. Guild/social activity continued (GuildInvite 79, FoundGuild 4, FoundGuild
parties live).

## T2 decide health — steady
capped 60.4% (leg-115 58.8%, leg-114 59.8%), TRUE success p50 1.92 s (1.95), p90 3.36 s
(3.81), attempts 12,813 / answered 12,789, 0 unpaired. Same load-dependent saturation
profile; decide health is a stable platform condition, not a leg-116 regression.

## T3 cadence band 75-305 — FAIL (2/29; leg-115 27/29)
Per-agent decide counts: median 463, IQR 442-481, max 513, min 96; 27/29 OVER the band,
0 under. The count is inflated by capped-decide retries (60.4% capped answers re-enter
the decide loop); band semantics need an attempts-vs-success split or the band edge needs
re-baselining before it stays a usable health signal.

## T4 clean health — PASS
29,182 steps, **0 step errors**, 27 transport rebuilds 0 exhausted, all 29 agents online
through the window, 29/29 clean offline at schedule close (receipt offline_agents = all
29 at envelope end).

Receipt: `run/plain_host_receipts/population-receipt-116-1795114230.json`; stats:
`run/reviews/leg116-readout-stats.json`. Seed-zeny unchanged (zeny flat — no refresh).
No heavengraph services touched; no live probes during the window.
