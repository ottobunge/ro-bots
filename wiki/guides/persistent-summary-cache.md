---
title: Persistent summary cache — implementation checkpoint
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [rathena, testing, ops]
sources: [run/reviews/memory-summary-cache.json, run/reviews/memory-summary-cache-parent-verification.json]
---

# Reuse stored nodes, not merely raw notes

Related: [[adr-004-isolated-agents-optchat-memory]],
[[adr-013-durable-agent-journals]], [[goals-ledger]], [[playable-world-acceptance]].

`Memory` and `MemoryLog` now accept an optional `summary_store`. With no cache
configured, existing behavior remains unchanged. `JsonlSummaryNodeStore` provides
private durable nodes for that port. Host factories and CLI wiring were unchanged
in this accepted cache/core snapshot; their integration is a separate pending slice.

## Persistence and source binding

The adapter reuses the unchanged private `JsonlExperienceStore` backend in a
separate `summary-cache/world/persona/policy/nodes.jsonl` subtree. Timestamp-zero,
`other` records are storage envelopes only: they are never agent experiences or
inserted into its raw memory. The payload distinguishes its purpose and identities.

Stored nodes carry coordinates, summaries and a private canonical source-prefix
binding. Explicit world, persona and policy identifiers isolate caches. Integer
and floating timestamps use the same canonical numeric representation. Previously
observed source changes, truncation, contradictory identities and malformed history
are refused; records are not silently erased or rebuilt.

Restore validates complete covered ranges, contiguous per-level prefixes and child
closure. Partial valid caches resume missing nodes. Node durability precedes local
node visibility and tree progress. Uncertain writes poison subsequent summary work
instead of repeatedly invoking the summarizer. Append/view/zoom/close share the
memory lock; cleanup attempts both owned stores and reports incomplete release.

## Bounds

- 8,192 cache nodes; maximum level 20.
- 1,000,000 source notes; maximum 65,536 UTF-8 bytes per source text.
- 4,096 UTF-8 bytes per one-line summary; 16,384 bytes per encoded outer row.
- Policy identifiers are opaque configuration, not proof of provider model weights.

These are finite admission limits, not an unbounded-lifetime or speed guarantee.
The adapter's retained-stream preflight deliberately depends on the backend's
private `_file` implementation; that coupling is part of the review scope.

## Parent verification

All four implementation/core/backend/test hashes matched. Parent reran seven
memory-related test files: **155 cases passed**, combined memory/cache coverage
**91.36%**. The adapter alone covers 183 of 196 statements; the core covers
219 of 244. The implementer's 195-case regression selection is a different scope.

The completed combined project gate passed **1,286 tests + 65 subtests** with
**93.94%** overall coverage, exit 0 in **183.71 seconds**. All **147 named public
code/gate fingerprints** remained stable, also checked after focused tests/audit.
`task audit` reported no known vulnerabilities for its Python dependency scope;
this is not an ownership, lifecycle or native-package security approval.

## Independent scoped acceptance

Independent review passed **210 distinct executed cases**, including **71 fresh
probes**, with no failures or skips. Parent parsed both JUnit batches and matched
all **15 frozen input hashes** before acceptance. See
`run/reviews/memory-summary-cache-final-disposition.json`.

The accepted scope is only the optional adapter/Memory persistence contract.
Measured repeated prefix hashing has quadratic work; the input caps do not make
it inexpensive. The inherited backend can retain writer descriptors/locks on a
pre-release interruption even after clearing its fd slot. Actual retained ownership
was observed before fixture cleanup. Incomplete-cleanup notes do not recover it or
prove release. These limitations are retained, not erased by scoped acceptance.

## Remaining acceptance

Restart tests use local counting/exploding summarizers, not live Qwen/Clef
inference or billing evidence.
Scheduled-host cache construction, CLI configuration, native reconnect/restart,
provider execution and human playtests are unverified. No full OptChat parity or
milestone completion is claimed.

The separate publication journal still has two reached sole-diagnostic interrupt
oracles outside the passing configured suite. Its review, original runtime flaws,
manager deployment and world startup remain blocked; the cache does not bypass them.
