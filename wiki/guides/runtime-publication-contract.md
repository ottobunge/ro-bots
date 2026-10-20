---
title: Bounded offline runtime construction and publication contract
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, ops, testing]
sources: [run/reviews/rathena-runtime-first-repair-review.json, run/reviews/runtime-first-repair-final-disposition.json]
---

# Proposal, not implementation or approval
Related: [[private-rathena-runtime]], [[isolated-rathena-bootstrap-frontier]],
[[goals-ledger]], [[public-rathena-bootstrap-assets]]. Companion:
`run/reviews/runtime-publication-contract.json` contains concrete acceptance specs.
Architecture choice, trusted manager deployment/exclusivity remain unresolved;
no code, tests, existing evidence or accepted ADR changes. Navigation/log
registration is left to the coordinator's separately owned files.

## Evidence and failed contract retained

The completed independent first-repair review has `passed: false`; the final
parent disposition preserves that result despite completed 1047 tests + 65
subtests / 93.58% coverage. This proposal does not reinterpret those gates as
filesystem approval. Exact sources below are repository-relative.

- `rathena_runtime_io.py:76-88` (under `src/robots/adapters/`) calls exclusive mkdir,
  then stat/open. The reached early-construction thread swapped in an existing
  empty same-UID 0700 root before first stat; both observations described the
  substitute and API success followed. No retained creation receipt exists.
- `rathena_runtime.py:198-229` removes `INCOMPLETE` before fallible fsync, close
  and final binding checks. `rathena_runtime_io.py:91-109` can only best-effort
  restore it. Four reached cases left a full unmarked manifest tree while the API
  raised: `fsync-restore-open`, `fsync-moved-restore-open`,
  `released-close-restore-open`, `released-close-binding-lost`. Origins survived;
  foreign replacements were untouched. These are on-disk predicate failures,
  not API successes, credential exposure or launches.
- Retain eight original corrective slices: IO-001 sentinel rejection, IO-002
  path-binding refusal, IO-003 single-fault improvement **not universal closure**,
  IO-004 cleanup-origin preservation, IO-005 metadata/readback checks,
  FIELD-002 native display bound, INPUT-001 raw spelling, INPUT-002 strict UTF-8.
  WIRE-001 remains closed separately. Original failed reports/receipts stay immutable.

## Explicit failure and trust model

Supported failures include write/flush/readback/fsync/unlink/rename/close errors,
interrupts, cleanup double faults, manager death, stale leases and observed path
replacement. Filesystems may refuse **all** subsequent writes; neither a marker
nor a quarantine-record write can then be guaranteed. Never promise every API
error rolled back, successful compensating writes, or automatic tree deletion.
Linux close errors can follow descriptor release: preserve the origin/traceback,
attempt cleanup once and never retry a potentially reused fd. [OS3]

Bound publication to one reviewed local filesystem supporting required directory
sync and nonreplacing rename; refuse unsupported semantics, including an unknown
filesystem, rather than falling back silently. No power-loss/hardware guarantee
is claimed by offline syscall injection; crash/restart denial is required. File
fsync alone does not persist enclosing directory entries. [OS2]

Creation requires a **project-controlled private workspace**, retained manager
parent handles, and a manager-issued scoped lease held from before mkdir through
publication/admission. Refuse arbitrary external parents and existing/adopted
roots, including empty 0700 roots. mkdir returns status, not a created-directory
fd; stat/open cannot establish creation identity if other mutators may intervene.
This inference matches the reproduced gap, not a hypothetical syscall fix. [OS1]

The trusted manager must derive authority from a reviewed deployment: exclusive
manager identity/access policy, controlled ancestry/mounts/ACLs, no shared writable
mount or delegated write handles, bounded registered workers and supervisor-owned
lease generations. Prefer a dedicated service identity isolated from ordinary
project processes; privileged host administration is trusted. Inspect actual
owner/mode/ACL/mount/binding evidence and enforce writer routing/lease revocation.
An arbitrary caller boolean, label, random basename or 0700 is not evidence of
same-UID adversary exclusion. Advisory flock serializes cooperating writers only.
If unaccounted same-UID mutators remain possible, admission is blocked; manager
provisioning/exclusivity is **not established here**. [OS4]

