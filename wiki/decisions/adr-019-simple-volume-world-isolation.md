---
title: Simple Compose and named-volume world isolation
created: 2026-10-06
updated: 2026-10-06
type: decision
status: accepted
tags: [architecture, ops, testing]
---

# ADR-019: Simple Compose and named-volume world isolation

- Supersedes [[adr-018-trusted-user-local-workspace]]; related [[adr-010-worlds-volumes-e2e]]
  and [[goals-ledger]].

## Decision

The user clarified: "isolation for the playable worlds should be as easy as
different docker volumes, nothing fancy".

Use the existing rootless Docker-compatible engine and ordinary Compose projects.
Each world has its own named persistent volume containing its database, agent
memory/persistence and logs. Use ordinary per-project Compose networks and explicit
host port selection when worlds run concurrently. Do not build a custom workspace
manager, publication receipt catalog or adversarial same-user security boundary
as a prerequisite for the playable experiment.

| World | Persistent volume | Lifecycle |
|---|---|---|
| debug | ro-bots-world-debug | Preserve across development restarts |
| test | ro-bots-world-test | Clean and initialize for E2E; optionally keep running |
| production, default | ro-bots-world-prod-default | Preserve; never selected by E2E reset |
| production, named | ro-bots-world-prod-<name> | Preserve independently per name |

Validate world names and derive exact project/volume names in one place. The E2E
reset targets only the test project's volume, not all volumes or a shared host
database. Production deletion must be explicitly requested for that exact world.
Keep private configuration out of source control and logs; use real server assets,
correct SQL initialization and actual gameplay checks. These are functionality and
basic operational safety requirements, not a new isolation framework.

## Supersession and limits

This returns world isolation to ADR-010's simple volume design and supersedes
ADR-018's custom cooperative staging/publication manager as a required execution
path. Previously accepted helper contracts and failed review evidence remain
historical component evidence, not blockers requiring that architecture.

The custom workspace implementation is not to be integrated as a prerequisite.
Any completed experimental files can remain for reference without being deployed.
This decision does not claim the existing Compose template is functional or that
worlds have been initialized. It does not execute container or volume changes,
reset any existing world, or establish gameplay acceptance.
