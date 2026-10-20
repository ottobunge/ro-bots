---
title: Historical offline checkpoints — October 5, 2026
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [ops, testing]
---

# Historical offline checkpoints

The following text is preserved verbatim from [[goals-ledger]]. It records earlier
snapshots, including findings then pending which later work may have resolved.
It is not the current approval/disposition list or evidence of native acceptance.
See the current [[goals-ledger]] and [[recovery-validation]] before resuming work.

- Previous complete parent `task check` checkpoint: **260 tests / 92.58% coverage**,
  before the concurrent repair slices. Audit was green; one Starlette warning.
- New parent full `task test`: **489 passed, 65 subtests, 93.21% coverage**.
  Full `task check` previously failed on 84 Ruff/80 typing issues in three
  protocol test files. Completed test-only cleanup reports zero scoped findings,
  preserving 79 tests and 65 subtests without config/production changes. Those
  historical blockers are superseded by the integrated checkpoint below.
- New parent scoped verification: **145 tests passed**, covering completed
  shutdown/journal repairs, memory integration, and WorldFeed. Five feed tests
  cover reconnect-after-last, retention follow, concurrent identity allocation,
  post-eviction resume, and immediate bounding. Scoped Black/Ruff/mypy pass.
- Directory-entry sync, hard-link/descriptor cleanup, and session-note-failure
  shutdown have scoped independent core approval. WorldFeed allocates locked lifetime-monotonic IDs, not retained
  array positions. Feed IDs are not durable across host restart, and evicted
  events remain unrecoverable. No whole-dashboard transport acceptance is implied.
- Identity migration, persisted summaries, and native restart/human-memory
  acceptance remain unresolved. No exactly-once retry or physical power-loss
  guarantee is made. Full combined quality gates must be rerun after edits settle.
- The second-cycle protocol review rejected L3-TEMP; the user authorized exactly
  one additional cleanup repair. Parent verified 138 protocol/compiler tests
  plus 65 subtests. Final `temporary-handshake-cleanup-review.json` now passed
  scoped offline; parent matched all 34 source/dependency fingerprints.
  Temporary ownership, origin preservation and retry/PASS prohibition are accepted
  only within that supported contract. No new native smoke or further repair cycle.
- Mechanics first-fix review now passed all four reviewed defects; parent matched
  all 29 fingerprints. Real formulas, compatibility and executable builds remain open.
- Final core second-cycle review independently resolved all three original
  interruption/cleanup defects. Approval was withheld solely for concurrent
  WorldState dependency drift (CORE-SECOND-CYCLE-004); transient intermediate
  roster errors are not claimed to persist. Completed WorldState hash
  `01dcd22c...` and unchanged core files were frozen for explicit read-only
  revalidation. That independent review now **passed** 170 guarded tests plus
  real-journal and lock probes; parent matched all 15 source/test hashes.
  CORE-SECOND-CYCLE-004 is closed for scoped core invariants only, not population,
  gameplay, durable summaries or repository-wide approval. No third repair occurred.
- Rust first-fix review independently approved exact escaping, checked overflow
  and persistent warnings, but RWF-POP remains PARTIAL for Python resource bounds.
  Core/POP frozen reviews completed; a new strict-TDD feature now targets Python
  worst-case allocation bounds before RNG, generation or aggregate mutation.
- Real HTTP/SSE and ruleset-specific metadata are compiled/offline tested, not
  gameplay acceptance. Python commands still do not execute through AgentHost;
  character creation remains disabled and no live smoke rerun is claimed.

### Integrated offline checkpoint (2026-10-05)

- Parent `nix develop -c task check`: **591 tests, 65 subtests, 93.44% coverage**;
  all configured Python quality gates passed. Dependency audit: no known
  vulnerabilities found. One existing Starlette TestClient warning remains.
- Parent Rust `dashboard:check` passed fmt, Clippy, **37 tests**, dependency
  audit, unused-dependency check and documentation build. Evidence is compiled
  Rust, Python serializer fixtures and isolated loopback, not real game/UI/Docker.
