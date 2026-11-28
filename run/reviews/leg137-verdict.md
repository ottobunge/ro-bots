# Leg-137 verdict — Sat 2026-11-28, window 09:00-10:30 CET (schedule [[5,9.0,10.5]] all 29)

**Overall: 3/5 bars PASS — the two combat-displacement fix bars FAILED.** Bars (c) kills,
(d) BOTH-ARM, (e) close-write passed; (a) pending_walk and (b) farm_approach blocked share
regressed vs leg-136. The displacement rule is live and firing at scale, but its expected
signature (pending_walk -> order 100, fa-blocked <10%) did not materialize: released slots
are re-contested by instant non-combat re-authoring before the swing lands.

Base: main `598f3e28` — the leg-136 attribution fix (t3/combat-displacement, merge
"combat displacement (leg-136 attribution fix)") WAS merged to main before the 08:32 wake
(local == origin/main at wake), so leg-137 tested the fix live and bars (a)/(b) were
bar-relevant. Shepherd: T3 subagent, leg-137 brief.
Receipt: `run/plain_host_receipts/population-receipt-137-1795851617.json` (6.7 MB, mtime 10:30).

## Preflight + launch

- PREFLIGHT PASS: `date '+%a'` = sab (Sat, weekday 5 = schedule index 5) at 08:32:08 CET;
  decide probe **DECIDE-OK 2.34 s warm, answers=10** (<3 s bar) on
  `http://192.168.1.156:8091/v1/systemone`; :8092 `/health` 200.
- Pre-window DB double-read: fleet **4,618z** exact (31 rows: 29 personas + 2 zero-z FX
  fixture chars).
- Launch **08:40:13 CET** — inside the 08:40-08:55 band; launch-timing law honored
  (launch + 6900 s = 10:35:13 >= close 10:30 + drain, RuntimeMaxSec ceiling 10:40:13).
  Proven inline `systemd-run --user --unit=leg137-runner` form. Log within 25 s: all 29
  personas rostered, `CLOCK: (5, 8.666)`, 15 playing groups `((5, 9.0, 10.5),)`, configured True.

## Mid-window

- 09:17 (+17 min past open): **26/29 online, 904 decides** — login-burst transport transient
  (27 TRANSPORT lines, documented ~1/agent pattern).
- 10:00: **29/29 online, 3,220 decides** — full recovery with 30 min to close.

## Close

- Receipt written **10:30:17 CET while `leg137-runner` was still active** (ceiling 10:40:13) —
  receipt kill-safety law held, **close-write 14th consecutive** (streak 124->137).
- DONE line: `steps 17821, errors 0`. Receipt figure: **steps 16,901, step_errors 0**,
  215 samples — the post-close drain advanced the runner counter by 920 steps; per the
  forensics law the receipt figure is the window figure (they differ this leg, unlike leg-136).
- Unit drained and terminated ITSELF (inactive by 10:39:06, before RuntimeMaxSec). Never killed.
- offline at close: `pop_0069_g00m00` (1/29). transport_recovery: attempts 8-23 fleet-wide,
  **exhausted: false** for all 29.
