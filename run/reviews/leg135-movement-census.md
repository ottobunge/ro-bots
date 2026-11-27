# Leg-135 movement census — who owns the 40,159 MoveTos

Measurement-only slice (no production behavior change). Window: the receipt's own
bounds `2026-11-27T07:41:15.930288+00:00` -> `2026-11-27T09:30:00.131400+00:00`
(leg-135, 09:00-10:30 CET). Evidence: `.work/runtime/population-live/traces/pop_*.jsonl`
(29 agents), receipt `run/plain_host_receipts/population-receipt-135-1795765275.json`,
attack membership from `run/reviews/drop-coverage-leg135-gates.json`.
Tool: `scripts/movement_census.py` (`robots.app.movement_census`, schema
`movement_census_v1`); machine output in the sibling
`leg135-movement-census.json`. The tool's windowed action census reconciles
EXACTLY with the verdict: 41,071 `action_executed` rows, **40,159 MoveTo**.

## Method (what evidence each classification uses)

Every windowed `action_executed` MoveTo is joined to its `move_performed`
sibling (the next such row within 6 rows; outcome/reason), the carried-forward
sampled `script_step` context (`script`, `nearest_monster_d`; 10 s telemetry
throttle, so context interpolates between samples), and the target's offset
from the standing cell. Classes, in precedence order:

| class | rule |
| --- | --- |
| merchant_trip | sampled script = `MerchantDrive`, OR dispatch reason in {trip_leg, staging_occupied, occupied_west_rerouted, npc_intercepted} |
| reroll_reaim | dispatch reason in {target_unwalkable_rerolled, escalated, stuck_cell_escalated, single_cell_path} |
| approach_engage | farm/grind script context with `nearest_monster_d` set (a visible monster; nearby players do NOT count — `nearby_n` is all actors) |
| roam_patrol | farm/grind context and offset in the scripts' own patrol draw set {(±8,0),(0,±8),(5,5),(-5,-5)} |
| travel_leg | farm/grind context and Chebyshev offset >= 12 (route legs) |
| other | none of the above (the honest remainder; reason histogram in the JSON) |

Arrival = any position-bearing row standing on the exact (map, x, y) target.
**Repeat churn**: an authoring of a (map, target) that was authored earlier in
the window with no arrival at that cell in between. **Abandoned-before-next**:
an authoring whose target saw no arrival before the NEXT authoring (walk
replaced unreached). Empty-view positions interpolate the tracked position
stream (`script_step` rows carry no coordinates).

## The answer: the empty-view roam patrol owns the budget

**roam_patrol = 32,677 of 40,159 MoveTos (81.4%)** — the w59/w60 roam leg of
`FarmScript`/`GrindScript` re-drawing a fresh ±8-cell patrol target every ~2 s
brain tick while the view holds no monster (and usually no player either).

| purpose | actions | share |
| --- | --- | --- |
| roam_patrol | 32,677 | 81.36% |
| merchant_trip | 5,400 | 13.45% |
| approach_engage | 1,747 | 4.35% |
| travel_leg | 166 | 0.41% |
| reroll_reaim | 12 | 0.03% |
| other | 157 | 0.39% |
| **attributed** | | **99.61%** (>= 95% bar met) |

Dispatch layer: 25,549 dispatched, **13,743 held_pending** (authored while the
previous walk was still in flight — never wire-sent), 867 refused, 0 unjoined.
The pacing machinery works; the authoring above it churns.

## The churn that burns the budget

- Repeat churn: **20,858 (51.9%)** of authorings re-author a target the agent
  had already aimed at without ever standing on it.
- **Abandoned-before-next: 39,765 of 40,130 (99.09%)** — effectively every
  authored walk is replaced by the next tick's fresh random draw before the
  agent arrives. One authored MoveTo costs ~1 cell of progress; the other
  ~7 cells of every aim are thrown away, so the agent jitter-walks a pocket
  instead of traversing to mobs.

## Per-agent table (sorted by MoveTo; empty% = share of sampled script_steps with nearby_n=0)

