---
title: Data-only publication journal — implementation checkpoint
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [rathena, ops, testing]
sources: [run/reviews/runtime-publication-journal.json, run/reviews/runtime-publication-journal-parent-verification.json]
---

# Historical records are not admission authority

Related: [[runtime-publication-contract]], [[runtime-publication-io]],
[[runtime-tree-sync]], [[private-rathena-runtime]], [[goals-ledger]].

`PublicationJournal` is a source-only local persistence component. It is not
integrated with the runtime builder or a deployed manager. Its schema 1 records
are not the replacement contract's proposed schema 2 publication receipts.

## Implemented API and limits

- Borrow an already-open private directory descriptor; the caller retains it.
- Open the fixed `publication-journal.jsonl` entry with no-follow semantics.
  Check private ownership/modes, regular-file type, single link and inode binding.
- Hold a cooperative nonblocking writer `flock`; serialize calls with an `RLock`.
  Neither mechanism excludes arbitrary same-UID or privileged mutators.
- Require canonical newline-terminated JSON with six explicit fields: `version`,
  `transaction_id`, `world`, `generation`, `event` and `reason`. Validate exact
  built-in input types, supported identifiers and phase transitions.
- Bound records to 4,096 bytes, history to 8,192 records and the file to 32 MiB.
- Append one full unbuffered write; file/directory fsync, readback and binding
  checks precede confirmed memory state and volatile journal-event acknowledgement.
- Poison reached append failures instead of retrying, truncating or repairing.
- Reopen historical records with a new process-issued generation. Previously used
  transaction IDs remain reserved; previous acknowledgements are not recovered.

`acknowledged_in_this_generation()` describes a journal append only. It is not
permission to publish a tree, recover an uncertain transaction or start a world.

### Failure control flow and writer-cleanup ownership

The first repair addresses only `JOURNAL-ACK-001` and `JOURNAL-OWNERSHIP-001`;
it is an implementation change, not independent approval. Ordinary acknowledgement
binding exceptions (including `OSError`/`ValueError`) poison the writer and return
`False`. Nonlocal `BaseException` origins outside `Exception`, including
`KeyboardInterrupt`, `SystemExit` and `GeneratorExit`, poison and propagate the
same exception with its traceback. Subsequent acknowledgement is denied and
appends refuse.

`PublicationJournal.cleanup_ownership` returns an immutable, typed
`JournalCleanupOwnership` snapshot under the journal's `RLock`. It records the
allocated `descriptor`, `owner_pid`, optional `expected_identity` (device/inode),
`close_attempted`, `status` and `observation`. Before close its status is `active`.
Close is attempted once through the unchanged shared `close_owned` helper; a
second `close()` performs no syscall and does not resolve an unresolved status.
The closed flag is a denial flag, **not proof of completed resource cleanup**.

After the attempt, `fstat` reporting `EBADF` produces `released_observed` /
`descriptor_absent`. A still-present descriptor, unknown initial identity,
observed different identity or diagnostic failure produces `unresolved` with
`descriptor_present`, `identity_unknown`, `descriptor_reused` or
`diagnostic_failed`, respectively. These are one-time observations, not continuous
descriptor identity or lock-release proofs. Matching device/inode is also not
authority to retry a close: a descriptor may already have been released and reused.
Diagnostic failures do not mask an already-active primary failure or claim
successful release. A sole nonlocal diagnostic origin (`KeyboardInterrupt`,
`SystemExit`, `GeneratorExit` or another non-`Exception` cancellation) propagates
as the same object with its reached frame, **after** retaining the immutable
`unresolved` / `diagnostic_failed` snapshot. Ordinary diagnostic exceptions such
as `OSError(EIO)` conservatively retain that snapshot without introducing a new
exception. Closed writers deny acknowledgement and append, including after a
sole diagnostic interrupt. The borrowed root remains caller-owned.

