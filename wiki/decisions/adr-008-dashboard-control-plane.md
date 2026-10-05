---
title: ADR-008: Dashboard as agent-tracking control plane
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, ops]
---

# ADR-008: Dashboard as agent-tracking control plane

## Context
ADR-007 scoped the dashboard as an observer. The requirement is broader:
it is also the **configuration and control surface** for the society.

## Decision
Expand the dashboard (same Rust stack + WorldFeed boundary) with:

- **Configurator**: set agent count, friend-group count, solo count, and the
  friends-per-group range; **Generate** (calls the runtime's roster builder
  with a seed; seeded = reproducible).
- **Tracking**: per-agent inspector gains related events, current goals
  (personal, friend-group, guild), schedule, and the characters the agent
  created (name, class, build — see ADR-009).
- **Edit**: persona fields (name, playstyle, attitude, chattiness, schedule
  windows) editable; changes write back to the runtime.
- **Force actions**: operator can inject commands — force goal change, force
  chat line, force party invite, force disconnect/reconnect (schedule
  override). Commands are audited in the feed ("operator forced ...").
- **Write path**: the WorldFeed contract gains a `Command` API
  (POST /commands: `regenerate_roster`, `edit_persona`, `force_action`,
  `force_schedule`), consumed by the Python runtime. The dashboard never
  writes to the sim directly — same contract-over-coupling rule as before.
- **Deployment**: local-only; Dockerfile (multi-stage Rust build) so it can
  run containerized against a host runtime.

## Consequences
- Force/injection commands must be tagged in logs so experiments can
  separate organic behavior from operator input.
- The command API is idempotent-safe and validated server-side; the
  dashboard is never trusted with simulation internals.

Related: [[adr-007-rust-dashboard]], [[adr-005-society-groups-reputation]],
[[adr-009-character-builds-item-cognition]]
