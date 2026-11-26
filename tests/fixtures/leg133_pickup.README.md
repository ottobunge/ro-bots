# Leg-133 pickup reason replay

`leg133_pickup.jsonl` contains 1,057 original trace rows extracted from
`/home/otto/dev/ro-bots/.work/runtime/population-live/traces/*.jsonl` for
2026-11-26 13:00 UTC through the leg-133 close,
`2026-11-26T14:30:00.085588+00:00` (exclusive). The receipt's complete lifetime
starts at `2026-11-26T12:40:21.798941+00:00`; a full raw replay of that lifetime
was independently compared with this fixture. Pickup counters, conversion
identities/proofs and the reason split agree. Relative session-generation
numbers and list ordering can differ after removing the pre-window history.

Retain original `loot_performed`, `world_event/ItemDrop`,
`swing_observation/session`, and `swing_observation/damage` with
`damage_type == 1` rows. Sort by persona and timestamp, preserving each persona's original
row order. No decision requests, chat, DB credentials or inventory snapshots
are included. Counts for unrelated combat activity are intentionally absent.

Source receipt: `population-receipt-133-1795696821.json`, SHA256
`a0aa09a8e9e7102b99387521f64ff40305b8a5af7dc42b9ad82e32aac49daaca`.
Fixture SHA256:
`2eea6fb3f18c00ddbc74fc096911c8758d6abc24ee706eef94aab900cc896338`.

```sh
nix develop -c uv run python scripts/swing_funnel.py \
  tests/fixtures/leg133_pickup.jsonl --output /tmp/leg133-split.json
```

The original rate is **57/87 = 65.517%**, with 57/57 successes. Splitting
reasons changes no sends, conversions, ownership, continuation or motion gates.
The reason distribution below records the original instrument. With the
leg-134 gate-consumption fix, the same replay resolves 8 `ownership_ceded`,
5 `authored_action`, 4 `walk_arrival_gate`, 2 `combat_priority`, and leaves
12 `unknown` plus the original 5 `despawn_before_observation`. Pickup rates
and the cohort partition remain unchanged; see `leg134_pickup.README.md`.
`pickup.drop_coverage` exposes the session-bound nearby-sighting partition:

- 37 local attempts matched to nearby sightings;
- 14 existing fleet-credited sightings;
- 36 uncovered sightings: 5 `despawn_before_observation`, 31 `unknown`;
- zero `out_of_approach_range_owned`, `spawn_timeout_far_kill`, and
  `map_transition_blindness` loss classifications;
- 6 local attempts outside the nearby cohort.

Thus the verdict's **30 is 36 minus 6**, not a set of 30 identifiable drops.
One item (572, pop_0069_g04m02) is sighted in two sessions; only the second
session has a local attempt. A floor-ID-only join incorrectly calls both
sightings attempted. Neither cross-session borrowing nor subtracting unrelated
sends can establish the missing coverage.

The six outside-cohort sends are pop_0003_g00m02/531,
pop_0069_g00m01/544, pop_0069_g04m03/545 and /546, and
pop_0069_g00m02/574 and /575.

The five `despawn_before_observation` classifications mean the *receipt for
presence expiry* precedes the *logged ItemDrop event*. They do not establish
natural floor TTL, or distinguish collection from visibility loss. The 31
unknowns preserve each observed gate and supporting receipt. Their last gates,
combined with the five ordering cases, are 12 no loot receipt, 11 nearer agent,
5 authored action, 4 threat, 2 pending walk, 1 awaiting walk arrival, 1 walking.
No-loot-receipt is not evidence of a safe, owned budget opportunity.

The `spawn_timeout_far_kill` class requires an explicit `spawn_timeout` receipt;
the current runtime does not emit one. Bare expiry, distant visibility and
nearby death broadcasts cannot establish that mechanism. A map boundary alone
does not establish map blindness: the observed and landed maps must disagree.
Earlier approach deferrals followed by combat/arrival barriers do not indict
approach starvation. Existing gate taps receive their own reason class while
the original reason remains intact.

Complete per-sighting evidence and the full-raw comparison are recorded in
`run/reviews/drop-coverage-leg133-split.json`. Acceptance >=70% is **not met**;
no counterfactual attempt or pickup success has been added to historical data.
