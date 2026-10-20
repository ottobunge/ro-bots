---
title: Public rAthena bootstrap reference assets
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [rathena, ops, testing]
---

# Public rAthena bootstrap reference assets

Related: [[adr-017-default-suppressed-public-bootstrap]], [[isolated-rathena-bootstrap-frontier]], [[goals-ledger]].

**Offline derivation only. No SQL was executed, no world was initialized or reset, and no launch/readiness authority is granted.**

## Source and proof

The only artifact input is the immutable public source
`/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source`, revision
`e985006171d2eb320ee512a653f4c83aea3d81b6`.
The adapter runs exactly `nix hash path --sri` against that fixed source and checks
`sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=` **before reading SQL**.
Every SQL file is then checked against its embedded original SHA256.
There is no source-path, expected-hash, credential-file, SQL connection, engine,
world or account input. It does not depend on a DB image or the runtime builder.

`src/robots/adapters/rathena_bootstrap_assets.py` exposes:

- `derive()` → four public reference SQL byte strings.
- `reference_bundle()` → those bytes plus a JSON-serializable provenance/schema manifest.

These are derive-only APIs. There is no apply/execute/reset CLI, SQL client,
connection, shell interpolation, engine route or launch-script integration.
Publication is deliberately outside this pure API. The exercised publication
created an exclusively new private scratch directory, exclusively created each
file using anchored `O_EXCL | O_NOFOLLOW` file opens, and read every output back
before recording its checksum. It never overwrote an existing destination.

## Exact suppression frontier

The original `main.sql` SHA256 is
`40bafce9c3aa14dd997d911b6dd42151d4b0e7afae9273d1ba96993ffdea1c80`.
Under that whole-file hash guard, a fixed line/span proof validates the one
standard operational `login` INSERT at source line 799: exact table, five-column
header, single statement terminator and unique target occurrence. The statement
values are **[REDACTED]**, never recorded in code, manifest or evidence.

The output removes source byte range **[29900, 30138)**, corresponding to lines
796–799: the statement, the two adjacent public default-account comments (which
expose reusable credentials), and their intervening blank line. Every byte
outside that range is unchanged. All DDL, four clan INSERTs and eight
clan-alliance INSERTs are retained. Missing, duplicated, changed-shape,
cross-target or other changed source is rejected by the full-file hash, rather
than filtered using a general SQL-deletion regex. No target body is retained in
the manifest. The other three files remain byte-identical to the pinned source.

## Observed projections and actual artifacts

The exercised artifact directory is:
`/home/otto/.hermes/cache/scratch/rathena-bootstrap-public-_uev2gnn`.
It contains `main.sql`, `logs.sql`, `web.sql`, `roulette_default_data.sql`, and
`manifest.json`. This scratch handle is temporary; archive it separately if
long-term retention is needed. Checksums/sizes are recorded in
`run/reviews/rathena-bootstrap-assets.json`.

| File | Bytes | Tables | Fields | Engines | Retained INSERTs |
|---|---:|---:|---:|---|---:|
| main.sql | 41703 | 56 | 651 | 53 MyISAM, 3 InnoDB | 12 |
| logs.sql | 7312 | 10 | 98 | 10 MyISAM | 0 |
| web.sql | 1308 | 4 | 17 | 4 MyISAM | 0 |
| roulette_default_data.sql | 5263 | 0 | 0 | none declared | 42 |

The manifest includes every table name, column name, field count and engine,
original/derived public hashes and sizes, and the sanitized suppression frontier.
Tests independently project the actual original source and compare the complete
projection, not merely counts. `login` has 20 fields and **no `online` column**.
The source uses spaced `ENGINE = MyISAM` on two tables; the projection handles
that actual syntax without consuming the following CREATE statement.

Primary-source context: `sql-files/README.md:7–21` names main, web, roulette and
logs for new installations; `:21–51` makes item/mob SQL conditional on
`use_sql_db`. With `use_sql_db: no`, those imports are not required. The actual
SQL readers remain outside this derivation:
`src/login/account.cpp:122–144` establishes a DB connection and removes web tokens;
`src/char/inter.cpp:962–990` connects and initializes inter-server readers;
`src/map/map.cpp:4396–4414` connects the map DB. None was run. See the existing
isolated-bootstrap frontier and authority evidence for broader prerequisites.

## Verification and limits

Strict vertical RED→GREEN was observed for unique default suppression,
hash-guarded ambiguous/changed-source refusal, real artifact/manifest projection,
and sanitized failed-attestation handling. Final scoped suite: **12 passed**;
Black, Ruff, mypy, Bandit, Xenon and Vulture passed without gate weakening.
An actual full `UV_OFFLINE=1 task check` through the pinned offline devShell also
returned success: **884 passed, 65 subtests passed**, total coverage **93.51%**.
It emitted existing FastAPI deprecation and concurrent runtime Bandit nosec
warnings. This is an observed whole-tree gate, not a frozen independent approval
of other writers' runtime changes. This module's fingerprints are recorded.

Static parsing is **not server SQL-parser acceptance** or actual schema creation.
Upstream engine parity remains unchanged: no MyISAM rollback claim, no implicit
InnoDB conversion. The standard server login row is absent; a runtime cannot use
it to authenticate. A separately owned private-account write/readback phase is
still absent and required before authentication. No executor for that phase is
invented here. Fresh-world admission/provisioning, SQL schema/account writes,
launch, gameplay and separately authorized reset remain entirely unimplemented
by this derivation. The existing lifecycle blocks are untouched.

## Independent acceptance

The exact offline reference derivation passed independent review in
`run/reviews/rathena-bootstrap-assets-review.json`:12 repository cases, direct
five-file equality/hash/size readback, full raw DDL/types/index/options preservation,
and adversarial fixed-source/attestation/error probes. Assertion totals in that
report are not test-case counts. Parent reconciled64 recorded inputs/artifacts;
only separately repaired runtime files changed afterwards, and this module has no
dependency on them. Its own source/tests and actual five artifacts still match.

This acceptance excludes SQL execution, database initialization, private accounts,
runtime/DB-image approval, launch and whole-repository acceptance.