| agent | MoveTo | roam | merch | appr | trav | rr | other | churn% | abandon% | empty% | attacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pop_0069_g01m00 | 2493 | 2488 | 2 | 0 | 2 | 0 | 1 | 44.3 | 100.0 | 100.0 | 0 |
| pop_0069_g00m03 | 2490 | 2468 | 1 | 20 | 1 | 0 | 0 | 47.6 | 100.0 | 99.2 | 0 |
| pop_0069_g03m02 | 2463 | 2441 | 1 | 20 | 0 | 0 | 1 | 55.7 | 100.0 | 99.0 | 0 |
| pop_0069_g04m02 | 2458 | 2440 | 1 | 17 | 0 | 0 | 0 | 44.3 | 100.0 | 99.2 | 0 |
| pop_0069_g02m00 | 2449 | 2405 | 0 | 41 | 1 | 0 | 2 | 43.4 | 100.0 | 98.0 | 0 |
| pop_0069_s01 | 2290 | 2070 | 199 | 21 | 0 | 0 | 0 | 45.5 | 99.8 | 78.1 | 0 |
| pop_0069_g01m02 | 2400 | 2385 | 0 | 15 | 0 | 0 | 0 | 48.3 | 99.9 | 99.4 | 6 |
| pop_0069_s02 | 2305 | 1733 | 527 | 45 | 0 | 0 | 0 | 52.5 | 99.8 | 56.4 | 8 |
| pop_0069_g01m01 | 2280 | 2120 | 128 | 29 | 0 | 0 | 3 | 45.3 | 99.8 | 51.0 | 25 |
| pop_0069_g00m01 | 2271 | 2030 | 197 | 42 | 2 | 0 | 0 | 51.3 | 99.7 | 21.4 | 22 |
| pop_0069_s03 | 2258 | 1985 | 118 | 91 | 55 | 0 | 9 | 55.9 | 100.0 | 70.7 | 5 |
| pop_0069_g03m00 | 2240 | 1910 | 297 | 27 | 3 | 0 | 3 | 53.4 | 99.7 | 61.1 | 23 |
| pop_0069_g03m03 | 2097 | 1795 | 71 | 193 | 36 | 2 | 0 | 50.6 | 99.9 | 52.3 | 4 |
| pop_0069_g00m02 | 1685 | 0 | 1554 | 131 | 0 | 0 | 0 | 90.3 | 96.9 | 20.7 | 78 |
| pop_0069_g04m01 | 1586 | 976 | 241 | 317 | 32 | 1 | 19 | 52.0 | 97.8 | 33.1 | 52 |
| pop_0003_g01m02 | 1519 | 566 | 386 | 513 | 2 | 0 | 52 | 58.9 | 97.8 | 32.8 | 38 |
| pop_0069_g02m02 | 1286 | 524 | 651 | 104 | 1 | 0 | 6 | 65.9 | 96.6 | 33.6 | 15 |
| pop_0069_g03m01 | 947 | 186 | 617 | 121 | 19 | 0 | 4 | 73.5 | 94.1 | 21.5 | 17 |
| pop_0069_g00m00 | 447 | 402 | 42 | 0 | 2 | 0 | 1 | 40.5 | 98.4 | 0.0 | 0 |
| pop_0069_g02m01 | 344 | 287 | 45 | 0 | 3 | 0 | 9 | 50.9 | 95.0 | 0.0 | 0 |
| pop_0069_g04m03 | 306 | 264 | 33 | 0 | 1 | 1 | 7 | 45.4 | 94.8 | 0.0 | 0 |
| pop_0069_s00 | 295 | 222 | 61 | 0 | 2 | 1 | 9 | 46.1 | 96.9 | 0.0 | 0 |
| pop_0003_g00m01 | 254 | 219 | 29 | 0 | 1 | 1 | 4 | 33.5 | 97.2 | 0.0 | 0 |
| pop_0003_g00m02 | 200 | 149 | 40 | 0 | 1 | 1 | 9 | 51.0 | 93.0 | 0.0 | 0 |
| pop_0003_g01m01 | 189 | 145 | 39 | 0 | 0 | 1 | 4 | 38.1 | 95.7 | 0.0 | 0 |
| pop_0003_g00m00 | 188 | 150 | 33 | 0 | 1 | 2 | 2 | 39.9 | 97.3 | 0.2 | 0 |
| pop_0003_s00 | 188 | 148 | 36 | 0 | 0 | 0 | 4 | 43.6 | 93.0 | 0.0 | 0 |
| pop_0069_g04m00 | 161 | 125 | 29 | 0 | 1 | 0 | 6 | 36.6 | 92.5 | 0.0 | 0 |
| pop_0003_g01m00 | 70 | 44 | 22 | 0 | 0 | 2 | 2 | 38.6 | 92.8 | 0.0 | 0 |

(attacks column from the gates file's `attacks_authored` for cohort membership;
the verdict's action census counts 221 Attack rows — different counters, do not
mix.)

## The empty-view cohort's positions

Fleet-wide, 39.15% of sampled script_steps (5,466/13,960) carry `nearby_n=0`:
no monster AND no player in view. Where they stood:

- **prt_fild08: 4,800 samples (87.8%)** — a static corner pocket around
  (210,365), cells (204-233, 343-371), roughly 35-45 cells NE of the
  field-entry cell (170,378). The top movers' top cells are all inside it:
  g01m00 (230,367)/(230,368)/(233,368); g00m03 (204,358)/(210,365)/(193,347);
  g03m02 (210,365)/(205,362)/(211,366). The ±8 jitter re-draws never carry the
  agent out of the pocket because every authoring is abandoned at ~1 cell.
- **prt_fild06 (36,211): 387 samples** — essentially ONE agent parked:
  pop_0003_g01m02 (72 samples at that cell; an ATTACKER with 513 approach
  actions, standing mobless a third of its window).
- **prontera: 278 samples** across the dealer-adjacent group (the bottom-ten
  walkers: <= 450 MoveTos each, 0.0-0.2% empty view — players around, and
  MerchantDrive shares the ticks).
