# Leg-134 gate-evidence replay

`leg134_pickup.jsonl` contains 5,586 unchanged JSONL records (1,336,556 bytes)
from `/home/otto/dev/ro-bots/.work/runtime/population-live/traces/*.jsonl`.
`leg134_pickup_verification.json` records the source receipt/fixture SHA256s,
original pickup counters and conversion proofs, receipt window, and twelve
individually checked sightings with original source filenames and line numbers.
The source receipt is `population-receipt-134-1795718339.json`, as named by
`run/reviews/leg134-verdict.md`; no `1795720872*` receipt exists on this host.

Extraction preserves source-file order (filenames sorted), every session row
before the receipt close, and in-window `loot_performed`, `world_event/ItemDrop`,
and `swing_observation/damage` rows with `damage_type == 1`. Session history is
retained even before the window so presence generations match the original
receipt exactly. No decision requests, chat, credentials, or inventory snapshots
are included. The window is inclusive at `2026-11-26T18:38:59.534156+00:00` and
exclusive at `2026-11-26T20:30:00.016649+00:00`.

Before changing the classifier, this fixture reproduced the complete original
pickup summary (including all conversion identities, generations, and proofs)
and coverage counters exactly: 118 nearby sightings, 50 cohort attempts,
29 fleet-credited sightings, 39 unattempted, 4 outside-cohort attempts, and
35 legacy residual. These counts and proofs remain identical after the fix.
Fleet-attempted remains **83/118 = 70.339%**, with 82/83 successes; agent-attempted
remains 54/118 with 53/54 successes. This is a measurement change only.

| Reason class | Original | Fixed |
| --- | ---: | ---: |
| out_of_approach_range_owned | 0 | 0 |
| spawn_timeout_far_kill | 0 | 0 |
| map_transition_blindness | 0 | 0 |
| despawn_before_observation | 3 | 3 |
| ownership_ceded | 0 | 12 |
| combat_priority | 0 | 7 |
| authored_action | 0 | 4 |
| walk_arrival_gate | 0 | 2 |
| pose_gate | 0 | 0 |
| pickup_ack_gate | 0 | 0 |
| unknown | 36 | 11 |

UNKNOWN falls from **36/39 = 92.308%** to **11/39 = 28.205%**, passing <50%.
Ten of the remaining unknowns have no associated loot evidence; one has only a
`map_changed` expiry (floor 617), which cannot prove map blindness or a pickup
gate. Zero entries for the six gate classes were absent from the original
aggregate schema; the fixed aggregate includes every class and sums to 39.

## Actual gate fields and resolution

Raw `kind=loot_performed` records identify a presence through `persona`,
`floor_item_id`, `drop_seq`, `drop_x`, `drop_y`, map and session generation.
`outcome=deferred` plus `reason` names the gate; live taps also carry a matching
`reason_class`. An `outcome=expired` row with
`reason=presence_epoch_expired` retains the **first** defer as `deferred_reason`
(`LootAttribution.defer` uses `setdefault`). This expiry annotation must not
override later deferred observations. The classifier uses the latest observed
defer, falling back to expiry's `deferred_reason` only if no defer tap survives.
It preserves both fields, plus the tap's `reason_class`, in the output evidence.

Refusal conjuncts found in these raw leg-134 records and their runtime producers:

- `nearer_agent` -> `ownership_ceded`: another observed body's `(distance, AID)`
  sorts before the client's. This proves ceding, not collection by that body.
- `threat` -> `combat_priority`: an active attackable threat blocks the loot path.
- `authored_action` -> `authored_action`: an authored Attack or Loot owns the tick,
  so the mechanical loot path stands down.
- `pending_walk`, `walking`, `awaiting_walk_arrival`, and
  `arrival_confirmation_exhausted` -> `walk_arrival_gate`: a walk is pending,
  received arrival/fresh position is missing, or the two confirmation requests
  for that presence are exhausted.
- `resting` -> `pose_gate`: the rest latch blocks pickup. It appears as an
  intermediate gate in leg-134, superseded by later ownership/combat gates.