- Close DB double-read: fleet **4,618 -> 4,935 (+317)**; windowed zenylog (UTC-stamped,
  08:00->09:31 UTC): **S 31 rows / 20 seller chars / 317z — S-sum 317 = fleet delta exact
  reconciliation** (all of this leg's zeny gain is sells). picklog **M 55 (-55) / P 43 (+43) /
  L 33 (+5) / S 44 (-50)**.

## Bars

| # | Bar | Result | Verdict |
| --- | --- | --- | --- |
| 1 | pending_walk < 300 (leg-136: 1,427) | receipt census **2,092** | **FAIL** (+46% vs leg-136; projection was order 100) |
| 2 | farm_approach blocked share < 10% (leg-136: 37.6%) | **395/927 = 42.6%** refused `await_pending` | **FAIL** (+5.0 pp) |
| 3 | kills vs 41 floor | **56 kill_credits**, 23 agents credited | **PASS** (+15 over floor, +37% vs leg-136) |
| 4 | BOTH-ARM attackers >=15 AND sellers >=10 | attackers **27/29** (10 with >=15 authored), sellers **20/29** | **PASS** (leg-136: 17/12) |
| 5 | receipt close-write 14th consecutive | landed 10:30:17 with unit active | **PASS** |

## Fix readout (why the leg exists — the displacement verdict)

- **The rule is firing.** Receipt census `walk_displaced_for_combat` **1,846** (step 1,464,
  trip_arrival_confirmation 280, stuck_cell_detected 36, escalated 30, field_route 16,
  rerolled 14, trip_leg 6); 148 traced. That is the same order as the leg-136 non-combat
  mass it was built to release (1,370), +35%.
- **But the release does not transfer the slot.** pending_walk census rose 1,427 -> 2,092 and
  await_pending refusal share rose 37.6% -> 42.6% (213/566 -> 395/927). Displaced non-combat
  walks RE-AUTHOR immediately — `field_authorships` 9,090 window-wide (top funnel:
  g04m01 field 621 / script_walks_blocked 464 / held_reissues 414) — so the freed slot is
  re-filled before the swing lands. The census counts heartbeat-weighted WAITS, and churn
  multiplies waits: traced `attack_refused` events are only **572** (pending_walk 151 = 26%,
  no_survivability 224, cooldown 140, disengage_active 34, target_not_visible 20, dead 2,
  out_of_melee_range 1).
- **Origin shift matches one leg-136 prediction:** `attack_deferred_behind_own_approach`
  57 -> **734** (4.0% -> 35.1%, now the dominant class, as projected); field_route 467 -> 678;
  roam_hold 228 -> 207; other_walk 368 -> 190; movement_walk 307 -> 166; unattributed 0 -> 117
  (5.6% — classification still >=90% bar, but the new combat_displacement taps close holds
  mid-flight and leave 117 gates unclosed for the tool).
- **Throughput vs census paradox:** kills 41 -> 56, attackers 17 -> 27, sellers 12 -> 20,
  fleet zeny +317 exact — the combat ECONOMY improved while every gate counter worsened.
  Displacement converts some waits into swings at the margin (swings 245 -> 263, below the
  ~330 projection; attacks authored 418, executed 273) but also multiplies re-author churn.
- **Mechanism conclusion:** displacement-as-instant-release churns the slot; it does not
  reserve it for the attack. The leg-136 A/B replay predicted pending_walk -> 0 under the
  rule; live, the surrounding re-author loop (9,090 field authorships) eats the release.

## Decide health (error-field split)

4,661 windowed `decide_response` rows across all 29 agents. Capped/error rows: **30 = 0.64%**
(all `PlayingBackendError: real inference request failed`, p50 15.09 s); **capped class 0
(0.00%** vs leg-136's 0.93%)**. TRUE success p50 **1.20 s** (p90 3.62 s). Backend exonerated
for every soft number in this window.

## Watch items (not bars)

- Cooldown did **NOT** overtake pending_walk as top census attack gate (2,092 vs 1,541;
  traced events 151 vs 140).
- Chat share **DOWN**: 68 PartyChat actions, **1 agent >10** (leg-136: 250 actions, 10 agents >10).
- Purchaser-pooling stays flagged for Otto (no buy leg observed; top seller 98z).
- Bar-design caveat for next leg: the pending_walk bar was measured on the receipt census
  (heartbeat-weighted waits), which diverges from traced refusal events (2,092 vs 151) once
  displacement churns re-authors. Define next leg's bar explicitly on one method.

## Named-next

**Make displacement sticky: lease the slot until swing.** Extend the displacement rule from
"release at authorship" to a short lease — the displaced walk backs off until the authoring
combat swings (or a timeout), reusing the disengage-step swing-lease shape; without it the
instant release is re-contested by 9,090 window field authorships. Secondary: close the
tool's 117 unattributed gates (displacement-tap closure path), and pin next leg's
pending_walk bar to traced events (151 tonight) or the census explicitly.

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-137-1795851617.json`
- Attribution: `run/reviews/leg137-pendingwalk-attribution.json` (windowed
  2026-11-28T08:00:00 -> 09:31:00 UTC, bucket-origin 07:40:13 UTC, mirroring the leg-136
  reproduce line)
- Runner log: `/tmp/population_leg137.log` (DONE 17,821 steps, 0 errors; drain +920)
- Pre/close DB reads: `/tmp/leg137_prefleet.txt`, `/tmp/leg137_close.txt` (uncommitted, /tmp
  only — no secrets; db-root secret read inside the container only)