## Two architectures

| Architecture | Contract and cost | Residual boundary |
|---|---|---|
| A: private staging + manager receipt catalog (recommended) | Build under manager staging; verify/sync closure; nonreplacing rename into manager world namespace; sync both changed parents; durable scoped receipt and manager readback. Adds staging/catalog/lease API. | Rename alone does not close post-rename fsync/descriptor/path loss; receipt may be uncertain; restart requires recovery. |
| B: manager-owned in-place tree + external receipt catalog | Keep a permanent advisory partial marker; build at final name; catalog, not marker deletion, commits validated tree. Smaller I/O rewrite, same manager/lease/receipt requirements. | Final namespace exposes partial trees; every consumer must use manager admission; equally uncertain catalog/fsync/close failures. |

Recommend A for a future fresh project-owned-world bootstrap: partial trees are
separate from named worlds, publication never replaces an existing destination,
and ownership/recovery phases align with quarantined nontransactional bootstrap.
Do not use ordinary replacing rename after an existence check: Linux rename can
replace an empty directory. Require tested nonreplace semantics (e.g.
`renameat2(RENAME_NOREPLACE)`), with no unverified fallback. [OS5]
Neither design establishes SQL/network/world authority or fixes hostile same-UID
mutation by itself. B is credible only with the identical admission discipline.

## Phases, commit point and API receipt

1. **prepared**: manager registers transaction intent before allocation; construction
   lease remains valid; complete private tree/readback and bottom-up directory sync
   succeed. Close all construction file/stream handles before publication. Partial
   markers are advisory only; manifest presence/absence does not admit anything.
2. **publication pending**: manager performs nonreplacing rename and syncs changed
   staging/world parents, rechecks fd/path ownership, then writes a transaction-bound
   catalog receipt, syncs its file and enclosing catalog directory and reads it back.
   Durable intent/catalog entries are individually written, never advertised as a
   multi-file atomic transaction. Any unacknowledged step is nonadmitted.
3. **committed**: the manager has acknowledged all required sync/readback/binding
   steps under the lease. This is the defined filesystem commit receipt, not the
   rename instant and not a launch token. A later cleanup or response-delivery error
   can leave a genuinely committed tree while the caller sees failure.
4. **uncertain / quarantined**: failed pending durability, lost ownership/binding,
   expired lease or unresolved cleanup poisons admission. Record when possible;
   if recording fails, deny the entire manager session's affected scope in memory
   and require explicit restart recovery. Never infer safety from missing records.

Keep `commit_state` separate from `cleanup_status` and `admission_state`. A proven
commit followed by unrelated cleanup error remains `committed` historically but
`admission_state: denied` until reconciliation; binding/exclusion loss similarly
revokes current admission without pretending to undo the commit. Unacknowledged
receipt fsync is `uncertain` even if visible bytes say committed. A process crash
loses acknowledgements: a new manager generation denies ALL recovered bundles
until explicit recovery, including apparently committed catalog entries. No
persistent bit can force a write-denying filesystem to remember quarantine.

Trusted offline recovery requires a fresh manager lease/exclusion proof, exact
workspace/transaction provenance, retained-or-reopened no-follow handles and new
binding/mode/owner/closure readback (public attestations, private equality only),
all required sync acknowledgements and a new generation receipt. Missing/stale/
contradictory intent or unknown directories remain quarantined; dev/inode numbers
alone are not durable provenance. Never adopt unknown trees, silently republish,
rewrite foreign paths or delete partial trees. Recovery is an explicit offline
operation, not launch/reset authorization or automatic startup behavior.

## Minimal data/API consequences

- New publication schema 2: `transaction_id`, `world`, `workspace_id`,
  `manager_generation`, `lease_id`, relative staging/final names, observed parent/
  root identities, existing public profile/source/package/asset attestations,
  `commit_state`, `cleanup_status`, `admission_state`, sanitized `reason_code`.
  IDs are opaque manager-issued references, not authority-bearing caller strings.
  Reject unknown/duplicate fields, invalid enums/types, identity disagreement and
  old schema 1 as admission evidence. Never export private bytes/derived hashes.
