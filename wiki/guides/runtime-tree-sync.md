---
title: Source-only fd-anchored private-tree synchronization
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [rathena, ops, testing]
sources: [run/reviews/runtime-tree-sync.json]
---

# Conditional syscall acknowledgement, not publication

Related: [[runtime-publication-contract]], [[private-rathena-runtime]],
[[goals-ledger]]. This helper is not integrated with construction, publication,
manager admission, native startup or any world executor.

`robots.adapters.runtime_tree_sync.sync_private_tree(root_fd)` borrows a real
integer, non-bool directory descriptor. The opened root and each encountered
entry must belong to the effective UID. Directories require exact 0700 and
regular files exact 0600, including refusal of special mode bits. Symlinks,
FIFOs, sockets and all other nonregular leaves are rejected before opening them.
Files are opened no-follow/nonblocking; directories are fd-relative/no-follow.
No private file contents are read, hashed or emitted.

All regular files receive real `os.fsync` first. A second verified traversal
acknowledges nested directories bottom-up, then the root last. File fsync alone
does not acknowledge directory entries: Linux fsync(2) explicitly requires
synchronizing the directory separately. Primary authority:
`https://man7.org/linux/man-pages/man2/fsync.2.html`.

Return value `None` means only that these calls and supported readback/cleanup
checks succeeded. It is not prepared/complete/committed/launchable status, a
multi-file atomic transaction, a power-loss test or a hardware guarantee.
Unsupported sync/syscall failures have no skip/fallback/pseudo-success path.

## Bounds and observations

The root is depth zero; at most 32 nested directory levels and 8192 total
non-root entries are accepted. Scans also stop after 8192 names per directory.
These fixed limits bound traversal, retained metadata and simultaneously owned
handles, not private file size or synchronization latency. They are deliberately
larger than the current asset closure; tests reach exact and exceeded boundaries
with real fixture directories/files and actual sync acknowledgements.

Observations retain device/inode, type/mode, owner/group, size/link count and
nanosecond modification/change times. Opened descriptors and parent-relative
no-follow stat readback must agree. Directory membership is checked again.
Reached before-open substitutions and post-sync substitutions/metadata drift
fail. Root-path rename/replacement after opening does not redirect access;
replacement sentinels are untouched. Current working directory is irrelevant.
No source URI or root pathname binding is promised.

Checks are not an atomic seal. Arbitrary same-UID mutators can act after the
last observation, and metadata equality is not durable provenance or content
validation. Trusted manager workspace/exclusivity, mutation exclusion and
admission/recovery remain prerequisites, not features of this helper.

## Cleanup and errors

The borrowed root remains open. Each independently owned descriptor/scan gets
one cleanup attempt. A cleanup double fault preserves the active original
exception object and origin frame and adds only a generic note. OSError errno
and identity survive, but filenames and messages are sanitized in place.
Do not publish traceback locals, which necessarily contain private names.

Linux close(2) warns against retrying a failed close because descriptor release
may already have occurred; primary authority:
`https://man7.org/linux/man-pages/man2/close.2.html`.
A test injection that fails before actual kernel release leaves that handle
physically open; the fixture releases it explicitly after verifying independent
cleanup attempts. Injections after actual release return to the measured
`/proc/self/fd` baseline. Neither case permits a blind production retry.

## Independent scoped acceptance

Final review passed40 repository tests and41 fresh independent probes, including
all five previously uncovered statement lines. Repository pytest coverage remains
95.19%; independent line tracing is not a fabricated merged coverage percentage.
Parent matched the exact helper/test/unchanged shared-cleanup hashes before this
acceptance update. See runtime-tree-sync-final-independent-review.json and
runtime-tree-sync-final-disposition.json under `run/reviews/`.

Acceptance is only for the documented source-only synchronization contract.

## Scope remains blocked

Original IO-003 and EARLY-CONSTRUCTION remain unclosed. Existing builder,
markers, manager/catalog/schema, runtime assets, SQL, native startup refusal78
and all world authority are unchanged. Scoped helper acceptance does not
approve any original construction/publication finding or grant launch permission.
