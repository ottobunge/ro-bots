# Leg-135 verdict — Fri 2026-11-27, window 09:00-10:30 CET (schedule [[4,9.0,10.5]])

Base: main `4f24a271`, schedule staged `3141875d`. Shepherd: T3 delegate task (leg-135 brief).
Receipt: `run/plain_host_receipts/population-receipt-135-1795765275.json` (6.1 MB, written 10:30).
Gates evidence: `run/reviews/drop-coverage-leg135-gates.json`.

## Preflight + launch

- PREFLIGHT PASS 08:32 CET: decide probe DECIDE-OK 0.47 s / 0.53 s warm, answers=10 on
  `http://192.168.1.156:8091/v1/systemone`; :8091 and :8092 `/health` 200.
- Launch 08:41:30 CET via `systemd-run --user --unit=leg135-runner --property=RuntimeMaxSec=7200`
  with the exact runner template. Note: the /tmp-launcher-script form died 203/EXEC ("Failed to
  execute ... No such file or directory" — /tmp is not executable for the user manager even though
  it is visible); the leg-134 inline `bash -c` form is the proven pattern and is what launched.
- Pre-window DB double-read stable: fleet 3,819z (29 personas), zenylog 163 S-rows, picklog 1,398
  (M 483 / P 291 / L 370 / S 254).

## Mid-window states

- 09:16:23 — online 29/29; transport_down 29 = exactly 1/agent (login burst, all rebuilt);
  backend errors frozen at 26 since the burst; 19 distinct positions; decides up to ~45/agent;
  sell funnel active (merchant taps 1,059).
- 10:01:25 — online 29/29 (t=4798 s); decides min 1 / max 229; 19 distinct positions; td 29
  (no new), backend errors 43 (stable); funnel cycling: dealer_counter_yield 10 = counter_released 10.
- One transient at 10:16 (27/29) recovered by 10:21 without any new TRANSPORT DOWN line.

## Close

- Window held full 90 min, 29/29 online to 10:30. Receipt written 10:30 while `leg135-runner`
  was still active; unit drained itself after `DONE: steps 21374, errors 0` — kill-safety law
  held, **close-write 12th consecutive**.
- Receipt window figure: **steps 20,246, step_errors 0**, offline_agents [], samples 215.
  (DONE figure 21,374 is inclusive of the post-close drain, per the forensics law.)
- Close DB double-read stable: fleet **3,973z**, zenylog 175 S-rows (+12), picklog 1,458
  (+60: M +20 / P +15 / L +4 / S +21).

## Decide health (error-field split)

3,946 windowed `decide_response` rows across all 29 agents. Capped (rows carrying `error`):
**24 = 0.6%** of attempts (`PlayingBackendError`). TRUE success p50 **1.00 s** (p95 5.86 s,
max 13.93 s); naive all-attempts p50 1.01 s. Decide cadence 105-262 per agent. The backend is
exonerated for every soft number in this window.

## Transport / stuck cells

- TRANSPORT DOWN: 29 lines in the login burst, distribution **exactly 1 per agent** — the
  documented shared transient; every agent rebuilt (transport_recovery entries read attempts 0,
  exhausted 0 — no receipt-side failure flag). No mid-window repeats.
- Stuck cells: one agent (pop_0069_g03m00) parked dealer-adjacent (172,129) with
  `stuck_cell_exhausted` ×8 alongside `merchant_post_trip_return` + `counter_not_selected`
  gates — a mild single-agent recurrence of the dealer-adjacent hold shape; fleet-wide
  stuck_cell_reset counts small and bounded.

## Bars

| # | Bar | Result | Verdict |
| --- | --- | --- | --- |
| 1 | BOTH-ARM: attackers ≥15/29 AND sellers ≥12/29 | attackers **12/29**, sellers **11/29** | **FAIL** (leg-134: 22/16) |
| 2 | kills ≥41 | **19** kill_credits | **FAIL** (floor; leg-134 peak 73) |
| 3 | fleet zeny vs 3,819 | **3,973 (+154)**, 11 net-positive | **PASS** |
| 4 | classifier LIVE: UNKNOWN <50% AND fleet-attempted ≥70% | UNKNOWN **1/7 = 14.3%**; fleet-attempted **21/27 = 77.8%** | **PASS** (first live window) |
| 5 | receipt close-write 12th consecutive | landed 10:30 with unit active | **PASS** |

**Overall: 3/5 bars PASS (3, 4, 5); bars 1-2 FAIL.** Combat participation and the kill floor
regressed hard against leg-134 (12 vs 22 attackers; 19 vs 73 kills; per-attacker 1.58 vs 3.3).

## Where the budget went (window action census, 41,071 `action_executed` rows)

- **MoveTo 40,159 (97.8%)**; GuildInvite 293; Attack 221; Say 133; Rest 116; Loot 62;
  InviteToParty 27; PartyChat 22; FoundGuild 13; TalkToNpc 7; NpcShopSellOpen 7;
  NpcShopSell 6; WhisperTo 5.
- Chat is NOT the thief this leg: only 3 agents exceeded 10 chat actions (160 chat actions
  total) — the leg-127 chat-storm shape did not recur.
- Movement dominates: ~1,385 MoveTos per agent; merchant-gate churn heavy (sell_contact_hold
  taps 1,382, merchant_trip_budget_released 29, dealer_counter_yield 13 = counter_released 27
  by close); final samples show `nearby_n` 0 fleet-wide — agents stood off-spawn while the
  window's walk budget ran.
- The sell funnel itself converted: 12 in-window zenylog S-rows by 11 sellers (CET 09:02-10:27;
  top rince_ko 55 + 12), with counter handovers cycling cleanly (13 yields, 27 releases).

## Named-next signature

**Movement-budget dominance with empty combat views.** A 17-agent zero-attack cohort whose
samples are filled with merchant admission / trip-cooldown / post-trip-return gates and roam
patrol walks, standing off-spawn (nearby_n 0), while 12 agents carried all 221 attacks and
19 kills. Backend exonerated (0.6% capped). Next readout: split MoveTo purpose per agent
(roam patrol vs merchant trip legs vs approach walks) from the traces to learn WHICH walker
owns the 40k budget — do NOT open another targeting / chat / combat-dispatch slice before
the movement census routes it.

## Buy-leg watch

PoringMuffin14 967 → **970z** (+3, one sale at 08:03:48 UTC) — still **280z short** of the
1,250z knife (1204). Small-sale accumulation is too slow at this cadence; the purchaser-pooling
design question stays flagged for Otto.

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-135-1795765275.json`
- Gates: `run/reviews/drop-coverage-leg135-gates.json` (scripts/swing_funnel.py over
  `.work/runtime/population-live/traces/*.jsonl`, window 2026-11-27T07:41:15.930288+00:00 →
  2026-11-27T09:30:00.131400+00:00, the receipt's own bounds)
- Runner log: `/tmp/population_leg135.log` (DONE 21,374 steps, 0 errors)
- Classifier replay pattern: mirrors `run/reviews/drop-coverage-leg134-gates.{md,json}`