- Keep content manifest separate from private manager catalog. Manifest records
  public assets plus transaction binding; mutable phase belongs to the catalog.
  Receipts describe observations, not perpetual pathname ownership or live grants.
- Replace Path-only write authority with manager workspace/lease handle plus exact
  world identity. Existing Path entrypoints must fail closed without manager
  resolution; they may remain offline compatibility wrappers, never auto-register
  arbitrary parents. This is a deliberate compatibility break, not a silent pass.
- Preserve CLI raw spelling validation **before** Path conversion, bounded private
  file/stdin inputs and sanitized errors. Typed Path cannot recover normalized
  spelling. CLI 0 means a delivered committed offline receipt only, never launch;
  errors may reference a sanitized transaction ID/state without claiming rollback.
  Preserve exact API origin identity/traceback; attach sanitized phase metadata
  without wrapping away interrupts or claiming metadata persistence succeeded.
- Preserve native inter fields23 / SQL password32 / display label19, no truncation.
  Source-equivalent public assets, omission policy, bootstrap derivation, package
  pins and native startup refusal78 are unchanged. Schema2 control metadata need
  not make a content-only manifest nondeterministic.

## Next implementation scope and concrete RED criteria

Change only the runtime construction/publication slice after contract/deployment
approval: `rathena_runtime_io.py:create_root` becomes manager-scoped allocation;
add retained workspace lease/intent and nonreplace publication helpers; preserve
`write_at/read_at/check_output/close_owned` safeguards and add bottom-up directory
sync. Replace `rathena_runtime.py:198-229` marker rollback with explicit phase/
receipt/admission handling; adapt build signatures and `main` for manager lookup.
Add a narrowly scoped runtime-publication manager/catalog module, not a generic
world executor. Assets/bootstrap/root flake/pins/guards are outside this repair.

Add `tests/test_runtime_publication_contract.py` and extend existing runtime
failure tests without weakening old assertions or modifying archived reviewers.
The JSON companion specifies each reached seam, positive control and expected
RED oracle; it is a test design, **not executed tests**. All cases assert exact
injected origin/traceback when raised, independent unchanged foreign-tree snapshots,
no private output/hashes, and zero launch/SQL/engine/provider effects. Use fresh
owned scratch only, existing pinned offline Nix dependencies, no archived harness
reruns. Missing new APIs alone are not RED evidence: first reach original faults.

Required cases: early pre-stat empty-root swap plus unauthoritative admission;
all four compound publication failures; rename success + parent/catalog sync failure;
commit + released-close error; crash/restart at each publication boundary; lease
loss and stale/forged receipts; nonreplace collision/unsupported filesystem; full
retained corrective regression controls; side-effect-denial guards. Preserve
existing 103-case safeguard coverage; review schema2 path/phase expectation migration
explicitly, then frozen full gates/review. No new fault passes without actual reach.

## Primary OS references (retrieved 2026-10-05)

[OS1] Linux man-pages `mkdir(2)`, SYNOPSIS / RETURN VALUE:
`https://man7.org/linux/man-pages/man2/mkdir.2.html`
[OS2] Linux man-pages `fsync(2)`, DESCRIPTION / ERRORS:
`https://man7.org/linux/man-pages/man2/fsync.2.html`
[OS3] Linux man-pages `close(2)`, CAVEATS / error returns:
`https://man7.org/linux/man-pages/man2/close.2.html`
[OS4] Linux man-pages `flock(2)`, NOTES (local advisory locks):
`https://man7.org/linux/man-pages/man2/flock.2.html`
[OS5] Linux man-pages `rename(2)`, DESCRIPTION / RENAME_NOREPLACE:
`https://man7.org/linux/man-pages/man2/rename.2.html`

All startup guards78, seeding and E2E remain inert until separately proven real
resource authority and explicit live authorization; no proposal field overrides them.
