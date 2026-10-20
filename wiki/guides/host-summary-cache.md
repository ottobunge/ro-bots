---
title: Explicit host summary cache — offline wiring checkpoint
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [architecture, testing, ops]
sources: [run/reviews/host-summary-cache-wiring.json]
---

# Explicit cache settings

Related: [[persistent-summary-cache]], [[adr-014-host-memory-integration]].

`AgentHost` accepts `summary_cache_world` and `summary_cache_policy`, both
optional literal identifiers. The CLI exposes `--summary-cache-world` and
`--summary-cache-policy`. Both settings require `--memory-root`; an incomplete
pair, missing root, unsafe identifier or non-builtin string is refused before
manifest reads, RNG construction, provider detection or storage allocation.

Identifiers match `[A-Za-z0-9][A-Za-z0-9_-]{0,127}` exactly. No normalization,
truncation, root-derived world name or default policy is supplied. Policy IDs
are opaque labels, not evidence of model/provider identity. The host still uses
`StubSummarizer` with its 120-character limit, not Qwen inference.

With both settings unset, in-memory and raw-journal-only defaults are unchanged.
A configured host adds a separate
`summary-cache/world/persona/policy/nodes.jsonl` beneath its memory root.
The root remains explicitly user-selected per world. Neither the directory nor
the world identifier grants deployment/resource ownership or startup authority.

# Ownership and consumers

One cache-enabled `Memory` is shared by the scheduled agent and brain; the
inspector binds that same facade's `MemoryLog`. Other personas' private notes
and storage envelopes are not injected into the agent's source history.

If cache construction fails, the host attempts to close the already-owned raw
journal. Once `Memory` construction begins, its existing contract owns both
stores, including failed restore cleanup. The host does not close them again.
A later bind/decision/scheduled-agent failure closes the completed facade once.
Population failure attempts cleanup for every previously completed persona.
Secondary cleanup failures do not replace the original object, errno or origin
frame. Diagnostic notes are sanitized and attempted conservatively, including
when `add_note` itself fails.

Disconnect/reconnect retains the same memory and both lifetime locks. Stop
joins agent and inspector producers before closing storage. Normal supported
shutdown permits both locks to be reacquired in another process.

# Evidence and limits

Offline synthetic fixtures demonstrate persisted host reconstruction, zero old
summary calls in a fresh process with an exploding summarizer, missing-node-only
work after append, strict identity/source-binding refusal, persona/world isolation,
and dual-resource lifecycle/construction failures. No real server or provider is
used; this is not player-observed or native reconnect/restart evidence.

The accepted backend's pre-release interruption can still retain descriptors
or flock ownership even after clearing an fd slot. A cleanup attempt or an
incomplete-release note does not prove physical release or recovery. Tests
observe retained locks before explicit harness recovery; no automatic retry,
process kill, cache regeneration or universal release guarantee is added.
Repeated source-prefix hashing remains quadratic and is not optimized here.

Final independent offline review passed **330 distinct cases** (318 selected
regressions plus 12 fresh probes). Parent parsed both JUnit results and matched
all **30 frozen inputs** before scoped acceptance. See
`run/reviews/host-summary-cache-final-disposition.json`.

The completed parent gate passed 1,397 tests + 65 subtests /94.01% coverage.
Accepted scope is optional offline host/CLI cache wiring only; no live inference,
native memory, universal cleanup or world approval. Existing native/world startup,
bootstrap, reset and deployment guards remain unchanged.
