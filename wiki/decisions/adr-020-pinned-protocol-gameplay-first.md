---
title: Pinned protocol manifest and gameplay-first MVP acceptance
created: 2026-10-07
updated: 2026-10-07
type: decision
status: accepted
tags: [architecture, protocol, testing, ops]
---

# ADR-020: Pinned protocol manifest and gameplay-first MVP acceptance

Related: [[adr-019-simple-volume-world-isolation]],
[[native-qualified-catalogue-readiness]], [[native-packet-sink-closure]] and
[[goals-ledger]].

## Decision and authority

After discussing the faster route, the user explicitly said:
**"I accept your proposed change of course"**.
Exact execution scope is recorded in
`run/reviews/playing-mvp-change-of-course-scope.json`.

For this private-server MVP, use a version-pinned, manually maintainable packet
manifest supported by source inspection, targeted compiler/layout checks and
individual/coalesced/fragmented parser regressions. AI may propose reviewed
interface changes; it must not auto-apply them to live worlds. Trigger maintenance
when intentionally changing the server/client profile or when actual uncovered
packets appear, not on every startup.

Keep the approved compiler catalogue/tracer as audit aids. Do not make extending
a general C++ recognizer or proving every allocator/session/lifetime path a
prerequisite for normal-operation testing in the isolated owned world. Source
assumptions and limits stay explicit; known defects must be fixed, not waived.
This changes the MVP acceptance workflow, not the truth of earlier proof claims.
The canonical uncorrected package remains uncorrected; use the independently
reviewed callback-qualified package for the new live acceptance run.

## First finite acceptance gate

Use the existing two owned non-human, non-GM fixtures. Verify:

1. Scheduled connection and real travel based on each client's received state.
2. A real Clef decision, actual combat damage and XP gain.
3. Actual acquisition of a targeted dropped item, not a request or synthetic event.
4. One real LLM chat escalation through existing configured providers.
5. Scheduled disconnect/reconnect with private experience memory retained.

This closes only the initial playing slice when observed. It does not close the
six full milestones, both-ruleset progression, guild/WoE, dashboard reconciliation,
human-client acceptance or sustained-population/GPU benchmark requirements.

## Deployment boundary

Build/verify/import the existing callback-qualified Docker image, then replace
only the three native roles in `ro-bots-test`, after fresh exact resource and
fixture-account ownership/offline checks. Preserve `ro-bots-world-test`, its
healthy database, fixtures and runtime data. Use ordinary Compose; no custom
world manager or extra publication-proof framework.

No volume/database reset, mass seeding, human/debug/production/unrelated-service
changes, new subscription or unbounded inference is authorized by this decision.
Stop on unexpected ownership, online human/foreign participants, native failure
or uncertain cleanup. Refresh observations immediately before live changes and
verify exact images/mounts/service readiness afterward.

## Protocol safety and limits

- Begin with the known missing `0x00C0` receive registration only. Preserve all
  other mappings and char/login/PIN/outgoing/variable policies.
- Unknown packets still fail closed: no guessed lengths, two-byte fallback or
  catch-and-skip. Add reviewed source-backed entries only after evidence/tests.
- Do not claim layout equals transmission in general, queue acceptance equals
  receipt, or a send/model decision proves damage/XP/loot.
- Keep source/profile/provenance and observation epoch/freshness boundaries.
- Source conditions remain unproven in the formal artifacts. No universal
  C++ memory-safety or all-path theorem is newly asserted.
- Historical rejected snapshots and exhausted repair budgets remain intact.
  This explicit policy change is not a disguised third repair of those tools.
- Dependencies continue through pinned tiny public Nix flakes; private world
  files, models and the whole checkout must never enter the Nix source boundary.

## Consequence

Prioritize a tested runnable world and observed agents. Batch focused protocol
repairs behind a finite source/compiler/parser review rather than repeatedly
expanding generic proof machinery. Broader hardening remains a separate decision.