The existing mapping also covers `not_standing` -> `pose_gate` and
`awaiting_pickup_ack` -> `pickup_ack_gate`; synthetic regression cases pin both,
along with every existing gate spelling. Unknown gate spellings remain unknown.
Explicit map mismatch, expiry-before-sighting and spawn-timeout evidence retain
their existing precedence. Neither disappearance nor an expiry after observation
proves natural TTL, ownership, a safe opportunity, or lost revenue.

## Individual raw-JSONL checks

Each filename below is under the original trace directory; line numbers are
1-based. The first ten are independently read gate-bearing sightings. The last
two are controls. The fixture retains the original raw records, not renamed
receipt output. Tests pin the literal expected reason and last gate for each.

| Persona | Floor / cell | ItemDrop line | Evidence lines | Hand-checked result |
| --- | --- | ---: | --- | --- |
| pop_0003_g01m01 | 600 / 171,354 | 378122 | 378119,378121,378133,378174 | threat -> awaiting_walk_arrival -> authored_action; expiry retains threat; **authored_action** |
| pop_0003_s00 | 600 / 171,354 | 429222 | 429214,429247 | nearer_agent then expiry; **ownership_ceded** |
| pop_0003_g01m01 | 601 / 172,352 | 378125 | 378120,378134,378175 | threat -> authored_action; expiry retains threat; **authored_action** |
| pop_0003_g01m00 | 614 / 148,358 | 393448 | 393441 | deferred threat with matching presence/cell; **combat_priority** |
| pop_0069_g01m01 | 619 / 222,339 | 123293 | 123309 | deferred threat; **combat_priority** |
| pop_0069_g01m02 | 624 / 275,332 | 104540 | 104515 | deferred pending_walk; **walk_arrival_gate** |
| pop_0069_g03m01 | 633 / 37,181 | 107965 | 107964,107980,107984 | nearer_agent -> authored_action; expiry retains nearer_agent; **authored_action** |
| pop_0069_g03m01 | 634 / 37,182 | 108010 | 108014,108038,108048 | resting -> nearer_agent; expiry retains resting; **ownership_ceded** |
| pop_0069_g02m02 | 640 / 31,206 | 103024 | 103028,103034 | threat then expiry; **combat_priority** |
| pop_0069_g03m01 | 648 / 79,205 | 110568 | 110572,110577,110596,110616 | pending_walk -> walking -> arrival_confirmation_exhausted; **walk_arrival_gate** |
| pop_0069_g01m02 | 606 / 256,305 | 104100 | none | no associated loot evidence; **unknown** |
| pop_0069_g03m02 | 612 / 171,330 | 103719 | 103685,103707 | expiry logged 19:03:00.655442 before sighting 19:03:15.784883; **despawn_before_observation** retains precedence |

For each gate-bearing case, the raw deferred row's `reason_class` agrees with
the hand result. Presence-expiry evidence is retained without upgrading these
observed barriers into claims of natural TTL expiry. The two controls stay in
their original classes. All twelve pass as regression fixtures. Independently,
all 25 newly resolved sightings agree with the latest raw defer's live
`reason_class` tag (12 ownership, 7 combat, 4 authored action, 2 walk arrival).

## Offline replay

```sh
nix develop -c uv run python scripts/swing_funnel.py \
  tests/fixtures/leg134_pickup.jsonl \
  --start 2026-11-26T18:38:59.534156+00:00 \
  --end 2026-11-26T20:30:00.016649+00:00 \
  --output /tmp/leg134-classifier-gates.json
```

Only `src/robots/app/drop_coverage.py` changes production code. Loot dispatch,
ownership, continuation, pickup proofs/counters, and the gate producers are
unchanged. Leg-133's existing raw fixture now resolves to 12 unknown, 8 ownership
ceded, 5 authored action, 4 walk arrival, 2 combat priority, and 5
expiry-before-observation (36 total), retaining its original pickup rates.
