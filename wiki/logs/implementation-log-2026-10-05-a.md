---
title: Historical implementation log — A
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [ops, testing]
---

Historical record preserved verbatim below; old checkpoint claims are not current approval.
See [[goals-ledger]] and [[implementation-log-2026-10-05-b]]; current actions are in [[log]].

# Wiki Log

- 2026-10-05: Parent recovered interrupted delegates, fixed the infinite SSE
  TestClient hang, passed 211 tests / 91.65% coverage and dependency audit.
  Added [[recovery-validation]]; corrected [[goals-ledger]] completion overclaims.
  Native four-limb smoke passed twice; recovered archived Heavengraph benchmark
  rows after inspecting raw files and reading service health. Build validity and
  real runner/dashboard integration remain under bounded read-only audit.

> Chronological record of all wiki actions. Append-only.

## [2026-10-05] create | Wiki initialized
- Domain: ro-bots design decisions + concept docs, normative over code
- Created SCHEMA.md, index.md, ADRs 000–003, concepts: decision-flow, escalation-policy

## [2026-10-05] implement | Durable private raw experience journals
- Added [[adr-013-durable-agent-journals]] and recorded criterion 7 in [[goals-ledger]].
- Memory/MemoryLog now accept an ExperienceStore port; the JSONL adapter restores
  notes across a fresh Python process, guards per-persona ownership and paths,
  holds a lifetime writer lock, creates private files, and fsyncs before acknowledgement.
- Tests first reproduced missing persistence, unsafe paths, duplicate writers,
  broad file permissions, symlink following, missing sync acknowledgement,
  copied owner data, invalid note schema, and failed-restore lock leakage.
- Final quality gates: 232 tests, 91.81% coverage; live host wiring and summary-cache
  persistence remain pending. No runtime persistence completion claim is made.
- Read the operator's OptChat source through the GitHub gist API after extractor
  failure. The ADR names deviations instead of claiming complete equivalence.
- Dispatched separate Renewal build research; native pre-Renewal server unchanged.

## [2026-10-05] implement | Serialized memory boundary for host sharing
- Reproduced and fixed append acknowledgement overtaking, duplicate concurrent
  summary construction, and closing storage during an in-flight write.
- MemoryLog now uses a private reentrant lock for durable append ordering,
  complete render/zoom snapshots, summary construction, and journal close.
- 64 focused memory/storage/context/concurrency tests passed. Full task check
  temporarily stopped at Black on the integration delegate's in-progress
  tests/test_host_memory.py; no full green gate claim is made for this checkpoint.
- Delegated strict-TDD host/brain/inspector/CLI wiring, lifecycle cleanup, and
  bounded private context for both Clef and LLM escalation. Native restart
  verification remains after integration delivery; no live acceptance yet.

## [2026-10-05] implement | Shared host memory and fail-closed storage
- Host/brain/inspector share per-persona memory through explicit --memory-root.
  Both Clef and LLM escalation receive bounded isolated context; fake-client
  host reconstruction and worker/inspector shutdown ordering are tested.
- Independent journal review rejected the initial implementation. Reproduced
  and fixed invalid-note acknowledgement, failed-sync continuation, public
  existing paths, symlink ancestors, unterminated tails, noninteger schema
  versions, and short writes. Added nine RED/GREEN regression cases.
- Parent full task check passed 260 tests / 92.58% coverage; dependency audit
  reported no known vulnerabilities. One existing Starlette warning remains.
- Updated goals-ledger and index; preserved accepted ADR-013 and created the
  proposed [[adr-014-host-memory-integration]] addendum rather than rewriting it.
- Dispatched two nonoverlapping TDD slices: shutdown cleanup after session-note
  failure; directory-entry durability, hard-link and descriptor initialization
  boundaries. Full no-secret reports will be stored as private run artifacts.
- No native restart acceptance, power-loss/exactly-once guarantee, full OptChat
  equivalence, or overall experiment completion is claimed. Nothing pushed.

