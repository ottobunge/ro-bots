---
title: Simple world Compose configuration and routing
created: 2026-10-06
updated: 2026-10-06
type: guide
status: proposed
tags: [ops, testing, rathena]
---

# Simple world Compose configuration and routing

[[adr-019-simple-volume-world-isolation]] selects ordinary Compose projects and
one named volume per world. This implements configuration and lifecycle routing,
**not a prepared playable world or live E2E acceptance**; see [[goals-ledger]] and
[[playable-world-acceptance]].

## Selection and persistence

`python -m robots.adapters.world_compose config [--world debug|test|prod-NAME]`
defaults to debug. `prod` is the sole alias, for `prod-default`. Names are strict
lowercase ASCII components; invalid names are rejected, never normalized.

Project: `ro-bots-WORLD`; volume: `ro-bots-world-WORLD`. No per-production YAML
stanzas or external-volume manager. Compose creates its ordinary project-scoped
default bridge. MariaDB has no published host port.

One volume contains `/db`, `/runtime`, `/manifests`, `/memory/agents`,
`/memory/worldfeed`, `/logs/rathena`, `/logs/agents` and `/logs/worldfeed`.
MariaDB mounts it at `/var/lib/ro-bots`, with
`--datadir=/var/lib/ro-bots/db`; other persistent roles mount it at `/world`.
The official MariaDB 11.4 entrypoint reads the effective command's datadir,
creates it and changes ownership only below that datadir. Its fresh-database
initialization imports `/docker-entrypoint-initdb.d/*`.

## Explicit inputs

Supply `RATHENA_IMAGE` (the new pinned **playable** image), `AGENT_IMAGE`,
`WORLDFEED_IMAGE`, `DASHBOARD_IMAGE`, `WORLD_DB_USER`, and private absolute files
`WORLD_DB_ROOT_SECRET_FILE` / `WORLD_DB_USER_SECRET_FILE` (mode 0600 or stricter).
No password defaults. The MariaDB image uses its official `_FILE` secret inputs.
No legacy rAthena build, source mount, demo module or WorldFeed stub fallback.
Image strings are inputs, not proof of image hashes or runtime behavior.

`WORLD_SCHEMA_DIR` is an existing absolute, **private prepared SQL directory**,
mounted read-only at `/docker-entrypoint-initdb.d` with host auto-creation disabled.
It must hold the reviewed suppressed schemas and explicit private server-account
SQL; directory existence does not attest its contents. SQL preparation belongs to
the separate bootstrap adapter; this module neither writes nor executes SQL.
`WORLD_DB_NAME` defaults to `ragnarok` and must match every prepared runtime DB
prefix and the prepared initialization SQL.

Host ports are loopback-only and selectable independently:
`WORLD_LOGIN_PORT=6900`, `WORLD_CHAR_PORT=6121`, `WORLD_MAP_PORT=5121`,
`WORLD_FEED_PORT=8400`, `WORLD_DASHBOARD_PORT=8401`. Select unused ports for
concurrent worlds and prepare matching advertised server addresses/ports.
CLI preflight rejects negative, injected, non-ASCII and out-of-range port values.

`WORLD_RULESET` is runtime/image metadata (default `pre-renewal`), not an
implemented Renewal build. The supplied role images must support the configured
runtime-root, memory and log paths. WorldFeed's production image must provide
real host integration; `AGENT_WORLDFEED_URL=http://agent:8402` is configuration,
not evidence that a supplied image implements that integration.

## Routes and verification boundary

`up`, `down`, and `wipe-test` require explicit `--world`. `up` uses existing local
images (`--no-build --pull never`). `down` preserves data. `status` scopes Compose
`ps` to the selected project. `--plan` validates inputs and prints argument arrays
without executing them. Config output exposes only project, volume/network names
and named-volume mounts: never environment, images, secret files or raw errors.

`wipe-test --world test` performs Compose `down` **without `-v`**, then
`docker volume rm ro-bots-world-test`. It refuses debug/production, stops if down
fails, never uses force, and leaves any still-mounted volume for the engine to
refuse. It does not initialize, copy runtime files or seed accounts afterward.

Tests exercise real Docker Compose **config only**, with synthetic private secret
files and schema directory. Lifecycle tests use an injected runner: they prove
command routing, not container/volume/SQL operations. The saved review distinguishes
these scopes. One historical test still expects an explicit `world-local` network;
ADR-019 now requires the project-default network, and that old oracle is not
silently weakened.

**Remaining before launch:** host runtime preparation and copying into the chosen
volume, correct image/runtime user permissions, prepared schema/account validation,
real service images and host/dashboard integration, then separately authorized
startup and observed gameplay. None was exercised by this configuration task.
