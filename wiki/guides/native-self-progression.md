---
title: Native selected-character and level receipts
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [protocol, testing, rathena]
---

# Native selected-character and level receipts

**Accepted scope: offline protocol retention only.** Historical character-list
information is not continuous current-class authority. No native receipt,
cognition or gameplay milestone is accepted here. See [[goals-ledger]] and
[[native-host-vitals]] for the surrounding readiness work.

## Retained data

`BotClient.selected_character_snapshot` is either absent (`None`) or the frozen
snapshot of the exact selected `CHARACTER_INFO` row. The pinned MAIN/pre-re
20180704 layout is155 bytes: character ID at0, signed job level at24, signed job
ID at64, signed base level at72, wire slot at118 and sex at154.

The client validates the entire0x006B list: exact bytes, matching header/declared
length,27-byte header and complete155-byte rows. Duplicate IDs, slots and decoded
names are rejected before selection. It selects the exact character name and
sends that row's wire `CharNum`, never its list ordinal. It publishes the snapshot
only after the0x0AC5 or0x0071 map-routing response returns the selected character ID.
Unknown/signed raw jobs and historical levels are retained as provenance, not
normalized to Novice or substituted for received current levels.

`status_params` retains signed SELF0x00B0 values for5/6/7/8 (HP/SP quartet) and
11/55 (base/job levels). Decreases, zero and negative receipts remain raw; the
pure projection rejects invalid values when used. Class enum19 and the0x00B1/
0x0ACB counters do not become current-level telemetry.

Authority: `run/reviews/native-character-progression-frontier.json` and the pinned
native headers/emission sites recorded there.

## Lifecycle and readiness limits

- Clear historical selection before character handshake, connect and close.
- Clear it again after the old reader stops during reconnect.
- Existing map-transport allocation clears the status map, requiring new levels.
- Supported connection failure clears selection while preserving the origin.
- Direct private map-allocation failure can retain the historical snapshot; it
  does not expose action-ready progression.
- No `job_fresh` flag or call to `require_native_progression` was added to the
  client. LOOK_BASE appearance, disguise, mounted variants and map transitions
  do not supply continuous actual-class authority.
- The pure projection remains separately bounded to Novice0 and requires an
  explicit caller-provided freshness decision. Host integration must not guess it.

Actual native receipt and safe freshness/warp/look revalidation remain future
work. Existing idle lifecycle evidence in [[scheduled-native-host-idle]] does
not resolve these limits.

## Verification and preserved failures

The implementer added49 source-shaped client cases. Its first combined run
passed435 and failed an older test expecting parameter11 to disappear. Parent
reproduced the failure, retained four unsupported-parameter cases using12 in
place of11, and added three health-isolation cases. Levels neither alter HP/SP
projection nor supply missing health; no production guard was weakened.

Parent selected439 unique cases pass. Independent review passes469 unique cases
(439 repository cases plus30 adversarial probes), with100% statement and branch
coverage for the vitals/progression helpers. Parent verified2869 current public
dependency hashes,27 review artifacts and physical JUnit identities. The configured
full gate passes3065 tests +65 subtests with94.64% coverage and156 stable public
source/test/config inputs. These are offline results, not server observations.

Legacy spike quality debt is not waived:47 Ruff findings,13 client plus2 packetdb
mypy errors. Existing numerical debt increased: constructor statements51→52,
character-handler branches31→32 and statements108→111. Configured public source/
test gates pass; they do not make the entire spike quality-clean.

The worker failure, parent RED and reviewer's corrected fake-allocator signature
failure remain archived. Final acceptance evidence:

- `run/reviews/client-native-progression-final-disposition.json`
- `run/reviews/client-native-progression-independent-review.json`
- `run/reviews/client-native-progression-parent-task-check.json`
- `run/reviews/client-native-progression-parent-baseline.json`
