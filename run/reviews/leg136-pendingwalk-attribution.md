# Leg-136 pending_walk attribution — the verdict's named-next readout

Measurement-only slice (no production behavior change). Routes the leg-136
verdict's question: WHERE do the 1,427 `pending_walk` gates come from, and
WHICH fix shape does the evidence support.

- Window: 2026-11-27T19:00:00Z → 20:31:00Z (leg-136 schedule 20.0-21.5 CET)
- Sources: `.work/runtime/population-live/traces/pop_*.jsonl` +
  `run/plain_host_receipts/population-receipt-136-1795804324.json`
- Tool: `scripts/pendingwalk_attribution.py` → `src/robots/app/pendingwalk_attribution.py`
  (21 unit tests on synthetic rows: `tests/test_pendingwalk_attribution.py`)
- JSON evidence: `leg136-pendingwalk-attribution.json` (per-agent, per-bucket)

## Census reconciliation

Receipt `attack_gates.pending_walk` **1,427** across 9 agents — matches the
verdict's gate census exactly. Every one of the 1,427 gates is classified to a
holding-walk origin (100% attributed; acceptance bar ≥90%):

| origin | gates | share |
| --- | --- | --- |
| `attack_deferred_behind_field_route` | 467 | 32.7% |
| `attack_deferred_behind_other_walk` (merchant/loot/stuck) | 368 | 25.8% |
| `attack_deferred_behind_movement_walk` (receipt-proven step/direct holds) | 307 | 21.5% |
| `attack_deferred_behind_roam_hold` | 228 | 16.0% |
| `attack_deferred_behind_own_approach` (self-paced, benign) | 57 | 4.0% |
| unattributed | 0 | 0.0% |

**96.0% of the loss sits behind NON-COMBAT movement walks.** Only 4.0% is the
combat pipeline's own approach pacing (which resolves on arrival and needs no
fix).

## Per-agent: pending_walk vs roam-waypoint cadence

| agent | pw | field | roam | other | move | appr | mints | exec | swings | fa dis/blk | field auth | disp walks (reissues) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pop_0069_g02m02 | 616 | 251 | 106 | 102 | 133 | 24 | 783 | 49 | 37 | 54/114 | 682 | 403 (211) |
| pop_0069_g04m01 | 475 | 99 | 31 | 229 | 100 | 16 | 547 | 42 | 34 | 38/35 | 713 | 372 (240) |
| pop_0003_g01m02 | 210 | 89 | 51 | 33 | 29 | 8 | 667 | 63 | 45 | 98/34 | 596 | 760 (505) |
| pop_0069_s01 | 47 | 9 | 12 | 2 | 23 | 1 | 80 | 7 | 6 | 7/2 | 202 | 882 (718) |
| pop_0069_g02m00 | 32 | 0 | 22 | 0 | 3 | 7 | 435 | 16 | 13 | 60/18 | 204 | 1438 (1099) |
| pop_0069_g01m01 | 29 | 10 | 1 | 0 | 17 | 1 | 191 | 23 | 22 | 20/4 | 136 | 1469 (1173) |
| pop_0069_g03m02 | 8 | 7 | 1 | 0 | 0 | 0 | 74 | 4 | 3 | 11/1 | 134 | 1306 (1042) |
| pop_0069_g01m00 | 6 | 2 | 1 | 2 | 1 | 0 | 50 | 4 | 3 | 4/0 | 412 | 551 (449) |
| pop_0069_s02 | 4 | 0 | 3 | 0 | 1 | 0 | 172 | 32 | 33 | 14/0 | 0 | 1442 (1171) |

Reading: three agents own 91.2% of the gates (g02m02, g04m01, g01m02), and
they are exactly the agents whose goal route runs through mob-dense ground —
combat intent churn (mints) is an order of magnitude above executed attacks
(2,729 mints → 240 executed attack rows across the nine), while
`farm_approach` authorships are refused `await_pending` at 37.6% fleet-wide
(213/566; g02m02: 114/168 = 68%). The pure-roam cadence agents (s02, g02m00,
g01m01: >1,100 held re-aims each) barely gate — the hold alone does not gate;
the hold CONTESTED by combat authorship does.

