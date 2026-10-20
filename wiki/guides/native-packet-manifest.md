---
title: Compiler-derived native packet manifest
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [protocol, rathena, testing, ops]
---

# Compiler-derived native packet manifest

## Accepted goal, not implementation acceptance

The user accepted this as an additional goal on 2026-10-07: build an auditable
packet catalogue from the exact pinned server source/profile, develop and verify
it offline, then integrate framing before another live gameplay attempt.
See [[goals-ledger]] and [[playable-world-acceptance]]. All six full milestones
remain open; accepting the goal is not accepting its implementation.

## Why this replaces selected-family discovery

The stable configured gate passes3612 unique tests plus65subtests at95% coverage.
Independent framing review passes264 physical cases plus65subtests; the15 latest
registry/name additions preserve all19 parser/helper ASTs and existing entries.
Nevertheless, the subsequent real single-session run fails after4.046s on0x00C0
at offset25 following0x07FB. Supported close/offline readback passes; native XP
and inventories remain unchanged. Packet-family subset coverage is insufficient
for ordinary server replies, even when each added family is correctly validated.

Evidence: `playing-fixed-framing-parent-gate.json`,
`native-fixed-framing-independent-review.json`, `playing-world-fixed-framing-run.json`.
Preserve these failures; do not describe the last run as successful gameplay.

## Exact authority

- rAthena revision `e985006171d2eb320ee512a653f4c83aea3d81b6`.
- MAIN/pre-Renewal packet version20180704; RE/ZERO/RENEWAL absent.
- Actual installed map compiler flags and compile recipe, not default headers.
- Full unchanged headers and bundled include dependencies; no guessed constants,
  deleted map.hpp include, whole-checkout Nix source or custom global toolchain.
- Native runtime obfuscation policy remains distinct from compiler support macros.

The parent compiled the full headers successfully using the installed flags and
bundled rapidyaml/c4core/libconfig plus the existing MariaDB development headers.
Executed oracle output: `emotion 192 7 0 2 6`, `stopmove 136 10`.
Source and binary fingerprints: `native-manifest-full-header-preflight.json`.
This proves these layouts, not the complete catalogue or live behavior.

## Catalogue requirements

1. Preprocess the actual profile and enumerate all active server-reply definitions,
   not a gameplay-topic regular expression that omits ordinary emotion messages.
2. Compile packet IDs, sizes and relevant offsets; retain source/flags/dependency
   fingerprints and exact definition/sender provenance.
3. Match active send lengths. Direct fixed-size sends may justify fixed frames;
   flexible prefixes or buffers sent using a computed length must not become fixed
   merely because their C++ structure has a sizeof value.
4. Record proven variable total-length framing explicitly. Unmapped aliases, raw
   WFIFO paths, ambiguous direction, conflicts and unsupported bindings remain
   an enumerated unresolved list; no silent coverage or universal-completeness claim.
5. Sort deterministically; regenerate to identical bytes on unchanged inputs;
   reject conflicting IDs, profile mismatches and compiler failures.
6. Test fragments, coalesced/repeated mixed frames, malformed variable lengths,
   truncation, unknown IDs and authority separation before runtime integration.
7. Keep C->S/login/character mappings separate from the first map S->C catalogue.
   Preserve previously reviewed mappings until same-profile migration is verified.

Framing is not gameplay semantics. No position/arrival/class/life/acquisition or
party-membership promotion follows merely from recognizing a frame. Unknown IDs
remain rejected. See [[two-bot-live-limbs]] and [[native-self-progression]].

## Work ownership and next acceptance

`deleg_88c694ee` separates a strict-TDD generator implementation from read-only
sender/variable/alias coverage reconnaissance. Neither operates the game world.
The parent owns source freeze, independent review, combined gates and later exact
fixture preflight/live observations. Catalogue coverage, runtime integration and
combat/XP/loot proof are separate acceptance steps.

## Interrupted generator recovery

The original generator task was interrupted mid-way through its fifth vertical
slice. Its final report was not produced. Parent rerun observes4 passing tests
and1 genuine failure: complete compiler dependency closure is not recorded.
Do not describe this partial generator as approved or integrate its output yet.
`deleg_4cd8d164` finishes from that exact RED boundary without discarding the four
working slices or changing the native parser.

The independent sender audit completed. Parent verifies20 compiler artifact hashes
and the unchanged public-source hashes; its430 compiled structure rows,517 sender
sites and366 unresolved entries match the physical report. These are different
inventory categories, not430 approved frames or366 unique missing IDs. The bounded
binding analysis is not universal executable sender/dataflow coverage.
Evidence: `native-manifest-sender-surface.json`, `native-manifest-parent-recovery.json`.
Catalogue provenance, conflict validation, output preservation and determinism remain
part of the generator acceptance frontier.

Before runtime migration, `deleg_9c48e822` independently inventories the actual
client/collector-used IDs and compares reviewed mappings with this compiler audit.
It separates map S->C proofs from outgoing shuffles and login/character scope,
and identifies alias/raw-send preservation requirements without changing framing.
This prevents a new catalogue from silently replacing verified entries with stale
numeric defaults or treating a length field as variable when the sender is fixed.

