# Leg 131 verdict — Wed 2026-11-25, window 20:00–21:30 Madrid (29 personas, [[2,20.0,21.5]])

Launch 19:40:11 CET, duration 7489s, RuntimeMaxSec 8389s, systemd unit `leg131-runner`.
Preflight: DECIDE-OK 0.53s answers=10 (warm) against heavengraph :8091; chat :8092 health 200.
Receipt: `run/plain_host_receipts/population-receipt-131-1795632018.json` (6.1 MB, on disk 21:31:20 CET with the unit still active — close-write verified, 8th consecutive).

## Headline

The dual operator reset + walkable-seed work is VALIDATED in vivo: both reset chars logged in exactly at
pay_fild04 (20,165) and roamed immediately (871 and 110 distinct cells). Combat hit the era peak
(23/29 attackers, 48 kills @ 2.09/attacker). Sells continued (fleet 3,023 → 3,140). The seller arm is
now STOCK-STARVED, not machinery-starved — that is the next signature.

## Bars

1. **s01 walkable + roam — PASS.** xXHyupunchXx (pop_0069_s01, char 300119) first in-window trace
   position pay_fild04 (20,165) at 19:04:09 UTC, then 871 distinct cells across pay_fild04 → moc_fild01,
   1,301 move_performed, 207 decides, 23 attacks / 1 kill / 11 loots, sold +6z at 21:08 CET. YuffieFy81
   (pop_0003_s00, char 300006) first position pay_fild04 (20,165) at 19:00:37 UTC, 110 distinct cells
   (pay_fild04 → prontera → moc_fild01 odyssey), 354 moves, 148 decides, 4 attacks / 1 kill / 6 loots.
   No stuck_cell names their old cells (stuck cells logged: prt_fild08 (170,375) cluster, prt_in (172,128)
   dealer-adjacent, prt_fild06 — none at the old sealed pockets).
2. **Rotation — PARTIAL.** Attackers 23/29 (bar ≥15 met). In-window sellers 5 distinct (sora_sama +6,
   xXHyubladeXx +5, PoringMuffin14 +36 over two sales, xXHyupunchXx +6, PipinWalker +3) — below the
   ≥15/29 two-arm shape. Cause is named by the funnel's own gates: admission refusals
   `no_stock_below_zeny_floor` ×588 and `merchant_stock_below_trip_minimum` ×320 — inventories below the
   sell floor after leg-130's 16-seller sell-out, and this window's loot (drops_seen 59 → pickup_success
   18/27) has not rebuilt stock yet. Machinery healthy: 17 sell_contact_authored,
   22 merchant_trip_budget_released, 19 merchant_warp_crossings.
3. **Kills — PASS.** 48 kill_credits vs baseline 42; per-attacker 2.09 (bar ~2.0). 418 attacks authored,
   261 swings sent, 220 damage events, 4,552 damage; base_exp +210, job_exp +91.
4. **Sells / zeny — PASS.** Fleet 3,023 (seed baseline, leg-130) → 3,140 in the char DB (+117).
   Six zenylog rows in-window (+56z across 5 sellers, UTC 19:40–20:30 = CET 20:40–21:30); the remainder
   is unlogged gain (zenylog coverage gap — noted, not investigated). xXHyupunchXx completing
   farm → loot → sell on its reset cell leg is the first full-loop fragment for a reset char.
5. **merchant_trip_budget_released taps — PASS.** 22 taps (0 in leg-130's pre-fix runs).
6. **Receipt close-write — PASS.** See headline; `offline_agents: []`, `passed: null` (known on this build).

## Health

- Final sample: 29/29 online AND standing; 4,151 decisions, min 99 / median 128 / max 260 per agent —
  no decide starvation anywhere (the leg-112/113 saturation shape did not appear).
- 18,131 steps, **0 step_errors**. 34 decide-tick tracebacks, all `PlayingBackendError`
  (known load-dependent class; sessions held, no churn).
- TRANSPORT DOWN 29 = exactly 1 per agent across all 29 (shared transient; rebuild_exhausted 0).
- Chat budget gate active (chat_budget_gated 94–161 per active chatter).
- `seed-zeny.json` was NOT rewritten by the runner at close (unchanged, sum 3,023) — the baseline stays
  coordinator-owned; next leg should compare against DB fleet 3,140 or a refreshed seed.

## Named next signature

**Pickup-to-stock conversion.** The sell arm refused 588 no-stock + 320 below-trip-minimum admissions
while drops_seen 59 produced only 27 pickup attempts and 18 successes. Two levers, in order of leverage:
why ~40% of attempts fail (threat deferral / authored-action collision / expiry — `loot-debug` rows name
each), and why 32 seen drops were never attempted. Feeding stock directly raises the seller count toward
the both-≥15 rotation shape without touching the funnel (its gates and lease release demonstrably work).

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-131-1795632018.json`
- Log: `/tmp/population_leg131.log` (scratch)
- Traces: `.work/runtime/population-live/traces/<persona>.jsonl`
- DB readback: roster 29 rows char_id 300000–300121, zenylog 6 in-window rows, picklog M39/P24/L14/S23
  since 18:40 UTC (M/L carry mob GIDs per the forensics law).
