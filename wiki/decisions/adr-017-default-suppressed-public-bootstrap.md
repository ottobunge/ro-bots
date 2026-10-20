---
title: ADR-017 — Default-suppressed public bootstrap assets before fresh-world writes
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, rathena, ops, testing]
---

# ADR-017: Public bootstrap derivation is not SQL execution authority

## Context

[[isolated-rathena-bootstrap-frontier]] identifies the exact public new-install
schema and an insecure standard server-account INSERT. Neither the accepted
offline package nor [[private-rathena-runtime]] provisions a private replacement.

The pinned main schema contains 56 tables, including 53 MyISAM tables. Declaring
a transaction does not make those writes rollback-safe. Existing seeder/lifecycle
entrypoints remain blocked; [[adr-010-worlds-volumes-e2e]] is not yet live acceptance.

## Decision

Derive a public, hash-attested bootstrap asset set before introducing a mutating
fresh-world executor:

- Use only the pinned public source and fixed bootstrap files: main, logs, web and
  roulette default data. Do not copy local/private SQL or apply existing-world
  migrations to the fresh baseline.
- Suppress exactly the insecure standard server-account INSERT. Preserve every
  other DDL/static-data statement and reject ambiguous or changed target shapes.
- Record public source/output hashes, table/engine projections and the suppression
  frontier without exposing any operational credential values.
- Produce and read back actual local reference artifacts. No SQL client, connection,
  schema creation, account write, reset, engine or server effect is part of derivation.
- Leave table engines unchanged. Fresh-world writes must be phase-recorded and
  quarantined on partial failure; never assert that MyISAM changes were rolled back.
- Keep a future private server-account insertion separate and parameterized, with
  exact account identity and reader-derived 23-byte interserver field constraints.
  No launch is possible until that account/configuration match is privately verified.

Future execution additionally requires fresh trusted resource ownership, exclusive
admission, exact schema/account readback and specific live-target authorization.
A derived SQL artifact or success marker is not such authority. Existing data reset
is a separate destructive operation, never a fallback from fresh-provision refusal.

## Verification and status

Strict vertical TDD must prove unique suppression, complete DDL/static-data
preservation, source/target drift refusal and actual output-manifest readback.
Lexical/static SQL projections are not native SQL parser acceptance.

Accepted only for the completed pinned public-reference derivation contract.
`run/reviews/rathena-bootstrap-assets-review.json` independently passed12 scoped
tests, exact five-file readback, actual raw DDL/types/index/options preservation
and attestation/error-boundary probes. Source/artifact hashes were reconciled;
unrelated active runtime repairs are not dependencies of this stdlib-only API.
No mutating executor, database bootstrap, admission or gameplay approval follows.
Related: [[adr-016-private-runtime-before-world-launch]], [[goals-ledger]].