## Gate sites

The 137 per-gate-timestamped trace rows split: **52 authored-attack refusals**
(`_attack` limb) and **85 pump-swing refusals** (`_continue_farm_swing` limb,
which keys on `view.arrival_confirmed`, not on `_pending` — it too defers
behind whatever walk holds the slot). Both limbs feed the same fix.

## The three mechanisms (trace-proven)

1. **Field-route legs hold the slot.** The goal-travel pump dispatches through
   `_perform_move` directly (playing_runtime.py:1805) — its only trace
   evidence is the `goal_field_routed` tap — and re-aims every 2 s pump tick
   (farm_combat.py:12) with 1 s no-progress re-sends. The combat approach to
   the same cell is refused `await_pending`, then the in-range attack is
   refused `pending_walk`, every cycle (traced chain 19:04:17-19:04:22,
   pop_0069_g02m02).
2. **Phantom trip legs hold the slot.** After the dealer→field warp the
   admitted trip intent keeps re-dispatching `trip_leg` walks that
   no-progress-release every ~1 s: `walk_released_no_progress(trip_leg)` ×3
   per 30 s bucket with `await_pending` ×4 and exactly 10 pending_walk gates
   per bucket for 21 consecutive buckets (pop_0069_g04m01 19:30-20:19, agent
   standing at the field spawn). Merchant-class holds: 229 gates on g04m01.
3. **Roam patrol holds gate where combat contests them.** The `_RoamWaypoint`
   hold (scripts.py:1345-1394) is proven innocent where uncontested (the
   pure-roam agents above) and guilty in contest windows — 228 gates.

The script-side `displace()` (scripts.py:1365-1367, called on every engage
path: scripts.py:1423-1446) only clears the NEXT roam aim; it never releases
the runtime's in-flight `_pending` walk. That is the gap: nothing in the
runtime yields the slot to combat.

## ROUTING DECISION: fix shape (c) — both, as ONE displacement rule

**When combat authorship arrives (authored Attack at `_attack`, or the farm
pump's approach MoveTo at `_continue_farm_approach`/`_move_gate`) and the
pending slot is held by a NON-COMBAT walk, release the slot exactly as
`_await_pending` already does on no-progress (playing_runtime.py:5183-5195)
and note `walk_displaced_for_combat(<origin>)`.**

- Deciding seams: `_attack` gate playing_runtime.py:1625-1627; pump swing gate
  playing_runtime.py:1979-1983; intent-mint deferral playing_runtime.py:1703-1705;
  `_move_gate` await_pending playing_runtime.py:3575-3577 (approach dispatch
  playing_runtime.py:2009); field-route dispatch playing_runtime.py:1805;
  merchant trip gate playing_runtime.py:4663; no-progress release
  playing_runtime.py:5183-5195; `displace()` scripts.py:1365-1367.
- **Not preempt-only (a):** the 213 blocked approaches (37.6%) are
  out-of-range engagements — no Attack is ever authored to preempt with, so
  those engagements stay dead.
- **Not budget-priority-only (b):** the in-range authored attacks (mobs
  already adjacent — 52/137 traced gates are this limb) never author an
  approach; approach priority never touches their loss.
- One rule covers both limbs and the phantom-trip loop (its holds are
  non-combat by origin class).

## Expected leg-137 live signature

- `pending_walk` collapses from 1,427 toward the self-paced floor (order 100);
  `attack_deferred_behind_own_approach` becomes the dominant origin class.
- `farm_approach` blocked share drops from 213/566 (37.6%) to <10%.
- Attack funnel: ~379 authored → ~370 executed (from 299), swings 245 → ~330;
  `cooldown` overtakes `pending_walk` as the top gate.
- Intent churn (`farm_target_authored` 3,436) drops toward ~1-2 per
  engagement; kills rise from 41.
- New census counter `walk_displaced_for_combat` names each displaced hold
  class; its per-class counts should approximate the leg-136
  field+roam+other+movement mass (1,370).

## No production change

This slice adds only: `src/robots/app/pendingwalk_attribution.py`,
`scripts/pendingwalk_attribution.py`, `tests/test_pendingwalk_attribution.py`,
and this report. No runtime/script file is touched.