- prt_fild05: 1 sample (transit).

The 17-agent zero-attack cohort owns 17,285 MoveTos (43.0%); its top five
alone (g01m00, g00m03, g03m02, g04m02, g02m00 = 12,353 MoveTos) sit at
98-100% empty view and 97.5-99.8% roam class. The 12 attacking agents' own
movement is ALSO 61-99% roam class — the roam churn taxes everyone; the
attackers simply had co-located mobs in the pocket's edge cases.

## Dominant class, named seam

**Dominant: per-tick empty-view roam patrol authoring in the farm/grind
scripts.** Per-agent evidence above; fleet evidence: 81.4% of MoveTos,
99.09% abandoned-before-next, 39.15% empty-view samples with a static pocket.

Authoring seam (the code that emits the churn):

- `src/robots/app/scripts.py:1523-1531` — `FarmScript._farm_step` roam leg;
  line 1527 `dx, dy = self._roam_rng.choice(((8, 0), (-8, 0), (0, 8), (0, -8), (5, 5), (-5, -5)))`
  and lines 1528-1530 `ScriptOutcome((MoveTo(max(0, state.x + dx), max(0, state.y + dy)),), ACTIVE)`.
  The comment names the intent ("an empty view must not stand still") — the
  leg succeeded at walking and failed at ARRIVING anywhere.
- Twin: `src/robots/app/scripts.py:1370-1380` — `GrindScript._roam_step`,
  same draw at line 1376 (random module, not the plan-seeded rng).
- The persistent-target precedent the legs already have but only use for
  spawn clusters: `src/robots/app/scripts.py:1521-1522`
  (`state.farm_roam_target`, supplied by `playing_runtime.py:1014`
  `_spawn_roam_target`, which returns None once the agent is within 12 cells
  of a cluster — inside the pocket this path is None every tick, so the
  ±8 fallback re-draws).
- Cadence context (NOT the defect): the brain steps the active script every
  tick — `agent_runtime.py:1115` `_advance_script`, `agent_runtime.py:1141-1142`
  (`step_script` + `execute_actions`); the runtime's pending-walk pacing that
  correctly throttles sends is `playing_runtime.py:5158` `_await_pending`.

## Recommended fix class (ONE; not implemented here)

**Persistent patrol waypoint in the roam legs — script-layer fix at
`scripts.py:1523-1531` (+ twin `1370-1380`).** Hold the currently-aimed roam
target in the script instance (the `farm_roam_target` precedent) and re-author
THE SAME cell each tick until one of: arrival (tracked position on the target),
the runtime's no-progress release (`walk_released_no_progress`), or a bounded
tick/time horizon; only then draw a fresh offset. Keep the target offset
ANCHORED AT ITS ORIGINAL AIM CELL (absolute cell, not `state.x + dx` re-drawn
from the drifted position), otherwise the waypoint walks away with the agent.

Why script-layer, not runtime-layer:

1. Ownership: scripts own mobility/engagement; the runtime owns pacing and
   real pickups (working agreement, and `_loot_first` precedent). The runtime's
   pacing is already correct — 63.6% of authorings dispatched exactly one path
   step each, and 13,743 held_pending were honestly withheld. Adding a
   target-stickiness layer in `playing_runtime` would fight the script's
   explicit per-tick authoring contract and double-own the same decision.
2. The authoring contract is the defect: the roam legs are stateless-per-tick
   by construction (`_roam_rng.choice` every step), so they cannot intend a
   destination. A script-local waypoint restores intent without touching the
   dispatch machinery, the leg-28 direct sends, or the reroll escalator.
3. It generalizes an existing, tested seam (`state.farm_roam_target`,
   scripts.py:1521) instead of inventing a new one.

Expected effect (testable next leg): authored-MoveTo volume drops by roughly
the abandonment factor (each aim either arrives or is released by the runtime
instead of being re-drawn every 2 s), displacement per agent rises, and the
pocket-bound agents get a chance to leave the mobless corner — the direct
lever on bars 1-2 (attackers, kills) named in the verdict. Gate it with the
existing move-gate instruments (`walk_released_no_progress(step)` counts) plus
a census re-run: roam share should fall while travel/approach shares rise.

## Limits

- `script_step` context is 10 s sampled telemetry carried forward between
  samples; the 157 'other' rows and any approach/travel boundary calls inherit
  that resolution. The class rules are deterministic from rows, but view state
  between samples is interpolated, not observed.
- Arrival = any position-bearing row on the exact target cell, so a
  pass-through counts as an arrival; standing-on-target re-authors (merchant
  engage, e.g. pop_0069_g03m01's (0,0) x42) are honestly NOT churn.
- `held_pending` authorings are classified by purpose but never wire-sent.
- MerchantDrive context leans on sampled rows; only 544 of the 5,400
  merchant_trip actions carry a merchant dispatch reason — the rest inherit
  the sampled MerchantDrive context (same lower-bound caveat as the verdict's
  gate-tap counts).
