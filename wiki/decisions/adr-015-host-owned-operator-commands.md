---
title: ADR-015 — Host-owned operator command delivery
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, events, testing, ops]
---

# ADR-015: Host-owned operator command delivery

## Context

[[adr-008-dashboard-control-plane]] requires operator commands to reach agents,
not just produce dashboard events. Before this slice, Python force_action only
recorded a private note/feed item. Standalone/demo still does; the live Rust
adapter still correctly refuses ForceAction until its separate integration exists.
The scheduled host owns clients, workers and journals. HTTP threads must not
send game packets or mutate the brain alongside its worker.

## Decision

Implement one vertical slice first: an operator chat request for a currently
online, host-owned persona. Other live force actions remain explicitly unsupported.
The standalone/demo note API is not evidence of host execution.

- The host installs a typed command dispatcher into its WorldFeed application.
  No automatic fallback from failed host submission to note-only success.
- Validate persona ownership, action, a bounded safe command identifier and text
  before queueing. Text must obey the pinned client's byte/framing constraints;
  reject invalid control characters, empty payloads and oversized input.
- Use a bounded queue and bounded terminal-status retention. Required identifiers
  make a matching duplicate submission idempotent within the retained lifetime;
  conflicting reuse is rejected. No restart-durable or unlimited idempotency claim.
- Only the agent's owning worker drains its queue and invokes the existing say
  limb. It checks current availability again immediately before dispatch.
- Admission returns **queued**, never applied. Readback distinguishes queued,
  dispatched, failed, cancelled and uncertain. A successful send call is not a
  server acknowledgement, delivery confirmation or a human-visible observation.
- A transport exception may follow partial wire effects: retain uncertainty and
  prohibit automatic retry. A later memory/audit error must not turn a completed
  send into a retryable unsent command. Sanitize failures to classifications.
- Reject submissions after stop and cancel pending work before journal release;
  existing producer joins and interrupted-cleanup ownership remain authoritative.
- Do not hold queue/aggregate locks during transport or private-memory work.
  Agent workers must not acquire the host lifecycle lock that stop holds while
  joining them; tests must exercise shutdown and concurrent submissions.

## Scope and acceptance

Accepted only for the completed **offline host-owned public-chat contract**.
Independent `run/reviews/host-chat-first-fix-review.json` passed 258 scoped cases
and retained 123 stable fingerprints; parent reconciled those fingerprints before
later packaging work. Parent full gates passed 796 tests +65 subtests /94.06%.

Verified boundary: HTTP request → queue → ScheduledAgent.tick → injected client
say, with exact status readback, duplicate/conflict/bounds/offline/stop and actual
private-journal interruption regressions. Interrupted audit/send finalizes the
last-confirmed delivery phase before preserving and re-raising its origin; dead
workers refuse new commands without discarding cleanup ownership. Fake-client
proof is not native gameplay, server acknowledgement or browser integration.

The live Rust adapter stays unsupported until a separate tested translation
supplies command identifiers and preserves delivery provenance. Goal changes,
party commands, schedule overrides, disconnect/reconnect and persona reconciliation
are later slices. No game/world/provider/database effects are authorized here.

Related: [[adr-014-host-memory-integration]], [[goals-ledger]].
