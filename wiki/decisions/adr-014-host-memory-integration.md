---
title: Shared host memory and fail-closed journal ownership
created: 2026-10-05
updated: 2026-10-05
type: decision
status: proposed
tags: [architecture, ops, testing, events]
---

# ADR-014 — shared host memory and journal failure boundaries

This addendum extends [[adr-013-durable-agent-journals]] without rewriting its
accepted historical checkpoint. Acceptance remains in [[goals-ledger]]; this is
not completion of [[adr-004-isolated-agents-optchat-memory]].

## Decision

- Opt in through an explicit `--memory-root` per world. No implicit shared
  filesystem root; ephemeral defaults remain for callers without one.
- Own one Memory per persona and share it with the scheduled agent, brain, and
  inspector. Include bounded private context in both Clef requests and free-form
  LLM escalation. Heard chat enters that persona's memory before reply selection.
- Serialize durable append/local-history commit, complete view/zoom snapshots,
  summary construction, and close with a per-log reentrant lock.
- Reject public or foreign-owned roots/files and nonregular journals. Walk each
  directory component with no-follow opens and open the file relative to the
  retained directory descriptor; checking a textual path alone is insufficient.
  This is scoped storage ownership, not an OS sandbox for same-user agents.
- Validate notes before mutation. Validate existing history before a first append,
  require a terminated record, and require an actual integer schema version.
- Do not acknowledge short writes or failed fsync. Poison that writer so further
  reads/appends fail until it is closed and the uncertain disk state is inspected
  or reopened. An unacknowledged record might still exist after an I/O failure;
  this does not provide exactly-once retries or automatic corruption repair.
- Join agent and inspector workers before closing storage. A failed session-note
  write must not leave clients or other journals open; errors must be reported
  after cleanup, without pretending the session note was saved.

## Evidence and frontier

Parent execution on October 5, 2026: `nix develop -c task check` passed **260 tests,
92.58% coverage**, including formatting, lint, strict typing, dead-code,
complexity, duplication, and security gates. `task audit` reported no known
vulnerabilities. One existing Starlette TestClient deprecation warning remains.

`tests/test_host_memory.py` exercises shared ownership, bounded isolated Clef and
LLM context, fake-client disconnect/reconnect, host reconstruction, explicit
world roots, initialization failure cleanup, and worker/inspector joins.
`tests/test_memory_journal_failures.py` adds nine review-driven RED/GREEN cases.
Original filesystem/process tests and concurrency tests also pass.

These are offline and local-filesystem results. Native-game restart/human-memory
acceptance, persisted summary caches, and identity migration remain pending.
Directory-entry durability and hard-link/descriptor boundaries need additional
review. The session-note-failure cleanup requirement above is **not implemented
at this checkpoint**; a separate bounded TDD slice owns that repair.

No power-loss or exactly-once claim is made. Mocked fsync tests are not physical
power-loss tests. The broader combat/loot, builds, real dashboard controls,
guild/WoE, and clean-world E2E criteria remain separate acceptance work.