## [2026-10-05] update | Renewal research artifact received and checked
- Registered [[renewal-build-research]] in index and updated criterion 7 in
  [[goals-ledger]]. Twelve provisional archetypes, two per requested playstyle;
  fourteen source references. Zero fully validated executable builds.
- Parent independently confirmed the pinned rAthena revision and all 31 unique
  item ID/Aegis pairs plus 70 unique explicit code/level skill targets against
  local Renewal records. The delegate's reported 71-target total has not been
  independently reproduced; prose aliases and prerequisite completeness still
  require validation rather than promoting a larger count.
- Preserved explicit Devotion, Sacrament, malformed STR, budget and rebalance
  gaps. Local skill data lacks AB_SACRAMENT. No classic catalog, server ruleset,
  bot initialization, database state, or live viability claims were changed.
- Shutdown and journal-boundary follow-up delegates remain pending; this research
  receipt does not complete criterion 7 or the overall experiment.

## [2026-10-05] update | Spike protocol review rejected; commit blocked
- Independent review returned passed=false with security and logic blockers.
  Parent confirmed unchanged staged parser/reader/party paths and unstaged all
  six spike files without deleting them or changing HEAD.
- Downgraded native smoke labels in goals-ledger/recovery-validation to historical
  provisional observations. Old seven-test success cannot validate uncovered
  timeout/coalescing loss, identity errors, duplicate dispatch or stale party evidence.
- Dispatched three bounded, nonoverlapping TDD fixes: packet conditions/native
  registration; client framing/lifecycle/identity/deadlines; harness evidence,
  disposable fixture configuration, seed ownership/offline checks and documentation.
- No native calls, database mutations, new commits or pushes. Independent
  re-review and tightened live smoke remain mandatory before protocol acceptance.

## [2026-10-05] update | Classic/integration audits and emergency world guard
- Both read-only audits rejected acceptance. Classic templates have illegal
  stat/class/skill/equipment choices and unsupported market prices; Rust is
  mock-only with incompatible contracts and commands never reach AgentHost.
- Parent directly reproduced E2E/seeder side effects using forbidden-call spies:
  three tests failed before the guard and passed afterward. Default CLI calls now
  exit 2 before subprocesses or manifest writes; direct apply_sql is blocked too.
  Real CLI invocations verified exit 2. No database/container/server changes.
- Quarantined unsafe legacy routines for scoped repair. Dispatched two bounded
  TDD slices with exclusive files: classic catalog/authoring legality and exact
  world-owned seeding/reset routing. The existing guard tests remain parent-owned.
- Updated goals-ledger and recovery-validation; saved safety/acceptance lessons
  in ro-bots-development. Earlier memory-only audit gap is partly superseded by
  host integration, not by native acceptance. No full-suite count is added while
  concurrent implementers are editing; last complete checkpoint remains 260.
- Overall experiment, real dashboard control, combat/loot, valid initialization,
  clean world E2E and volume isolation remain incomplete. No commits or pushes.

## [2026-10-05] implement | Stable feed identity and completed core repair verification
- Parent read completed host-storage-failure and memory-journal-boundary reports,
  then independently ran the combined core/host/feed scope: 145 tests passed.
  Scoped Black/Ruff/strict mypy and git diff --check are green. Full-tree gates
  are deferred while other owned protocol/build/isolation edits continue.
- New feed TDD reproduced last-event replay, following stalled at the retention
  cap, and concurrent duplicate identity allocation. Fixed with lifetime sequence
  IDs, locked allocation/append/trim/snapshot, and resume after the delivered ID.
  Added post-eviction resume and no-reader retention regressions (five total).
- Completed children added namespace directory sync/hard-link/fd cleanup and
  shutdown cleanup after session-note failures. Producer joins precede release;
  originating errors are reported without acknowledging failed notes.
- Dispatched fresh read-only independent core-memory/shutdown/feed re-review,
  with source hashes and a full no-secret JSON artifact. Approval still pending.
- Updated goals ledger. Feed sequence IDs are process-lifetime, not durable
  restart IDs; evicted history is not reconstructed. No native/gameplay, Rust
  transport, full E2E, physical power-loss or exactly-once acceptance claimed.

