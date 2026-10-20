---
title: Recovery validation — interrupted delegates and native limbs
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [testing, protocol, rathena, ops]
---

# Recovery validation

This is an evidence checkpoint, not an additional architecture decision.
See [[goals-ledger]], [[adr-005-society-groups-reputation]], and
[[adr-010-worlds-volumes-e2e]] for acceptance scope and world isolation.

## Recovered Python foundation

Previous guild/human, WorldFeed, runner, build-template, and ROCm delegates
stopped on provider billing errors. Their output summaries are not completion
proof. The code remaining on disk was exercised by the parent.

A bounded isolated run of `tests/test_worldfeed_server.py` hung at
`test_force_action_tagged_in_feed`. Faulthandler showed TestClient buffering the
intentionally endless `/feed/events` response. Removed that unrelated buffered
GET; retained force-action response assertions and bounded SSE generator tests.
The full suite then completed: **211 tests, 91.65% coverage**. `task check` passed
Black/Ruff/mypy/Vulture/Xenon/Pylint-dup/Bandit/test gates; `task audit` reported
no known vulnerabilities. These are offline quality gates, not real game E2E.

## Native packet limbs — provisional after independent review

`spikes/003-clientless-limbs/test_limbs.py` reported PASS for all four limbs twice
against native localhost login/char/map servers. These timings are historical
observations, **not current protocol acceptance**:

An independent precommit review subsequently returned `passed=false`. It
reproduced handshake timeout/coalescing data loss, inactive conditional branch
selection, inconsistent actor identity/removal, duplicate chat dispatch and
stale/wrong-recipient party false positives. It also found unrestricted eval,
reusable credential defaults, insufficient seed ownership/offline validation,
unbounded deadlines, socket cleanup and lock-backoff defects, and an unsupported
character-creation request. Seven passing old regressions did not catch these.
Commit and additional native acceptance are blocked until fixes pass independent
re-review and the tightened smoke is repeated. No native re-run or SQL write was
performed in response to this review.

| Observation | First pass | Second pass |
|---|---|---|
| A's chat relayed to B | 1.02s | 1.01s |
| B observed A's movement destination | 1.11s | 1.11s |
| B observed sit and stand | 1.31s | 1.31s |
| Party create/invite/accept, names and accepted result | 1.81s | 1.81s |
| Total including reconnect/teardown | 13.26s | 13.25s |

Corrections were based on pinned rAthena source and real wire failures:
struct-only packet lengths, strict unknown-ID framing, six-byte walking position
decoding, correct final movement/action/tick mappings, and avoiding false party
acceptance from the creator's own join. Passing limbs also require live receive
threads. Seven independent offline protocol regression tests passed.

Test SQL readback showed both fixture characters were originally unseeded level
one novices, with no Basic Skill rows and separated spawn cells. The isolated
`seed_test.sql` updates only SpikeBot01/SpikeBot02 to job level 10, Basic Skill 9,
and adjacent Prontera cells; its exact records were read back. Human accounts,
production worlds, and the rest of the native database were not reset.

The legacy table is not an exhaustive current packet implementation. Self movement
arrival, combat, loot, NPC/quest actions, and further packet families remain
acceptance work. See the spike README for source paths, byte sizes and commands.

## Inference services

Both Heavengraph HTTP health endpoints (8091 Flash / 8092 full Clef) returned
healthy responses during recovery. Archived `bench_flash.txt` and `bench_27b.txt`
were inspected before updating the shared benchmark table:

- Flash: p50 **1118ms**, p95 **3363ms**, 20 singles; best batch-8 **8773ms**.
- Full model: p50 **3575ms**, p95 **5766ms**, 20 singles; best batch-8 **28588ms**.
- The archived first-call timings are requests against loaded models, **not**
  model cold-start measurements. Hosted batch data is sequential and is not
  directly comparable to these concurrent batches.

The local ROCm child process was terminated with its failed delegate. Files/logs
remain, but no local 8093/8094 listener was observed. No new local GPU viability
claim is made.

## Remaining evidence

Read-only audits were dispatched for build-source/skill/equipment accuracy and
for real runner/dashboard integration. Do not infer missing combat, command
execution, persistence, real build initialization, or E2E acceptance from the
passing mock tests. The current goal statuses intentionally remain partial.

## Completed classic and integration audits

The classic catalog is not mechanically accepted. Twelve templates were audited;
old tests even required an illegal DEX adaptation. Reported blockers include
nonexistent/accessory and class/slot-invalid equipment, missing rebirth/first-class
transitions, unavailable/overlevelled skills, omitted prerequisites and discarded
skill levels. Unsubstantiated market prices must not become NPC-price substitutes.
Corrective TDD is assigned; no live character initialization is authorized.

The runner/dashboard audit found mock-only Rust transport, incompatible wire
contracts, commands that only log rather than reach agents, missing attack/loot
and reliable vitals/perception, send-based E2E evidence, and unsafe shared-native
seeding. The earlier RAM-only memory finding is superseded in part by the newer
host-memory integration checkpoint; native restart acceptance is still pending.

Parent reproduced the unsafe E2E/seeding entrypoints with side-effect spies, then
blocked default main() calls and direct apply_sql. Three RED/GREEN safety tests
pass; both actual CLI entrypoints now exit 2 with a blocked diagnostic. No
container/server/database was started or changed. The legacy implementations are
quarantined for scoped repair, not exposed as accepted test entrypoints. Exact
world/account ownership and isolated test-volume reset remain unimplemented;
full gameplay E2E and dashboard acceptance remain separate work.
