# Leg 125 verdict — arrival-swing validation (2026-11-24, Tue 14:00-15:30 Madrid)

Receipt: `population-receipt-125-1795523969.json` (close-write verified on disk at
15:32:40 CET while `leg125-runner` was still active — the ad3d2ce0 kill-safety
contract held again). Runner self-exit window 15:44, unit hard-kill 15:59
(RuntimeMaxSec 8400). HEAD at launch `a99ef6bf`.

## Runner health

- 29/29 online the entire window (`offline_agents: []`), 16,568 steps, **0 step_errors**.
- Transport rebuilds: 2 agents attempted (5 and 3 attempts), **none exhausted**.
- Decide health (traces, window UTC 13:00-14:30): 9,546 `decide_response` rows,
  **26.7 % capped**, true-success **p50 13.97 s** (leg-124: 22.1 % / 13.78 s) —
  the same load-dependent saturation band, no regression.

## Bars

| Bar | Result | Verdict |
|---|---|---|
| 1. >= 20/29 agents with >= 1 authored attack | **10/29** (290 authored, 127 swings, 2,102 damage) | **NOT MET** (leg-124: 8/29) |
| 2. kills > 16 and drops/pickups > 0 | kills **23** (> 16), drops_seen **18**, pickup_success **0** (2 attempts) | kills+drops **MET**, pickups **NOT** |
| 3. sell conversions continuing | fleet zeny 2,436 -> **2,457** (+21); zenylog 36 -> **39** (+3 S-rows) | **MET** |
| 4. receipt close-write verified | on disk 15:32:40, unit still active | **MET** |

Bar-3 detail: exactly 3 in-window sell conversions, zero purchases —
KafraMuffin52 0 -> 8 (+8), NyxNyan18 42 -> 48 (+6), xXLunasongXx 145 -> 152 (+7).
The zenylog S-rows (13:09:55 / 13:11:14 / 13:17:49 UTC = 14:09-14:17 CET) match the
per-char deltas row-for-row. `seed-zeny.json` advanced to the post-window fleet 2,457
(zeny CHANGED).

## The arrival-swing seam (223827d2) — verdict

**The seam works where it engaged; it did not widen participation.**

- Funnel: 290 attacks authored -> 127 swings -> 119 damage events -> 2,102 damage ->
  **23 kill credits** (leg-124: 16 kills) -> 110 base / 45 job XP.
- `pending_walk` refusals **373 -> 212**; `arrival_swing_minted` fired on the engaged
  agents (tap lives in the receipt's `swing_conversion_v1` telemetry, not the runner log —
  SwingTelemetry is a receipt-side ring buffer; only `sell_contact_authored` is a log line).
- attack_refusals (fleet): pending_walk 212, cooldown 56, disengage_active 34,
  target_not_visible 5, dead 4.

**Participation stayed group-shaped, now harder**: attackers are 6/6 pop_0003 members
plus 4 of 22 pop_0069 (g01m00 11 / g01m01 8 / g01m02 4 / g00m02 3 authored). The 19
zero-attack agents are 17 pop_0069 (g02/g03/g04 entirely + all 4 solos) + pop_0003_g01m01
+ pop_0069_g00m01. pop_0069's farm-plan target quality — leg-124's "secondary" — is now
the **dominant** limiter: those agents never author an attack at all (0 authored, so no
refusals either; the refusal table only exists on engaged agents).

## Second signature: pickup regression

18 drops seen by 8 agents, but **pickup_attempts 2 / pickup_success 0** (leg-124: 12
drops, 3 pickups). The loot-ownership -> pickup chain (eefb95c4 era) did not convert any
ground drop to inventory this window. No zeny consequence yet (sells came from carried
stock admission), but the in-window-loot -> sell link (205408c8) is starved by it.

## DB readback (docker run sidecar on ro-bots-e2e_default; secret inside container only)

- zenylog 39 rows (baseline 36, +3 this window)
- picklog M 135 -> 155 (+20), P 65 -> 67, L 67 -> 100, S 59 -> 63
- Close positions: 25 of 29 population on prt_fild08 grounds, PipinWalker + RinceNyan on
  prt_fild06, NyxSong + PoringMuffin14 in prontera, xXHyupunchXx still pay_fild04.

## Decisions taken

- `seed-zeny.json` refreshed to the post-leg-125 fleet baseline (2,457) — zeny CHANGED.
- Receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit, explicit paths.

## Named next signature

**pop_0069 farm-plan target quality — now the primary participation limiter.** The
arrival-swing seam closed the walk->swing gap for agents whose plans put them on mobs
(290 authored, 23 kills), but 17 of 19 non-attacking agents are pop_0069, and their
zero-authored shape (not refusal-shaped) says their plans never target reachable species.
Lever: audit pop_0069's authored plans/spawn targets against prt_fild08 ground truth
(species overlap + distances), the same way the group-0003 cluster's plans were built.
Secondary: the pickup regression (2 attempts / 0 success over 18 drops) — re-arm the
loot-ownership admission checks from the eefb95c4 era before the in-window-loot sell
link can compound.
