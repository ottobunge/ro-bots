# Leg-133 drop coverage split

Base: `3b84e1f4`. Branch: `t3/drop-coverage-split`.

**Measurement is implemented; >=70% acceptance remains unmet.** The split
preserves the original fleet attempt rate, **57/87 = 65.517%**, and 57/57
successes. The full original trace replay and reduced fixture agree.

## The verdict's residual is not a 30-row cohort

| Reconciled measurement | Count |
| --- | ---: |
| Nearby per-persona sightings | 87 |
| Local attempts matched to those sightings | 37 |
| Existing fleet-credited sightings | 14 |
| Uncovered sightings | 36 |
| Attempts outside the nearby cohort | 6 |
| Historical arithmetic residual (36 - 6) | 30 |

The original numerator counts every send, including six without a nearby
sighting. Reconnecting can also surface a physical floor item more than once.
For pop_0069_g04m02/572 the 13:42:42 sighting belongs to the old session; the
13:43:02 attempt belongs to the new session's 13:43:01 sighting. Matching only
persona/floor ID incorrectly hides the old session's missing attempt.

## Exact evidence-based loss distribution

| Reason class | Count |
| --- | ---: |
| Out of approach range while owned | 0 |
| Explicit far-kill spawn timeout | 0 |
| Observed map differs from drop map | 0 |
| Presence-expiry receipt before ItemDrop trace | 5 |
| Unknown loss cause | 31 |
| Total identifiable uncovered sightings | 36 |

The five ordering cases are pop_0003_g01m00/528 and /529,
pop_0003_s00/528 and /529, and pop_0003_g00m02/533. Their receipt ordering
establishes disappearance before the event was logged, not natural TTL expiry.
No confirmed collection exists under the original fleet-conversion rules.

Gate evidence is preserved separately: last gates across all 36 sightings are
12 with no loot receipt, 11 `nearer_agent`, 5 `authored_action`, 4 `threat`,
2 `pending_walk`, 1 `awaiting_walk_arrival`, and 1 `walking`. A gate tap is an
observed barrier, not proof that a subsequent safe pickup opportunity existed.

## Changes and mechanism decision

- Add a reason enum and `reason_class` to every existing runtime
  `drop_unattempted_reason` tap. Original reasons and memo behavior are retained.
- Attach session-bound per-sighting rows, zero-inclusive counts, original gate
  evidence, and mixed-cohort reconciliation to fleet and per-agent receipts.
- Include the original 1,057-row portable fixture, source hashes, replay
  instructions, and complete raw-replay evidence in the adjacent JSON/README.
- No runtime behavior fixes landed: none of the classified losses indicts
  approach-budget rotation, far-spawn timeouts, or map blindness with a clear
  mechanism. Combat priority, nearest-agent ownership (`eefb95c4`), no pickup
  during walking, and one wire attempt per presence retain their existing code.

The immutable historical replay cannot demonstrate new sends from a runtime
change. Improving the rate requires new received-wire evidence or a separately
labelled, evidence-complete counterfactual replay. Relabelling unknowns,
subtracting six unrelated sends from arbitrary reason bins, loosening ownership
or arrival checks, or treating expiry as collection would manufacture closure.

## Validation

- TDD RED: 19 initial failures for the new receipt contract; another RED caught
  generation-blind borrowing of an old session's fleet credit in the new split.
- GREEN: 23 new test cases; 123 focused pickup/ownership/continuation/funnel
  tests passed. Each reason class and the exact leg-133 partition are pinned.
- Full `nix develop -c task --dir . check` GREEN: all static checks,
  **7,867 passed, 1 skipped, 65 subtests passed, 96.00% coverage**.
- An earlier gate started before the pinned rAthena source was installed and
  encountered missing-fixture failures. The fresh final run used rAthena
  `e985006171d2eb320ee512a653f4c83aea3d81b6` and main's two knowledge DB/config.log
  symlinks. No application code was changed to accommodate those missing files.
