# Leg-132 pickup replay

`leg132_pickup.jsonl` is a reduced, offline trace capture for the exact
`population-receipt-132-1795678598.json` window:
`2026-11-26T07:36:38.276912+00:00` inclusive through
`2026-11-26T09:30:00.250124+00:00` exclusive.

Source: `/home/otto/dev/ro-bots/.work/runtime/population-live/traces/*.jsonl`,
windowed using that receipt's `swing_conversion.start/end`. Retain all
`loot_performed`, `world_event/ItemDrop`, `swing_observation/session` and
`swing_observation/damage` rows with `damage_type == 1`; retain only identity,
position, receipt outcome, reason, session and sequence fields. Sort by persona
and trace timestamp. Session rows are essential: transport rebuilds reuse native
sequences, and collection receipts must remain with their own presence generation.
The 732 rows contain no credentials, inventory snapshots or decision requests.

Original receipt SHA256:
`22eace4898a45446cfb491892b1103931ad917a5f95a4b69792eb5ef5e9f833d`.
Fixture SHA256:
`e5fdbeeec876f733b1e430daa72f07143186a09f052bba0fdff19858e4fdab53`.

Replay from the repository root:

```sh
nix develop -c uv run python scripts/swing_funnel.py \
  tests/fixtures/leg132_pickup.jsonl --output /tmp/leg132-fleet-replay.json
```

The replay preserves pickup counts (other combat counts are intentionally absent):
51 nearby sightings; agent attempts 23 (45.10%) with 19 successes (82.61%);
fleet attempts 38 (74.51%) with 37 successes (97.37%). Fifteen confirmed
unattempted cedes add attempts and successes; three peer-won attempted races
add successes only. The per-persona sighting cohort can describe the same
physical item more than once; these fleet numbers measure converted
opportunities against that existing cohort, not distinct inventory additions.
Unconfirmed cedes and bare expiry remain unconverted.
