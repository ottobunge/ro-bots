---
title: Source-only descriptor-relative nonreplacing directory move
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [rathena, ops, testing]
sources: [run/reviews/runtime-publication-io-first-fix-review.json]
---

# Scoped move acknowledgement, not world publication

Related: [[runtime-publication-contract]], [[runtime-tree-sync]],
[[private-rathena-runtime]], [[goals-ledger]].

`move_directory_noreplace(source_parent_fd, source_name,
destination_parent_fd, destination_name)` invokes the actual typed libc
`renameat2(RENAME_NOREPLACE)` binding. An existing target is not replaced; there
is no ordinary-rename, copy, link or delete fallback. Both directory descriptors
are borrowed and remain caller-owned.

Names must be **exact built-in `str` values**, each a single printable ASCII
component of 1–255 bytes. No normalization or identity truncation occurs.
Empty/dot/dotdot names, separators, controls, NUL and non-ASCII are refused.
Strings containing spaces remain literal components, not world identities.

## Subclass finding and closure

The original independent review failed: an in-process string subtype could
replace validated text with traversal bytes through an overridden `encode()`.
That failed review remains unchanged. Parent real-filesystem RED reproduced it;
the minimal exact-type guard now rejects all string subtypes before overridden
methods, descriptor/source inspection or native use.

Fresh first-fix review passed **58 repository cases and 53 independent probes**.
Two of the independent probes calibrate the prior guard on fresh owned fixtures;
these are not recovered historical modules or current-fix successes. Helper
statement coverage is 100%. Real source/destination rejection, retained inode
checks, collisions and process races support the scoped closure.

Parent matched all **14 frozen dependency/report hashes** before acceptance.
Machine-readable final disposition:
`run/reviews/runtime-publication-io-final-disposition.json`.
Broader configured-gate evidence is separately recorded in
`run/reviews/publication-io-first-fix-parent-verification.json`.

## Mandatory limits

- Source namespace control is a prerequisite. The no-follow source-kind check
  is not atomic inode/type binding across an arbitrary same-UID replacement.
- Parent descriptors anchor operations, not requested-path ownership or creation
  provenance. This helper does not create a workspace lease or trusted manager.
- Return means the move syscall acknowledged success, not parent/tree durability,
  completion, rollback, receipt delivery, admission or launch authority.
- Unsupported/error-return branches use calibrated synthetic injections. Actual
  cross-mount or unsupported-filesystem behavior was not claimed as exercised.
- The original runtime IO-003 and early-construction findings remain open.
  No builder integration, SQL, container, account or world startup is authorized.
