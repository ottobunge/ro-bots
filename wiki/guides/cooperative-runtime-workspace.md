---
title: Cooperative private runtime workspace
created: 2026-10-06
updated: 2026-10-06
type: guide
status: proposed
tags: [rathena, runtime, offline]
---

# Cooperative private runtime workspace

Related: [[adr-018-trusted-user-local-workspace]], [[runtime-publication-contract]],
[[runtime-publication-journal]], [[runtime-tree-sync]], [[private-rathena-runtime]].

## Scope

`RuntimeWorkspace(root)` is an explicit **new workspace initializer**. The trusted
operator/project configuration chooses the absolute private root. Existing roots
are refused, even empty roots with mode 0700. There is no reopen/recovery API.
Restart cannot adopt directories, replay permission or grant old receipts.

The fixed project marker registers this new source-only workspace under ADR-018's
trusted same-user policy. It is not adversarial authentication. Every same-UID
mutator must cooperate with the lifetime `manager.lock` flock. Private metadata
and retained handles are observations, not a physical construction receipt,
mutation immunity or protection against hostile same-user code.

## Managed publication

`publish_world(world, raw)` accepts only exact built-in string world IDs (`test`,
`debug`, `prod-` followed by 1–14 safe suffix characters) and exact input bytes.
Existing strict decoder and private validation run before intent, allocation or
public-asset reads. There is no caller destination, receipt or trust boolean.

The manager owns transaction/session IDs and journal generation. It attests pinned
public dependencies before intent. The accepted journal durably appends intent
before allocation of `staging/<transaction>/<world>`. The actual existing builder
produces the pinned public bundle and synthetic/private configuration there;
its successful manifest return is required, not an `INCOMPLETE` label or mode.

The manager retains the candidate descriptor, verifies namespace bindings and
public manifest readback, and calls the accepted bounded bottom-up tree sync.
Prepared is acknowledged before the accepted descriptor-anchored libc
`renameat2(RENAME_NOREPLACE)` helper moves into `worlds/<world>`. Both changed
parents, candidate, staging and workspace root are synced; binding and manifest
readback are checked again. The accepted journal then syncs/readbacks committed.
A receipt is returned only after transaction handles close successfully.

The default tree limits remain 8192 entries and depth 32. The real pinned bundle
was exercised within those unchanged limits; exact counts are in the review data.
File appends are not a multi-file atomic transaction.

## Denial and failure

Every receipt is data only: `launchable: false`, `admission_state: denied`.
The source-only publication path does not launch, supervise or admit worlds.
Session/generation values and historical committed rows confer no permission.
Native startup guards, public SQL artifacts and live-resource boundaries remain
unchanged; no engine, volume, socket, provider, SQL or native server was exercised.

Detected binding changes or I/O/cleanup failures poison subsequent publishing.
Before rename, failed candidates remain staged and unpublished. A failed rename
acknowledgement, including collision, is conservatively uncertain. After rename,
final bytes may remain, but no success receipt is delivered. Postcommit cleanup
failure is quarantined. No tree deletion, replacing rename or rollback occurs.
Failure-event append can itself fail: in-memory denial does not assert that an
on-disk marker or quarantine record was successfully written.

Original exceptions retain identity, errno and origin frames; secondary cleanup
must not mask them. Each owned close is attempted once; `cleanup_ownership` and
`cleanup_status` distinguish observed release from unresolved process ownership.
Constructor failures expose ownership snapshots on the original exception as
`workspace_cleanup_ownership`. Repeated `close()` does not retry uncertain FDs.
A retained/unresolved descriptor is not permission to kill/retry/autoexit.

## Evidence and remaining boundary

`tests/test_runtime_workspace.py` includes a real pinned complete bundle positive
control. Other narrow builder callbacks are explicitly synthetic fixtures. Reached
faults use actual owned descriptors and kernel rename/flock; collision sentinels
remain untouched. Tests cover parent/root/journal/tree sync, postcommit cleanup,
registration/current-handle replacement, original failure preservation and restart
refusal. The report records scoped regression counts and static checks; it is
implementer evidence, not independent approval or completion of criterion 8.

There is no recovery/cleanup-handoff executor, live isolation authorization,
SQL bootstrap, admitted runtime executor or playable-world claim. The old failed
reports, IO003 and EARLYCONSTRUCTION are not retrospectively closed.
