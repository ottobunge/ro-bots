---
title: ADR-016 — Private runtime bundles before isolated world launch
created: 2026-10-05
updated: 2026-10-05
type: decision
status: proposed
tags: [architecture, rathena, ops, testing]
---

# ADR-016: Private runtime bundles before isolated world launch

## Context

[[rathena-nix-package]] supplies pinned public native artifacts, not a runnable
world. Startup is deliberately blocked; NPC/runtime assets and private server
configuration are missing. [[adr-010-worlds-volumes-e2e]] still requires playable
worlds with separate debug, disposable test and named production storage.

A private configuration file or a world label is not proof that a database,
container, network or volume belongs exclusively to this experiment. Read-only
[[test-world-inventory]] does not authorize startup, seeding or reset.

## Proposed decision

Implement a separate offline runtime-bundle builder before enabling launch:

- Consume attested pinned public source and the existing native package, never
  local working-tree configuration or the entire repository.
- Derive configuration keys and NPC/db/config references from actual pinned
  readers and import chains; report unsupported or missing dependencies rather
  than inventing successful completion.
- Require explicit private settings and a bounded world identifier. Never reuse
  upstream operational credential defaults, infer a native SQL connection, or
  print configuration values in evidence.
- Materialize public assets and private configuration outside the Nix store and
  image. Refuse existing destinations, unsafe aliases and cross-world mixing;
  keep directories owner-private and confidential files owner-private.
- Read back the produced bundle and its dependency manifest. Keep private values
  out of the public manifest and document the exact source/compiler/runtime policy.
- Separate successful offline preparation from launch authority. Keep all native
  launch guards, lifecycle/E2E scripts and seeder effects blocked in this slice.

The next launch/bootstrap implementation must independently obtain appropriate
exclusive locking, fresh resource identity/ownership and offline evidence, and
specific authorization for its disposable live target. Fresh initialization and
reset of existing data are separate operations; SQL rollback must not be assumed
for nontransactional tables.

## Verification and ownership

Use vertical RED→GREEN tests with actual private filesystem bundles and explicit
readback, including world separation, missing assets, invalid inputs, alias/mode
refusal and partial-I/O failures. A manifest is not proof that rAthena parsed or
ran the resulting world; that remains a later native acceptance step.

The coordinator owns [[goals-ledger]], scope boundaries and integration gates.
Delegates own disjoint implementation, bootstrap-source reconnaissance and
independent package review. Their summaries are not independent approval or a
substitute for verified artifact handles.

## Status

Implementation and pinned-source bootstrap reconnaissance are delegated.
No runtime-bundle completion, launchability, database mutation or whole-goal
acceptance is asserted. This decision remains proposed until its exact contract
is independently verified.
