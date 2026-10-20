---
title: Pinned offline rAthena Nix package
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [rathena, ops, testing]
---

# Pinned offline package, not world provisioning

This slice builds real login/char/map ELF binaries and their Nix runtime closure.
**Launch is deliberately blocked in both the native core and package CLI.**
Private configuration validation is not isolation/ownership evidence or permission
to launch, seed, reset, connect to SQL, or bind game ports. See [[test-world-inventory]]
and [[goals-ledger]]. The existing Dockerfile/entrypoint path was not used or changed.

## Reproduce from the tracked root flake

```sh
nix build .#rathena-server --no-link --print-out-paths --cores 16
nix build .#rathena-image --no-link --print-out-paths --cores 16
nix develop -c uv run pytest tests/test_rathena_package.py -v
nix develop -c task check
```

The root nixpkgs lock is unchanged; the existing devShell derivation is unchanged.
All packaging expressions and generated validator text are inline in tracked
`flake.nix`; untracked helper visibility and whole-project path inputs are avoided.
The server source is fetched publicly, never copied from the native working tree:

- revision: `e985006171d2eb320ee512a653f4c83aea3d81b6`
- computed unpacked SRI: `sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`
- upstream `configure` supports `--enable-packetver=20180704`,
  `--enable-prere=yes`, `--disable-lto`, and explicit connector `mysql_config`.
- actual dependencies: zlib, PCRE, MariaDB connector C; bundled upstream
  libconfig/rapidyaml/yaml-cpp build through native Make dependencies.
- no MariaDB daemon, apt/pip/container dependency installs, or SQL fallback.

A native C++ oracle uses defines extracted from the generated map Makefile,
compiles static assertions, then emits evidence: MAIN=20180704, pre-Renewal,
not RE/ZERO, obfuscation disabled explicitly via custom post-defines, and compiled
PIN support present. Runtime PIN policy is not generated in this slice.
The native fixture source retains upstream compiled obfuscation support; its
runtime obfuscation policy was not established by this packaging slice. This
offline package explicitly removes that support to meet the requested no-obfuscation
profile. This difference is documented, not inferred from a profile label.

## Safe offline exercise

Use the printed package path, here called `$PACKAGE`:

```sh
"$PACKAGE/bin/rathena-package" --help
"$PACKAGE/bin/rathena-package" --version
"$PACKAGE/libexec/rathena/login-server" --help
"$PACKAGE/libexec/rathena/char-server" --version
"$PACKAGE/libexec/rathena/map-server" --version
"$PACKAGE/bin/rathena-package" launch map
```

Missing secret input exits 2. Native no-argument execution exits 78. Help/version
are handled **before SQL, socket, timer, config initialization or directory changes**;
the shipped core excerpt proves ordering. The patch supplies an early native CLI
rather than relying on upstream help, which is processed after common initialization.
Even valid private inputs cannot launch: exit 78, executor blocked. No server was started.

`validate --secret-file /absolute/private/file.json` accepts exactly these fields:
`server_mode`, `db_host`, `db_port`, `db_name`, `db_user`, `db_password`,
`inter_user`, `inter_password`. The only mode is `MAIN-pre-re-20180704`.
The file must be owner-private regular 0400/0600, at most 8192 bytes, with no symlink
in any path component. Duplicate/unknown fields, bool/invalid ports, localhost/
127.* native fallback hosts, connection strings, quotes, controls, comments and
unsafe conf delimiters are rejected. Passwords are restricted to 1–32 safe ASCII
characters; identifiers to 1–23 alphanumeric/underscore characters. No values are
printed, rendered into argv/environment, or written to generated runtime files.
No actual secret fixture is supplied by this guide or embedded in the package.

## Built artifacts and checksums

- package: `/nix/store/bnacwjisnzz146j80sdha606j3j96ipc-rathena-server-20180704-e985006171d2`
- package NAR: `sha256-j/yjHMH+WB16iaKl1GEnNpzqfu+EKSgcvPP0NnsrjhA=`
- image: `/nix/store/r7hq750ivzabk9k12icb71fq60nvj72h-ro-bots-rathena-offline.tar.gz`
- image SHA-256: `e1ae45efa2aa26b02d35aa4b7f3563610dedfd6d5029c833abdccfdc19ad95cf`
- compressed image: 108691698 bytes; package NAR: 19896568 bytes;
  runtime closure: 251166152 bytes.

`dockerTools.buildLayeredImage` produces a Docker-archive image, **not an OCI-layout
tar**. Its OCI metadata labels identify the revision; default command is offline
help, nonroot UID/GID 10001, no exposed ports or declared volumes. Archive config
and all layers were inspected with Python without loading/running an engine.
Fixed image creation time supports reproducibility; an independent second clean
rebuild has not been performed.

## Evidence and limits

`run/reviews/rathena-nix-package.json` records exact binary sizes/checksums, source
hash, lock/devShell fingerprints, package closure, and sanitized inspection results.
The package contains 136 files: selected public db assets without Renewal/import
examples, battle/message configs, build proof and license. No local logs, pidfiles,
models, SQL dumps/schemas, private runtime imports, credential-bearing server
configuration, or native checkout modifications are copied. Upstream non-UTF-8
localized message assets are identified in the report and scanned as bytes;
they are public message catalogs, not private config. Compiled upstream credential
literals may remain in unreachable implementations; **no active credential defaults
can initialize** because the native core refuses all startup modes.

Observed TDD: missing package RED→GREEN; missing native/profile evidence RED→GREEN;
missing validator/assets RED→GREEN; missing image RED→GREEN. Final scoped suite:
**18 passed**. Full nonmutating `task check`: **814 passed + 65 subtests, 94.06%
coverage**, static gates passed; one pre-existing Starlette warning.

This is an offline artifact checkpoint, not a playable/launchable world milestone.
Remaining frontier: independently reviewed world launch executor, private runtime
configuration generation, required NPC/world assets, explicit isolated DB schema
and bootstrap, ownership/offline admission, then separately authorized native
acceptance. No lifecycle guards, compose/world scripts, reset/seeder or account
mutation were enabled or changed; no container/world/server/provider was started.

## Independent offline acceptance

`run/reviews/rathena-nix-package-review.json` passed the exact offline contract:
18 repository cases and 172 independent probes, independently reconfigured public
source and all three native role oracles. Parent reconciled 127 reviewed files,
136 packaged files and binary/image/package/source hashes before these metadata
updates. See `run/reviews/rathena-nix-final-disposition.json`.

Two nonblocking boundaries remain explicit: the root-flake comment about fixture
obfuscation has no established runtime evidence, and host validation is lexical,
not endpoint isolation/ownership proof. It accepts some alternative loopback
spellings; no execution authority may be derived from validation success.

Acceptance does not approve launchability, gameplay, native-fixture parity, a
second clean reproducible rebuild or the overall repository. Root packaging and
all native startup guards remain unchanged while private runtime work continues.
