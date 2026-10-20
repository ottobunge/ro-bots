---
title: Pinned MariaDB Nix database software image
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, ops, testing]
---

# MariaDB software artifact — offline only

Related: [[isolated-rathena-bootstrap-frontier]], [[rathena-nix-package]],
[[private-rathena-runtime]].

This supplies actual upstream MariaDB software, **not a provisioned world or
permission to launch**. Root server packaging, existing worlds, compose, SQL,
runtime helpers and lifecycle gates are not modified by this slice.

## Build without staging

From the repository root:

```sh
nix build --no-write-lock-file --no-link --print-out-paths \
  path:./nix/db-image#rathena-db^out \
  path:./nix/db-image#rathena-db-image^out
nix flake check --offline --no-write-lock-file path:./nix/db-image
```

Only the new two-file flake directory is supplied as a path input. Never use a
whole-checkout path flake: private configuration, local databases, sockets,
models or journals must not enter the public store. Git flakes omit untracked
helpers; the explicit tiny path works immediately without staging or commits.
The child lockfile is byte-identical to the existing root lockfile, with the
same `github:NixOS/nixpkgs/nixos-unstable` input definition. It does not relock
or extend the root flake or server closure.

Pinned nixpkgs revision: `a7868a727837f3c09cee2ce0ca671c76b1589fed`.
NAR hash: `sha256-KgItSKML8Xvte0B7/uGnBDsYzSnnKHcOaiUbgWBXLXw=`.
Its actual `pkgs.mariadb` is **11.4.12**, not a latest-version claim.

## Verified artifacts

- Package: `/nix/store/jhx2a9k5hyyj9jbn0pvxb53qryfnnda9-mariadb-server-11.4.12`
- Package NAR: `sha256-TjSt9yU5V2TlrgNgGAclzo3HcW1GYl1PtMaN7Ok6pRs=`
- Image: `/nix/store/js40iqnfh3v22c2qclipvwnxrvapnjwv-ro-bots-rathena-db-offline.tar.gz`
- Image SHA-256: `11e59cd5a8ac332e0baf8480a94c8830557f2a0e8d68c4b6ec7a028bfd02aa9c`
- Image size: **168,286,076 bytes**, 32 layers.
- DB runtime closure: 94 store paths, **545,083,640 NAR bytes**; this is
  package closure size, not compressed image size or all image-tool closure size.

The image is a **gzip-compressed Docker archive**, not an OCI-layout archive.
OCI-named labels do not change that format. Its immutable created time is
`1970-01-01T00:00:01Z` (Docker config encodes equivalent `+00:00`). Labels retain
package version, nixpkgs revision/NAR hash, format and offline authority boundary.
The image revision label identifies nixpkgs, not a nonexistent new repository
commit; flake/test hashes are in the companion report.

Actual daemon/client ELF64 x86-64 files, interpreter, dependencies, RPATH,
checksums, layer hashes and package closure paths were read back with Python,
without loading an engine. The three inspected native binaries match layer
bytes. All image store-target links and the native ELF interpreters resolve.
One dependency-provided systemd link points to absent `/etc/environment`; it is
reported rather than copying host configuration. This is not a systemd runtime
image, and no future launch/init behavior has been validated.

## Offline defaults and safe evidence

The image has stable nonroot `10001:10001`, static public passwd/group entries,
working directory `/`, and actual daemon entrypoint with default arguments
`["--no-defaults", "--version"]`. No ports, volumes or healthcheck are declared.
No privilege or capability grant is requested. The archive contains no active
`my.cnf`, user option/login files, initialized datadir, system-table data files,
sockets, pids, private configurations or host data. Upstream public bootstrap SQL
**templates** shipped with MariaDB are software, not initialized system tables.
Coreutils/sed/grep/awk and script interpreters are included for the future trusted
executor; that executor is not part of this deliverable.

Before any native probe, inspect the installed files and exact upstream source:

- nixpkgs `pkgs/servers/sql/mariadb/default.nix` wraps only `mytop`; daemon and
  client are actual ELF files, so no wrapper can prepend a defaults file.
