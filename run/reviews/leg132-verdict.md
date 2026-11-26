# LEG-132 VERDICT (Thu 2026-11-26, [[3,9.0,10.5]] 09:00-10:30 Madrid)

Receipt: run/plain_host_receipts/population-receipt-132-1795678598.json (6.2 MB, written 10:30 during unit lifetime — 9th consecutive close-write proof)
Unit: leg132-runner, launch 08:36:33 CET, natural drain 10:31:39 CET (exit 0, 42min CPU / 1h55m wall, 1.1G peak). NOT killed.
Population: 29/29 personas; steps 21,025; step_errors 0; offline_agents [] at close.

## PREFLIGHT (hard gate, 08:35)
- DECIDE-OK http://192.168.1.156:8091/v1/systemone 0.57s answers=10 (warm bar <3s: PASS)
- :8092 /health 200 (PASS)
- Weekday verified: jeudi = Thursday, Python weekday() 3 = schedule [[3,9.0,10.5]] (PASS)

## BAR VERDICTS

### BAR 1 — pickup conversion live: PARTIAL (success PASS, attempted MISS)
- pickup_success 19/23 = **82.6%** (bar >=70%: PASS; offline reference 83.3% — live == offline)
- drops attempted 23/51 = **45.1%** (bar >=60%: MISS)
- Taps ALL PRESENT and exercised: pickup_deferred_retried 17, pickup_race_expired 52, drop_unattempted_reason 98 — the d0d15c83 deferred-continuation machinery ran live, not just offline.
- Unattempted reasons are dominated by legitimate cedes/consumptions, not lost loot: nearer_agent 51 (drop ceded to the nearest peer — party-shared pickup release), no_floor_item 52 / presence_epoch_expired 52 (drop consumed/vanished), received_takeitem 6 (peer took it). DB corroboration: picklog P delta +19 == receipt pickup_success 19.
- Named-next signature: reconcile the drops_seen denominator against FLEET-level conversion (a nearer_agent cede that succeeds for the peer is a fleet pickup, not a miss). Bar as written (attempted >=60%) cannot distinguish ceded-consumed from lost; suggest fleet-level attempted = (pickup_success + successful_cedes) / drops_seen, or count cedes that end in a peer take receipt.

### BAR 2 — sellers >=8 distinct: PASS (18, 2.25x leg-131)
- zenylog: 18 rows this window, ALL type S, 18 DISTINCT char_ids, spread 08:05:47→09:18:06 (+78z total)
- sell_contact_authored 21 across 10 authors (pump path: YuffieFy81 x5, RinceNyan x4, PipinWalker/KafraMuffin52/xXHyubladeXx/ZenySong x2, misu_drop/TalonWind/xXDoramrinXx/xXLunasongXx x1); the remaining 8 sellers converted via the decide path. Both sell paths live.
- sell_contact_hold 1665 (ring holds), sell_contact_gates 0 (no refusal-naming lines — refusals not the limiter this window)

### BAR 3 — kills vs 48: MISS (41 kill_credits)
- swing_conversion_v1 fleet: attacks_authored 334 (27/29 attackers — participation held), swings_sent 197, damage_events 162, damage 3,505, kill_credits 41, exp +131 base/+64 job, 24 distinct killers.
- 41 vs 48 = -7, same band as legs 127-131 (45/42). Consistent with the documented rotation: 18 sellers (trips to the dealer) displaced combat time — the participation/economy trade-off, not a regression.

### BAR 4 — fleet zeny vs 3,140: PASS (3,218, +78)
- Per-char DB readback matches seed-zeny.json EXACTLY pre-window (c9ed58f9 rebasing confirmed live: all 29 chars at seed values) and grew +78 across 18 chars in-window.
- All zeny movement is type-S (sell); no buys yet — fleet max is PoringMuffin14 831z, still accumulating toward the 1,250z 1204 knife at live prices.

### BAR 5 — receipt close-write 9th consecutive: PASS
- mtime 10:30:xx < unit exit 10:31:39; unit exit 0 (natural duration drain). Kill-safety law held.

## DECIDE HEALTH (window-filtered 07:36→09:32 UTC, error-field split)
- OK 3,749: TRUE p50 **0.97s**, p90 2.52s
- CAPPED (error) 15: p50 15.04s — capped share **0.4%** (best-ever band; leg-128 was 0.7%)
- Uniform: no agent under 20 ok decides. The :8091 slot saturation seen in legs 110-116 did NOT recur this window.

## TRANSPORT / STUCK CELLS
- TRANSPORT DOWN: 29 one-shot events, all recovered in-window (transport_recovery exhausted=false for every agent, attempts <=10; offline_agents [] at close). Recurring ~20-30/window one-shot pattern, absorbed by connect backoff.
- stuck_cell_detected 27 mentions / 2 cells (prt_fild08 (170,373) PipinWalker, (170,375) LunaHunter), both escalated via stuck_cell_escalated after epochs=5 — recovery machinery named and fired; no fleet stall (decisions and dealer trips continued).

## LAUNCH/BOOKKEEPING
- Launched 08:36:33 CET via systemd-run --user --unit=leg132-runner --property=RuntimeMaxSec=7200 (inside the 08:40-08:55 slot; window opened 09:00 with 23 online by 09:02, 29/29 by 09:35).
- Baselines read FRESH pre-window (never stale): picklog M350/P175/L252/S162, zenylog 104, per-char zeny == seed sidecar.
- Deltas: picklog M+23 / P+19 / L+14 / S+21; zenylog +18 (all S).

## NAMED NEXT
1. BAR-1 reconciliation: fleet-level attempted-rate metric (count nearer_agent cedes that end in a peer take receipt as fleet successes) — the 45.1% raw number understates conversion; DB P +19 == success 19 already corroborates.
2. Kills vs economy rotation: with 18 sellers converting, expect kills to rotate DOWN when sell trips rise; bar should be evaluated jointly (kills + conversions) rather than kills alone.
3. Buy leg: fleet zeny +78/window at this rate reaches the 1,250z knife in ~15+ windows for the leading char (831z); consider seeding more sell volume (or a cheaper starter weapon row) if the buy arm should close soon.
