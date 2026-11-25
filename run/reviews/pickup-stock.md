# Pickup-to-stock conversion — SOL slice, 2026-11-25

Branch `t3/pickup-stock`, base `c9ed58f9`. Read `leg131-verdict.md` first.
Sources: `.work/runtime/population-live/traces/<persona>.jsonl`, UTC
2026-11-25 19:00 inclusive to 20:30 exclusive, plus `/tmp/population_leg131.log`.
The compact extracted evidence is `pickup-stock-leg131-evidence.json`; timestamps,
personas, floor IDs, packet sequences and complete relevant receipt rows locate
its sources without depending on scratch logs. No trace or spike was rewritten.

## Failure-mode verdicts

| Mode | Verdict | Evidence and change |
| --- | --- | --- |
| Threat deferral | REAL missing continuation | Both `_loot` and `_loot_mechanical` called `_note_loot_threat_defer`, which only logged; unlike out-of-range/rest/arrival deferrals, it never called `LootAttribution.defer`. A newly deferred item therefore could not reach `_loot_resume`. Now queue owned, unattempted presences before logging and resume from received host ticks and the existing serialized combat/keepalive pump. No threat override. |
| Authored-action collision | REAL missing queue; existing queue also blocked | `_note_loot_authored_defer` likewise only logged when an Attack or authored Loot held the tick. The second item behind an authored Loot could lose its continuation. Now it uses the same presence queue. A held out-of-range move also returned `None`, admitting the farm roam action; it now returns an empty action tuple while its approach is held. Invalid/unmintable targets still allow other candidates. |
| Ack-lane starvation | REAL, principal attempt-success accounting gap | Six of the 27 attempts had no picker inventory ACK. All six have an own-source `0x08C8` action type 1 naming the attempted floor ID, plus a matching successful inventory ACK on a different party member. Pinned `pc.cpp:6250` calls `party_share_loot`; `party.cpp:1298` delivers to the selected party member, while `clif.cpp:5315` broadcasts successful collection by the picker. Previously the picker's single lane stayed pending until a map boundary. Now that exact received collection releases the lane; it never invents held inventory. |
| Expiry after long approach | RULED OUT for the three explicit refusals; presence expiry is REAL | Floor IDs 445, 453, 476 were attempted about 1.828, 0, 3.371 seconds after surfacing, at pickup range. Result 6 alone cannot distinguish ownership priority, another picker winning, or removal. Long walks do not explain these three. Deferred presences do disappear: expire them without sending, retain their original deferral reason, and tap the loss. Refusal after observed absence has the same race tap. No server-refusal retry. |
| Never attempted / ownership | REAL legitimate ownership holds; species filtering RULED OUT | 59 nearby persona/drop sightings contain 26 same-persona attempts and 33 unattempted sightings: 13 ownership, 5 ack-lane, 3 walk/arrival, 1 rest, 11 without a receipt reason. `_owns_floor_item` only compares received player distance and account-ID tie-break; it has no species or server ownership-window selector. Preserve that rule unchanged. Newly queued threat/collision work and the draining collection lane address losses without broadening ownership. |

The verdict's arithmetic `59 - 27 = 32` mixes nearby sightings with fleet attempts:
one attempt's drop was first surfaced outside radius two. The exact nearby cohort
therefore has 33 unattempted sightings. Nearby sightings can name the same shared
drop on several agents; they are not distinct world items. The 11 legacy cases
without a receipt reason remain unknown individually; the new taps remove that
blind spot rather than assigning unsupported causes retrospectively.

## Receipt and safety contracts

- `drop_unattempted_reason`: bounded per-presence/per-reason deferred rows, including
  threat, authored action, nearer agent, pending walk, rest and ack-lane holds.
- `pickup_deferred_retried`: the refired row of a real sent attempt, preserving the
  original `deferred_reason`, floor/item identity and attempt number.
- `pickup_race_expired`: queued presence removal, or an explicit refusal after its
  presence was removed. This means lost received presence, not proven TTL despawn.
- A successful own-source take animation creates `collected`; only its sent cursor
  and floor ID release the lane. Peer animations, unsent floors, stale sequences,
  and absence alone cannot create collection success.
- Inventory ACK first gives `succeeded`; collection first gives `collected` and a
  later matching inventory ACK gives `received`. The funnel counts the collection
  once; stock admission still requires a received successful inventory ACK.
- Standing, confirmed arrival, no pending walk, threat/rest/NPC/passive barriers,
  live authored combat priority, nearest-agent ownership, map/presence boundaries
  and one send per presence remain enforced. A send-side latch also prevents an
  ownership-deferred, already-attempted item being sent again by the resume path.

## Validation and limits

TDD: first regression run had **9 failures / 1 pass** on the baseline. The focused
new suite has **23 tests**, including both received-tick pump paths, approach
budget ownership, safety barriers, expiry/reused ID, party sharing, both receipt
orders, and end-to-end host-trace funnel counting. Existing ownership tests also verify
that an in-range pickup with no sell stock beats an active buy-trip approach;
that merchant collision is ruled out at `_priority_shop_actions` without changing
merchant admission or leases.

`pickup-stock-validation.json` records the same eight-case synthetic wire twin
run against baseline runtime and this implementation. It exercises direct pickup,
threat clearance, action collision clearance, received arrival, shared delivery,
an explicit refusal, nearer-agent ownership, and threat-held expiry. Baseline:
**4/8 attempted (50%), 2/4 successful (50%)**. Changed:
**6/8 attempted (75%), 5/6 successful (83.33%)**. Both offline bars pass. This is
not a counterfactual replay of the full live trace population.

For leg-131 itself, the six own collection animations establish **24/27 server
collections (88.89%)**, whereas picker inventory-ACK attribution alone recorded
18/27 (66.67%). The implementation now receipts this previously invisible success
and releases its lane; it does not add six new historical pickups or manufacture
stock for the picker. **Post-change live attempt and success rates remain for the
coordinator's leg-132 measurement.** No live runner, SQL mutation, merge or deploy
was performed in this implementation slice.

Full gate **GREEN**: `nix develop -c task --dir . check` — all static checks,
**7,821 passed / 1 skipped / 65 subtests**, **95.95% coverage**, 377.31 seconds.
A fresh unchanged-baseline measurement (same source as `c9ed58f9`) gives
**7,798 passed / 1 skipped / 65 subtests**, **95.94% coverage**, 388.16 seconds.
The brief's historical 96.40% was not reproduced on the baseline; this slice
improves the fresh comparable coverage by 0.01 percentage point. No coverage
threshold, test selection or safety gate was weakened.
