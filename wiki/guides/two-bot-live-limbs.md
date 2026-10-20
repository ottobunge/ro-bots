---
title: Two-bot native client-entry and limb verification
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [protocol, rathena, testing, ops]
---

# Two-bot native client-entry and limb verification

This is a bounded native protocol smoke result, not completion of any standing
milestone. See [[first-live-native-world]], [[goals-ledger]] and
[[adr-019-simple-volume-world-isolation]].

## Scope

The user separately authorized exactly two fresh non-human, non-GM test accounts
and novice characters in `ro-bots-world-test`, INSERT-only provisioning after code
review, brief stop/restart of only its native roles, and login/movement/chat/
sit-stand/party actions. No existing-account writes, world reset, debug/production
changes, paid inference or legacy seeder bypass was authorized or performed.
All credentials, PINs and connection material remain private: [REDACTED].

## Reviewed code and provisioning

- Pure renderer review: 82 unique tests, 100% renderer coverage, 51 additional
  malformed-input probes, and 17 frozen current dependencies reconciled.
- PIN protocol review: 93 tests and 405 native inverse-permutation vectors.
  The seven new EM101 diagnostics were corrected with unchanged-message
  assignments. Independent delta review proved exactly those seven edits;
  254 unique tests plus 65 subtests passed. Existing spike lint/type failures
  remain recorded, not waived or described as clean.
- Last configured full gate before those lint-only assignments: 1,926 tests
  plus 65 subtests, 94.36% coverage, exit0; 137 public input hashes unchanged.
- Immediately before provisioning, exact container labels, immutable image IDs,
  volume mounts/users and localhost bindings were checked. Only the owned map,
  char and login roles were stopped; the database remained healthy. Their ports
  could be bound while stopped, and no non-root database sessions remained.
- Fresh selected-schema and conflict checks confirmed one server-only account,
  zero normal accounts/characters/skills, and actual allocation counters.
- Six plain INSERTs ran once: two login, two character and two Basic Skill rows.
  Exact identity, private scalar, class/level/coordinate and skill readback passed.
  The existing server-only row was unchanged before restart; counts in the other
  67 tables were unchanged. MyISAM rollback/exactly-once is not claimed.
- The two novice fixtures have level10/Basic Skill9 for protocol testing, not a
  certified legal leveled build. Private manifest and SQL have mode0600 below a
  mode0700 stage directory. Native roles were restarted without resetting data.

## Actual native observations

Both four-action runs passed; the second used the same accounts and existing
party state without reseeding or reset:

| Action | Required observation | Result |
|---|---|---|
| Login | Exact fixture account/character pair | Passed throughout both runs |
| Chat | Fresh message received by the other client, exact sender | Passed twice |
| Movement | Other client observed exact announced destination | Passed twice |
| Sit/stand | Other client observed sit followed by stand, exact actor | Passed twice |
| Party | Fresh current-party invite and exact recipient acceptance/membership | Passed twice |

The second run recorded eight native PIN-required statuses and eight matched
success statuses. All PIN account IDs matched. Supported socket/reader cleanup
checks passed. Both runs finished in approximately14 seconds within the bounded
59-second harness budget.

Final external readback confirmed four running services, healthy MariaDB,
one server-only account, exactly two non-GM fixture accounts/characters, both
characters offline, two Basic Skill9 rows and one persistent party containing
both exact fixture characters.

## Important movement limitation

An initial second-run preflight incorrectly expected the saved Y coordinate to
remain at least151. It failed before any second-run player action. Actual database
coordinates remained the original spawn positions, although the first smoke had
observed the advertised destination. The failed assumption is preserved in its
report; the cause has not been established.

The corrected second run checked walkability from the actual current positions
and passed the unchanged harness. This accepts peer-observed destination messages,
**not completed arrival or saved-position persistence**. Investigate and verify
that gap separately rather than converting an announced walk into an arrival
claim. Party persistence was read back independently and is accepted narrowly.

## Subsequent arrival investigation

Pinned native source confirms that movement announcements precede coordinate
updates. Ordinary disconnect removes the pending walk timer and saves the actual
cell. A controlled differential reproduced the issue: immediate close retained
(150,150), while a one-second dwell saved (150,151). This is normal cancellation,
not evidence of corrupted persistence; a fixed dwell is not a general oracle.

A separate live prototype then sent one confirmation request to the same target.
Its fresh self0x0087 had both origin and destination equal to (150,152), unlike the
initial acceptance from (150,151) to (150,152). It arrived in0.151 seconds, with no
fixed post-movement sleep. Immediate supported cleanup saved exactly (150,152),
and both characters were offline. No SQL writes or reseeding were involved.

This verifies the candidate arrival barrier on the actual pinned fixture. The
existing production harness has not yet incorporated or reviewed it; strict TDD
implementation is delegated. Freshness/correlation and deadline checks remain
necessary, and this does not imply arbitrary nonce/replay or multi-cell guarantees.

## Latest strengthened-harness acceptance

The independent arrival review passed 276 unique cases plus 65 subtests, matched
22 frozen current inputs, and covered every executable line in the arrival helper.
The configured whole repository gate passed 1,979 tests plus 65 subtests with
94.46% coverage; the separate host transport review is source-only.

The **revised production harness** subsequently passed twice without reseeding or
reset. Native saved coordinates advanced from (150,152) to (150,153), then from
(150,153) to (150,154), exactly matching each requested destination. Both runs
required the peer announcement plus fresh mover-stream native0x0087 from=to=target;
no fixed post-movement dwell was added. Chat, ordered sit/stand and exact-recipient
party acceptance passed too. Both exact characters were offline afterward in
one shared persistent party, with four running services and healthy database.

This closes the ordinary bounded one-cell fixture arrival/save gap. Historical
failed assumptions and prototype evidence above remain preserved. General
multi-cell/combat/status/warp movement, scheduled cognition and full milestones
are not accepted by this result. See native-arrival-revised-harness-live.json and
native-arrival-host-transport-final-disposition.json under run/reviews/.

## Evidence

Sanitized reports under `run/reviews/`:

- `world-test-fixture-independent-review.json`
- `client-pincode-independent-review.json` (original quality findings preserved)
- `client-pincode-quality-delta-review.json`
- `two-bot-fixture-live-provisioning.json`
- `two-bot-first-native-limbs.json`
- `two-bot-second-preflight-failure.json`
- `two-bot-second-native-limbs.json`
- `two-bot-live-final-readback.json`

Raw native output, SQL and the fixture manifest stay private and are not embedded
or hashed in these public reports.

## Still open

Completed movement arrival/persistence; combat/XP/targeted loot; scheduled host
with real Clef and LLM escalation; actual restart/reconnect agent memory; legal
progression; relationship/contribution/gossip/guild/WoE behavior; live dashboard
reconciliation; convenient clean Taskfile E2E; human-client joinability; sustained
populations and comparable benchmarks. None of the six full milestones is closed.