The second bounded repair obtains process identity **before** `os.open`.
An interrupt at that explicitly called seam propagates before any owned writer
or journal leaf is allocated; no cleanup capsule is claimed for an unallocated
resource. Later allocated constructor failures retain the handoff below. PID is
snapshot data, not authority over a process. This does not promise atomic
provenance or immunity to interrupts at arbitrary bytecode/allocation boundaries.

If construction fails after allocating the writer, **the same original raised
exception** has a public `journal_cleanup_ownership` attribute containing that
typed snapshot, even if the first file `fstat` failed before identity capture.
An unresolved handoff adds a sanitized note naming this attribute. Callers may use
`getattr(error, "journal_cleanup_ownership", None)` and check
`isinstance(handle, JournalCleanupOwnership)` without retaining a hidden traceback
object. Retain this evidence as pending process ownership; do not treat the public
descriptor number as permission to close it again. Returned objects expose the
same boundary through their property. Snapshots are observations, not live handles
that perform cleanup; reread the property after a close attempt.

No automatic process termination or safe descriptor-retry mechanism is added.
Actual release of an unresolved resource may require controlled teardown by the
caller/supervisor of the **owning process**, with separately established ownership
and authority. Reached tests demonstrate that a fresh independent process remains
locked while an owned synthetic worker retains a pre-release fault, and can reopen
after that worker exits and the kernel closes its descriptors. Fixture-only manual
disposal is not counted as production recovery. This explicit unresolved handoff
replaces an unconditional "every failed constructor leaves zero live descriptors"
oracle; the original failed review/report remains unchanged. It does **not** claim
that the new status physically closes any descriptor.

## Parent execution

Actual parent reruns passed:

- **51 focused cases**, journal statement coverage **94.83%**.
- Configured full `task check`: **1,196 tests + 65 subtests**, **93.75%** overall
  coverage; configured static gates passed, exit 0 in **191.377 seconds**.
- **143 named public code/gate fingerprints** stayed stable. All **104** recorded
  pre-existing Python files also match the implementer's before snapshot.

The initial implementation RED was a missing-module import failure, not a reached
behavior assertion. Subsequent behavior slices have separately retained RED/GREEN
logs. These historical pre-fix implementation and parent passes do not substitute
for independent review. `run/reviews/runtime-publication-journal-independent-review.json`
withheld approval on the two findings above. The first repair evidence is in
`run/reviews/runtime-publication-journal-first-fix.json`. Its independent review,
`run/reviews/runtime-publication-journal-first-fix-review.json`, withheld approval
on sole diagnostic control-flow loss and the post-open process-identity gap.

The second and final bounded repair has reached RED/GREEN evidence for both
findings in `run/reviews/runtime-publication-journal-second-fix.json`.
The final scoped run passes **112 cases** (the unchanged original 73 plus 39 new
cases), with **97.24%** journal statement coverage. Black, Ruff, strict mypy,
Bandit, scoped Xenon and whole-source R0801 return exit 0 without new exemptions.
This is implementer execution evidence, **not independent approval**. A fresh
frozen review remains required; the parent owns the completed combined gate.
No full combined gate was run during concurrent unrelated host work.

## Independent scoped acceptance

Final independent review passed **223 cases**, including **111 fresh probes**,
with **98.16%** journal coverage. Parent parsed the JUnit result and matched all
**23 frozen inputs** before acceptance. See runtime-publication-journal-final-
disposition.json under `run/reviews/`. Original failed reports/oracles remain
unchanged; unconditional zero-live-descriptor cleanup is not retroactively closed.

The accepted contract is historical journaling plus the narrowed observational
cleanup handoff only. `sys.exception()` also includes a caller's active `except`:
close in that context treats it as primary and may suppress a new secondary
diagnostic. No blanket mask-freedom or process-disposal authority is claimed.

## Unaccepted boundaries

The original construction/publication, deployment, recovery and world-admission
requirements remain separate from this accepted data-only component.

Initial workspace construction identity, external pathname/ancestry control,
exclusive manager ownership, builder integration, publication receipts, recovery
and admission are still absent. The original IO-003 and early-construction findings
remain open. All server-start/reset guards remain unchanged; no database, SQL,
container, volume or world was started or changed by this slice.
