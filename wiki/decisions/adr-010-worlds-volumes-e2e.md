---
title: ADR-010: Worlds, volumes, and the e2e playground
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [ops, testing, architecture]
---

# ADR-010: Worlds, volumes, and the e2e playground

## Context
Otto's criterion 5: a Taskfile task that runs a full e2e test — clean server,
clean default test agents (builds, playstyles, groups), initialized, checked
for goal-directed behavior — doubling as a fast local dev playground; plus
three world classes with isolated volumes (debug / test / production).

## Decision

**Worlds are named, isolated data spaces.** A world = MariaDB datadir +
server logs + agent memory/persistence, all under one volume. Isolation is
enforced at the docker-compose level:

| World | Volume | Lifecycle |
|---|---|---|
| `debug` | `ro-bots-world-debug` | live development; persists across restarts |
| `test` | `ro-bots-world-test` | **wiped + re-initialized on every e2e run** |
| `prod` (nameable) | `ro-bots-world-prod-<name>` (default name `default`) | persists; never wiped by tests |

Volume names are derived from `WORLD=` env (or `--world` arg): compose
templates `ro-bots-world-${WORLD_KIND}` so worlds can't mix data.
`WORLD_KIND` ∈ {debug, test, prod-<name>}.

**Taskfile tasks** (root, delegating to scripts in `scripts/`):

- `task world:up world=debug|test|prod-NAME` — compose up MariaDB +
  rAthena (login/char/map) + WorldFeed server for that world's volume.
- `task world:down world=...`, `task world:wipe world=...` (wipe is
  refused for `prod-*` unless `FORCE=1`).
- `task e2e` — the full criterion-5 flow:
  1. compose up the `test` world clean (wipe → up),
  2. seed default test agents: a fixed seed roster (2 friend groups +
     1 solo, known personas/playstyles), author builds via the stub-or-real
     Clef (configurable; default stub for determinism),
  3. connect clientless bots (spike 003 BotClient) for every scheduled-on
     persona, run the EventDrivenBrain tick loop for N simulated minutes,
  4. **assertions**: bots move (position changes), chat events appear in
     the feed, party formation happened (invite+accept observed), a farming
     plan was authored with a mob target, no brain fell back on every tick,
     escalation_rate recorded and reported,
  5. print PASS/FAIL per check + timings; leave the world running with
     `KEEP=1` for use as a dev playground (`task e2e KEEP=1`).
- `task playground` — alias for `task e2e KEEP=1 world=test` then tail the
  dashboard: the fast dev loop.

**Composition**: the agent accounts for the test world are created
deterministically (SQL seed script) so the e2e is reproducible; the seed
roster uses the same SocietyRoster.build(seed) as the dashboard so
dashboard-generated worlds and e2e worlds have identical shape.

## Consequences
- `task e2e` becomes the gate before any integration commit — the repo's
  full-stack test.
- Prod worlds are structurally protected (no wipe path without FORCE).
- Everything composes from existing pieces: compose (infra), SocietyRoster
  (society), BotClient (protocol), EventDrivenBrain (cognition), WorldState
  (dashboard feed).

Related: [[adr-007-rust-dashboard]], [[adr-008-dashboard-control-plane]],
[[adr-005-society-groups-reputation]], [[adr-001-event-driven-brain]]