## Completed bounded generator, pending acceptance review

The finisher completes the original closure RED and retains all five original
cases. Ten physical tests now pass with89.96% owned coverage; owned Black/Ruff,
strict mypy and Xenon B/B/A pass. The author's combined task check times out during
pytest and remains failed/unverified evidence, not whole-suite acceptance.

Parent executes the CLI independently: output is byte-identical to the author's
gold catalogue, with265 unique resolved IDs (216fixed,49variable) and102 unresolved
records. All469 recorded dependency hashes physically match. These counts cover
the bounded named-structure/direct-sender recognizer, not all raw/alias paths.
Reports: `native-manifest-generator.json`, `native-manifest-parent-reproduction.json`.

The185-file completed snapshot is frozen. Independent generator review
`deleg_1a23a6a6` and a fresh long-running parent task check are underway. No runtime
integration or native effects. The migration-baseline audit remains separately
owned; catalogue and gameplay acceptance are still distinct.

## Independent rejection overrides the configured gate

The completed pre-repair configured gate passes3622 unique tests plus65subtests
at95% coverage. Independent review nevertheless rejects the generator:37 physical
probes contain7 failures (30pass), plus a real mutable-flags profile-bypass probe
publishes changed rows under the unchanged claimed profile.

Findings are limited to compiler-evidence/options trust, ambiguous sender identity
and assignment order, and floats accepted for two integer variable-frame fields.
The reviewed gold catalogue is reproducible; no wrong gold row or malicious/private
input execution is demonstrated. That does not make the unsupported cases safe.
The catalogue remains excluded from runtime. `deleg_b1f2d2eb` owns repair cycle1,
with separate RED/GREEN slices and a fresh independent review required afterward.

The read-only migration audit identifies four framing-policy differences:
09FD/09FE/09FF and0A1C are current variable mappings but compiler-proven fixed sends
for this profile. They require explicit migration tests/review, not automatic edits.
Shared login/char/PIN framing and reviewed006D override stay separate from map
numeric shuffles. Evidence: `native-manifest-migration-baseline.json`,
`native-manifest-generator-independent-review.json`,
`native-manifest-parent-review-rejection.json`, `manifest-generator-parent-gate.json`.

## Repair cycle1 finished, independent re-review pending

Parent matches repair source/test hashes and retained RED/GREEN physical evidence.
All36 owned cases pass,94.76% coverage. Trusted compiler evidence/options are bound
before invocation; original response-file probes now reject without publication.
Uncertain sender identity/scope/order stays unresolved; variable fields require
exact integers. Original rejected review and265-row gold remain unchanged.

The conservative classifier moves `ZC_ITEM_PICKUP_ACK` and `ZC_ADD_EXCHANGE_ITEM`
to unresolved because their senders reset the object before final assignment.
New output:263 resolved (214fixed49variable),104 unresolved; repeated bytes match.
This is an honest narrower catalogue, not permission to lose pickup framing.

`deleg_86d5a7cf` independently re-reviews this repaired snapshot. The185-file frozen
parent full gate runs anew; previous3622-case gate describes the pre-repair code.
No loader/runtime/native integration occurs until approval and explicit mapping
preservation. Evidence: `native-manifest-generator-review-repair.json`.

## Cycle1 re-review rejection and final automatic repair

The completed cycle1 configured gate passes3648 unique tests plus65subtests,
95% coverage. Re-review reproduces all original checks successfully but its71
independent cases contain3 fresh failures: lambda-parameter shadowing and prefix
header increment/decrement. Parent matches artifacts and executes the valid C++
counterexamples, observing headers2/0 and the lambda's distinct object size.
No matching constructs were found in the pinned sender source; no wrong current
catalogue row is proven. Unsupported cases nevertheless falsely resolve, so the
catalogue stays rejected. Compiler-options trust fixes remain accepted in scope.

`deleg_c786aebb` is automatic repair cycle2of2, restricted to these two findings.
If final re-review still rejects it, stop automatic repairs and request a user
 decision. Preserve both rejected reviews, all counterexamples and pre-repair gate.
Runtime/native framing remains unchanged. Evidence:
`native-manifest-generator-rereview.json`, `manifest-repair1-parent-gate.json`.

Cycle2 now finishes on its bounded source scope:43 physical owned cases pass,
94.81% coverage; replayed71 previous probes pass. Parent matches physical artifacts
and source/test hashes. Only `associated_body` changes; trusted compiler/input
checks and all original36 test ASTs remain unchanged. Catalogue263/104 output bytes
remain identical. Fresh final review `deleg_e885e556` and a new185-file parent gate
run before admission. Replayed probes by the repairer are not independent approval.

Final review rejects nine fresh cases despite the passing3655+65/95% parent gate.
Both automatic repairs are exhausted; implementation stops for user direction.
See [[native-packet-manifest-review-blocker]] for verified counterexamples and scope.






