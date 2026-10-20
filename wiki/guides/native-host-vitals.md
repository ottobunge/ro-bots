---
title: Native host vitals — source-backed projection and readiness frontier
created: 2026-10-06
updated: 2026-10-06
type: guide
status: proposed
tags: [protocol, testing, rathena, ops]
---

# Native host vitals

Related: [[goals-ledger]], [[scheduled-native-host-idle]], [[two-bot-live-limbs]].

## Accepted offline client/projection scope

The client retains received SELF `0x00B0` HP/MAXHP/SP/MAXSP counts, with empty
initial state and connection/map-transport allocation resets. The pinned packet
is eight bytes: unsigned 16-bit header/parameter and signed 32-bit count.
The strict detached projection requires all four valid counts and preserves zero
SP; missing or inconsistent values deny projection rather than imply full health.
Map-warp reset is not covered. Positive presented HP is not an alive/death oracle.

Independent client/projection review passed 208 unique repository cases plus
65 subtests, with 100% helper statement/branch coverage under the unchanged 85%
scoped threshold. Parent readback matched all 14 frozen public inputs and five
review artifacts. This excludes scheduled-host source and captured native frames.

Evidence:
- `run/reviews/native-vitals-independent-review.json`
- `run/reviews/native-vitals-parent-review-reconciliation.json`
- Earlier combined baseline: 311 tests plus 65 subtests, not host integration.

## Host integration: implemented, not accepted

Received counts replace the four `1` placeholders in `ScheduledAgent.build_state`.
Brain startup has a separately bounded status wait; incomplete tick snapshots skip
cognitive processing, while operator dispatch stays on its existing path. Idle
presence with no brain does not require vitals. Twenty-one new synthetic tests
were reported. Only the explicit `FakeGameClient` status fixture was added; no
old assertion was weakened. Full configured gate attempt timed out after 120
seconds and did not establish current root coverage or acceptance.

Parent's real offline negative probe exposed a readiness hole: a client with a
complete retained quartet, `running=False`, `connected_map=False`, null socket and
no reader was accepted if receive/dispatch errors were empty. The native client
has no `is_healthy` hook, so the optional hook did not protect this case.

`host-native-vitals-stopped-reader-red.log` preserves the failed assertion.
Delegate `deleg_d9e1508b` owns a narrowly scoped vertical-TDD repair of the guard
and new host tests. No unreviewed host was activated and no native telemetry probe
was run. Reader repair is now implemented: exposed stopped/disconnected/null-socket/
dead-reader states deny the retained quartet; exact nonlocal liveness exceptions
propagate. Forty-one host cases pass (21 integration plus 20 repair); implementer
combined scope325 passed. Fresh frozen host/self-chat review is deleg_8408ed50.

Parent full configured test task passed2070tests plus65subtests/94.57% coverage,
149public inputs stable and exact JUnit counts matched. However the complete
configured check failed before pytest: `_native_vitals` has Xenon rankC, while
maxB is required. The failure is preserved separately from the passing test task;
no lower thresholds or full-check success claimed. Reviewer was steered with this
quality blocker, source kept frozen. A minimal behavior-preserving guard extraction
and fresh verification remain; actual native receipt remains unverified.

Frozen independent host review completed:325 host regressions,104 client regressions
and50 additional adversarial cases (479 unique physical JUnit entries) passed.
No security concerns or logic errors reported; overall review is false solely for
Xenon rankC. Original failed evidence is retained. Repair cycle1 `deleg_7d3443f8`
owns only a behavior-preserving extraction of session readiness from projection.
No test edits, lowered gates, native execution or new cognition are authorized by
that source repair. Fresh frozen review/full configured check must follow.

The quality repair is now implemented: session readiness is extracted without
changing checks/evaluation order/tests. `_native_vitals` isB/6 and the new helper
B/8; old C/13 failure retained. Parent completed the full configured `task check`:
2070tests plus65subtests,94.57% coverage, allstatic gates passed,149public inputs
stable/current. Dependency audit exit0/no known vulnerabilities found by that run.
Fresh independent final review `deleg_875a98fc` is pending, so host acceptance is
still withheld. No native telemetry or cognition was enabled by these checks.

## Bounded native proof — now accepted

Fresh independent final review passed489unique cases (479 regression/adversarial
plus10 differential ordering probes),93.11% scoped coverage/helper100%; parent
matched149current review inputs plus whitelist and exact physical JUnit artifacts.
The full configured2070+65/94.57% gate and dependency audit remain unchanged.

User separately authorized one passive two-existing-bot probe capped60seconds,
with no restart/reset/account edits/game actions/inference. Fresh engine checks
verified exactfour test-owned containers/volume users, expected images, loopback
16900/16121/15121 and healthy MariaDB. Fresh SQL matched both exact nonGM fixtures
and offline characters; credentials stayed private and were never printed/hashed.
Initial raw-inspect tool truncation and kernel Docker-endpoint mismatch refused
without connecting; terminal-local compact parsing resolved these harness issues.

Both actual clients then received SELF0x00B0 IDs5/6/7/8. Wire counts, retained data
and reviewed host projection matched for each: HP42/MAXHP86/SP11/MAXSP20. This is
received client presentation, not alive/death truth. Native phase0.053seconds,
account-matched PIN challenge/success twice each, no brain/agent worker/model/game
calls. Supported clients/readers/temp transports closed; retained vitals were
rejected after disconnect. Exact native SQL readback confirmed both offline and
saved coordinates unchanged; four existing services stayed healthy. All149public
source inputs still match. Evidence: `native-vitals-passive-live.json` and
`native-vitals-passive-final-disposition.json`. No whole milestone closed.

## Still outside acceptance

No real cognition is enabled. Actor type/distance, level, job and inventory still
contain placeholders; status presentation does not prove combat or death state.
Self-chat suppression uses account IDs plus inherited character-ID echo tags,
whose senderless representation remains lossy. Neither synthetic frames nor the
prior real idle/journal test establish intelligent play or any full milestone.
