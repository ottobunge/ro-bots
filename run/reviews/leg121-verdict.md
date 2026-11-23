# LEG-121 VERDICT — dealer-ring convergence validation (948f59cb)

Window: Mon 2026-11-23 20:00–21:30 Madrid (CET), 29 personas `[[0,20.0,21.5]]`.
Staged HEAD 572a2c9a; shepherd unit `leg121-runner`, launched 16:22:35 CET (DUR 19345s, RuntimeMaxSec 19645s), DONE 21:45.

**Verdict: PARTIAL PASS — 3 of 4 bars met (2, 3, 4); bar 1 undemonstrated (no idle-hold occurred to release), its guarded failure mode absent.**

## Preflight

- `decide_probe` :8091 → `DECIDE-OK ... 0.47s answers=10` (warm, <3s gate met).
- :8092 health → 200 `{"status":"ok"}`.
- World: ro-bots-e2e containers up (login/char/map/mariadb, map up 5d).

## Window health

- 29/29 online across the window (runner-sample min 0 = the first pre-login sample).
- Runner DONE: **65,346 steps, 0 errors**; receipt written 21:45 BEFORE unit exit (duration law held; no reconstruction needed).
- Decide health (trace `decide_response`, error-field split): **212,844 ok / 80,956 capped-error = 27.6% capped; ok p50 1.41s, p90 8.89s, mean 2.91s** (leg-120: 1.34s / 27.5% — regime stable).
- End-of-window census: **0 agents parked in the prt_in dealer box** (last-live sample t=18448.6, all 29 on field/other positions, all distinct).

## Headline bars (from leg-120 verdict)

1. **walkable_free > 0 at the ring (ring_lease_released_idle firing): NOT DEMONSTRATED — 0 taps all window.** No lease holder ever idled 5s at the counter, because nobody held it idle. The leg-120 starvation shape (walkable_free 0/8 with a parked peer) did NOT recur: no parking anywhere, the single counter visit was clean in-and-out. The tap is a release signal; with no idle-hold there was nothing to release. Treat as unproven-positive, not violated.
2. **Contacts admitted ONLY at received Chebyshev<=1: MET.** Zero out-of-range contacts (leg-120: 35 silent rejections). The one counter contact was authored at (172,129) — Chebyshev 1 from the dealer (172,130).
3. **Stockless agents END trips: MET.** `merchant_stock_below_trip_minimum` 29 + `no_stock_below_zeny_floor` 43 = 72 terminations (leg-120: 654+295 multi-hour HOLDS), zero end-of-window dealer parking, counter freed after each visit.
4. **Zeny movement vs fleet seed 1741: MET — 1741 → 1746 (+5).** One seller: **AeroSong25** (pop_0069_g02m00, char_id 300107) +5z, zenylog row 19:42:59 UTC = 20:42:59 Madrid, mid-window. Weak vs leg-120 (+161 / 13 sellers) — cause is input starvation, not funnel failure (below).

## The one sell, end-to-end (pop_0069_g02m00 trace)

19:42:07 warp prontera→prt_in (168,128) → 19:42:36 adjacent (172,128) → 19:42:38 `TalkToNpc 110001762` (decide/script-authored — hence `sell_contact_authored` 0: the pump path never needed to fire; decides were healthy) → 19:42:40 dialogue `opening` → 19:42:57 `unsupported_shop` → `NpcShopSellOpen` → 19:42:59 `NpcShopSell sales=[[3,1]]` (+5z, exact zenylog match) → 19:43:01 leaves for (168,124). Counter occupied ~24s, clean exit, no requeue.

## Why only one sell: the funnel is INPUT-STARVED, not blocked

- The fleet entered the window with sold-out bags (leg-120's 22 sell rows cleared them): inventory table holds 1201 x29 (knives), 915 x2, and singles — almost nothing sellable.
- In-window farm output: **34 attacks authored → 20 swings → 18 damage events → 5 kill credits (receipt) / picklog M+6; drops_seen 2, pickup_attempts 3, pickup_success 2 (picklog P+6).** Six kills fleet-wide cannot feed 29 sellers.
- Bag-first admission (948f59cb) correctly refused the unfunded trips: the 72 terminations ARE the fix working.
- Chat dominance persists: decide streams show heavy `chat` share (sell_wts/lfp premades, public crossfire audible in every trace).

## Baselines vs brief

- zenylog 26 → **27** (+1 in-window).
- picklog M83→**89** (+6), P45→**51** (+6), L27→**27** (+0), S43→**44** (+1).
- seed-zeny.json updated: fleet 1741 → **1746** (pop_0069_g02m00 21→26).

## Named next signature

**Farm-side combat throughput** — the economy is now demand-limited: the sell funnel, dealer ring and trip admission all behave; the missing input is loot. 34 attacks authored / ~6 kills / 90 min across 29 agents is the bottleneck. Levers: grind share vs chat share in decides, approach→attack conversion (20 swings from 34 authored), species-target spread. A leg whose bar is fleet kill rate >= ~30/window would feed the funnel 5x and give the ring real throughput to validate at scale.

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-121-1795447364.json` (swing_conversion v1 per-agent totals; samples 589).
- Runner log: /tmp/population_leg121.log (taps census: contact_walk_escalated 10, contact_walk_released_farm 3, merchant_stock_below_trip_minimum 29, no_stock_below_zeny_floor 43, ring_lease_released_idle 0, sell_contact_authored 0).
- Traces: `.work/runtime/population-live/traces/` (2.8 GB, 29 agents).
- DB readback via ro-bots-e2e-mariadb-1 (char/zenylog/picklog/inventory), SQL staged at /tmp/q121.sql, /tmp/q121b.sql.