- MariaDB `mysys/my_default.c:284-299,422-455`: `--no-defaults` must be first;
  option-file search is bypassed.
- `sql/mysqld.cc:8252-8264,8786-8789,4091-4105`: version/help set the abort flag;
  nonverbose abort exits before signals, datadir handling, server components and
  networking at lines 5908, 5935, 5986, 5990. Never add `--verbose` casually.
- `client/mysql.cc:1354-1356,2174-2177,2200-2204`: version/help exit during
  option handling before `sql_connect` at line 1383.
- Installed `bin/mariadb-install-db:118,173,276,334`: help exits **1** during the
  first argument parse, before defaults-tool invocation or bootstrap writes.

Only source-proven `--no-defaults --version` / `--no-defaults --help` were run,
with scratch CWD/HOME/TMPDIR, pinned PATH, empty inherited environment, stdin
closed and bounded timeouts. Daemon/client help/version returned 0 and reported
11.4.12; installer help returned its source-defined 1. Every probe left scratch
empty and stderr empty. Raw help was neither printed nor retained: only lengths,
hashes, safe version and exit codes are in `run/reviews/rathena-db-nix-image.json`.
This is source-ordering/empty-scratch evidence, not syscall tracing or proof of
container execution. The repository tests **never invoke a DB tool or engine**.

## Scoped regression checks

Tests-first RED was kept in scratch until both real artifact behaviors were
GREEN, then the same tests were published and re-exercised. RED cases were the
missing child flake and missing image output. Multi-output `^out`, UTC encoding
and absolute/cross-layer symlink parser corrections were not counted as feature
RED. The resulting tests were split after GREEN for static complexity gates.

Use pytest and static tools from the same pinned nixpkgs, not global installs:

```sh
nix-shell --expr 'let
  f = builtins.getFlake ("path:" + toString ./nix/db-image);
  p = import f.inputs.nixpkgs {};
  in p.mkShell { packages = [
    (p.python314.withPackages (q: [ q.pytest ])) p.ruff p.black p.mypy
  ]; }' --run 'PYTHONPATH=src python3 -m pytest -q tests/test_rathena_db_image.py && ruff check tests/test_rathena_db_image.py && black --check tests/test_rathena_db_image.py && mypy tests/test_rathena_db_image.py'
```

Three scoped tests, Ruff, Black, mypy and child `nix flake check` passed. Repeated
cached builds returned the same paths; a second independent clean rebuild was
**not** performed. Whole-suite gates are coordinator-owned during concurrent
runtime/bootstrap changes; this guide does not claim their approval.

## Independent review disposition

`run/reviews/rathena-db-nix-image-review.json` records a passed final offline
artifact contract but an overall **failed** review. Three scoped tests and
independent closure/layer/native-probe checks passed; the coordinator rehashed the
actual archive and confirmed the recorded SHA-256 and168,286,076-byte size.
The134 stable fingerprints describe the review snapshot, not later repository edits.

**DBIMG-SEC-001 remains unresolved:** an earlier whole-root Nix path lookup violated
source-import scope. Its failure does not prove absence of temporary private
reads/copies. Final-artifact checks do not erase that execution-scope breach or
prove zero exposure. This guide remains proposed; no unconditional approval,
initialization or serving permission follows. Preserve the original failed report.
The absent `/etc/environment` dependency link also remains a future-executor concern.

## Remaining live frontier

Pinned MyISAM `storage/myisam/CMakeLists.txt:35-38` declares a mandatory storage
engine; InnoDB source declares a default storage engine. This is source/build
evidence, **not SHOW ENGINES, successful DDL or actual SQL engine readback**.
The pinned rAthena baseline needs main 53 MyISAM + 3 InnoDB tables, log 10 MyISAM
and web 4 MyISAM; retain the nontransactional quarantine requirements in the
bootstrap frontier. No SQL was run here.

Still absent: private identity and secret generation, initialization/bootstrap
route, fixed-world launcher, exact database/world ownership, exclusive lock,
fresh-world authorization, actual engine/schema/account readback, authorized
native game startup and gameplay. Actual raw binary capability does not relax
any existing fail-closed gate. No new live authorization is assumed or requested.
