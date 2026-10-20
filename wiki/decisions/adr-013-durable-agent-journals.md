---
title: Durable private experience journals
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, ops, testing, events]
---

# ADR-013 — durable private experience journals

## Context

[[adr-004-isolated-agents-optchat-memory]] models private episodic history,
but the original Memory/MemoryLog existed only in RAM. Schedules and session
notes alone do not preserve a relationship through a host restart.
[[adr-010-worlds-volumes-e2e]] also requires development/test/production worlds
not to share experience histories. See [[goals-ledger]] for full acceptance.

The operator's OptChat source was retrieved through GitHub's gist API after
our page extractor failed:
`https://gist.github.com/VictorTaelin/91837951a5ce5b38f341ec1ba1df6449`.
It specifies durable append-only raw history, a lifetime single-writer lock,
and a separately persisted summary cache. This decision implements the raw
journal boundary only; it does not assert full OptChat equivalence.

## Decision

- Add an `ExperienceStore` Protocol to the memory boundary: `load`, `append`,
  and `close`. Memory and MemoryLog accept an optional store; existing offline
  callers remain in-memory. No filesystem dependency enters the memory model.
- Implement `JsonlExperienceStore(root, persona_id)` as a Linux local-filesystem
  adapter. The operator chooses a **world-specific** root. Each persona gets
  its own file, and each row records both persona ownership and schema version.
- Preserve persona IDs literally; reject path-like or malformed IDs instead of
  silently transforming them into other identities. Do not expose a "load any
  agent" lookup through the agent memory interface.
- Create new roots owner-private and new files with mode 0600. Refuse file
  symlinks. Existing operator-created directories/files are not an OS sandbox;
  their permissions need deployment verification.
- Hold a nonblocking `flock` for the lifetime of the opened journal. Another
  store/process cannot acquire the same journal while its owner is alive.
- Write one complete JSON record, flush, and fsync before MemoryLog adds the
  note to visible in-process history. Storage failures propagate rather than
  pretending an experience was durably acknowledged.
- Validate ownership, note kinds, text, and finite timestamps on restore.
  Damaged/unknown journals fail closed; this version does **not** silently skip
  corruption or automatically repair truncated writes.
- Memory closes its store explicitly. A failed restore releases the writer
  lock, allowing diagnosis/repair/retry rather than leaving a locked file.

## Row format

```json
{"version":1,"persona_id":"p-0","note":{"ts":123.5,"kind":"party","text":"a perceived experience"}}
```

Raw notes rebuild the existing lazy summary tree. The summary cache is not yet
persisted: using an LLM summarizer after restart would repeat summary work.
Persisting summaries and preserving their exact identities/byte budgets is a
separate required follow-up before claiming complete OptChat-style behavior.
The current memory facade also collapses experience text to one line rather
than logging every message/tool event verbatim, another deliberate difference.

## Verification

`tests/test_memory_storage.py` covers the memory port and real filesystem:
reopen/restoration (including UTF-8), a separate Python writer/reader process,
world-directory isolation, path rejection, copied wrong-owner journals,
nonconcurrent ownership, private file creation, symlink refusal, schema/value
validation, failed-sync acknowledgement, and lock cleanup after failed restore.

Full quality gates passed with **232 tests / 91.81% coverage** on October 5,
2026. These results do not prove live runner persistence: AgentHost/WorldState
must still be wired to the **same per-agent** durable Memory instance.

## Integration frontier

1. Thread explicit world memory roots through the host CLI and container mounts.
   Never use an implicit shared root for debug, clean test, and named production.
2. Own one durable Memory per stable persona; share that instance with its brain
   context and inspector, not a separate WorldState-only memory. Define identity
   migration/re-generation behavior before reusing IDs for new personas.
3. Serialize all accesses for a given agent and close journals only after its
   worker stops writing. This adapter's process lock is not a complete host
   concurrency implementation.
4. Verify real connect/disconnect/restart and retained human relationships with
   native clients; test scripts alone are not live acceptance.
5. Persist summary nodes, add explicit crash/torn-write recovery, and evaluate
   large-journal startup cost. No exactly-once retry or power-loss recovery claim
   is made by the current raw journal slice.