- Catalog integration RED/GREEN: both actual pre-re/re inputs crashed on unknown
  market-tier comparison; consumer now excludes unknown prices from affordable
  goals without inventing prices. Fifteen focused tests passed.
- Core repair hashes (four files), protocol repair hashes (13 files) and both
  catalogs' YAML hashes match their reports. Parent evidence is saved in
  `run/reviews/integrated-offline-checkpoint.json`; independent core/protocol,
  mechanics and Rust reviews are running. Passing gates are not reviewer approval.

### Population-configuration checkpoint (2026-10-05)

- Configured generation now honors independent friend-group/solo counts and
  both friend-size bounds; configured group IDs remain distinct when labels
  repeat. Default legacy generation remains compatible.
- Reproduced bound-memory detachment on regeneration; host-bound rosters now
  refuse regeneration until account/memory reconciliation exists. This is a
  guard, not a live character-generation executor.
- Parent scoped verification: 80 tests passed, including 11 population cases;
  scoped Black/Ruff/mypy and diff checks passed. Full offline `pytest tests
  --no-cov`: 589 tests and 65 subtests passed with the existing Starlette warning.
  No new coverage measurement or all-gates-green claim. Independent review pending.
- Exact total-agent allocation, live roster reconciliation and generation of
  real characters remain open; no new native, database or reset effects occurred.
- Original independent review rejected **POP-001**: binding could win after
  regeneration admission and then be overwritten. The first-cycle correction
  now shares a lifecycle lock for binding validation/install/ownership and the
  final regeneration guard/full commit. Parent verified **140 scoped tests**,
  all eight report hashes, and diff checks. The fixer reports a full 608-test,
  65-subtest / 93.49% gate; parent has not re-certified that full snapshot.
  User-authorized final verification now passed 143 scoped tests and accurate
  static/diff checks; all 16 fingerprints match the prior 14-probe snapshot.
  POP-001 is independently approved at that frozen snapshot only. The new Python
  allocation-limit feature will require fresh review; no old approval is inherited.
  Individual reads exclude half-commits, but multi-getter HTTP serializers can
  still span two completed unbound generations; full HTTP snapshots are not atomic.
- `task world:inspect` now provides an actual read-only resource listing;
  parent execution found zero labelled test containers and no exact test volume
  on the configured engine. No provisioning/reset is implied. Lifecycle/E2E
  task descriptions now explicitly say BLOCKED and advertise no bypass.
  Eight new task regressions plus safety guards/planners: 90 scoped tests passed.

### Prior recovery checkpoint

- `nix develop -c task check`: 211 Python tests passed, 91.65% coverage; all
  configured quality gates green. `task audit`: no known vulnerabilities found.
- A buffered TestClient GET to infinite `/feed/events` was the actual suite hang.
  Fixed the offending test; bounded generator/SSE tests remain.
- Spike 003 previously reported two four-limb PASS runs in 13.26s / 13.25s;
  seven old regressions passed. Independent review reproduced blocking data
  loss, identity, duplicate-dispatch and party false-positive defects. Those
  results are not protocol acceptance. All six rejected files were unstaged,
  retained on disk, and not committed; corrective TDD slices are dispatched.
- Previous delegates stopped on provider billing errors; files were recovered
  rather than treating failed summaries as completed work.
- Both read-only audits completed and rejected acceptance. The memory gap in
  the earlier runner snapshot is partially superseded by shared persistent host
  wiring; other dashboard/commands/combat/build/E2E/isolation gaps remain.

## Next acceptance frontier

1. Incorporate the two audit reports; fix exact integration and build defects.
2. Exercise an isolated scheduled native agent using real Clef, observe it through
   the real WorldFeed/dashboard, and verify operator commands reach it.
3. Implement/verify real combat, loot, navigation/arrival, quest and mechanics
   adapters rather than counters or fake world events.
4. Prove memory persistence, human interaction/contribution, multi-character
   sessions, autonomous groups/guilds, and WoE incrementally.
5. Validate complete clean-world E2E and volume isolation without touching human
   accounts or named production worlds.
