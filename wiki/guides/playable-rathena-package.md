---
title: Separate pinned runnable rAthena package
created: 2026-10-06
updated: 2026-10-06
type: guide
status: proposed
tags: [rathena, ops, testing]
---

# Explicit runtime selection, not gameplay acceptance

This separate `nix/playable-world` package leaves the accepted
[[native-runtime-root]] and [[rathena-nix-package]] artifacts unchanged.
[[adr-019-simple-volume-world-isolation]] governs deployment: ordinary Compose
projects and separate named volumes, **not** a custom manager, receipt catalog or
publication protocol prerequisite.

## Artifacts and build

Only five public tiny-flake files are imported into Nix. The lock is an exact
copy of `nix/runtime-core/flake.lock`; the source remains revision
`e985006171d2eb320ee512a653f4c83aea3d81b6`, NAR
`sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`.

From this checkout, build the explicit public directory only:

```sh
nix build --offline --no-write-lock-file --cores 4 --max-jobs 1 \
  --no-link --print-out-paths \
  "path:$PWD/nix/playable-world#playable-rathena" \
  "path:$PWD/nix/playable-world#docker-image"
```

Built artifacts and exact file hashes/sizes are in
`run/reviews/playable-rathena-package.json`. The archive is a **Docker archive**,
not an OCI-layout tar. Its layers contain the native package and its public Nix
runtime closure only; no project checkout, SQL, accounts or private runtime
configuration is bundled. Public runtime NPC/db/config assets are also **not**
bundled here.

The package contains actual `libexec/rathena/{login,char,map}-server` ELFs and
compiled profile evidence under `share/rathena-playable`. The generated flags and
four native profile oracles confirm MAIN/pre-re, PACKETVER 20180704, PIN support,
compiled packet obfuscation disabled, no RE/ZERO/Renewal. This is not parity proof
with an earlier fixture's runtime policy. Renewal is not implemented.

## Native contract

- Exact `--help` or `--version` alone exit successfully before initialization.
- Exact `--check-runtime-root ABS` validates/binds the filesystem directory and
  exits before initialization. It is **not** configuration or world validation.
- No `--runtime-root` startup selection returns 78, preventing accidental launch
  from a store/CWD directory. Malformed/duplicate custom flags and invalid roots
  return 2, with generic errors that omit paths/configuration values.
- Explicit `--runtime-root ABS` is the intended runnable route. The root must be
  a literal absolute ASCII path, no dot/dot-dot/empty components or symlinks,
  owned by the current effective UID and exactly 0700. Directory-FD binding and
  inode/path readback precede Core status, malloc, SQL, timers, sockets, configs
  and role initialization; native argv[0] relocation is removed.
- Only the custom flag/value pair is removed. Original native role arguments,
  argc, argv[0], trailing null and the original role parser remain intact.
  Original Core initialization/run/finalization and failure returns are retained;
  the native startup tail is byte-equal to the pinned source.

These directory checks are a local caller-trust rule, **not** an adversarial
ownership/exclusion guarantee for a world volume. No authenticated receipt is
required. Do not run the valid startup route until its exact world/SQL scope is
separately authorized.

## Image mount/identity contract

The image uses `User=10000:10000`, `WorkingDir=/world`, and ordinary volume
`/world`. Its entrypoint is the package's `login-server`; empty `Cmd` means the
unconfigured default refuses startup 78. A future authorized Compose service
selects its role entrypoint and supplies `--runtime-root /world/runtime` explicitly.

`/world/runtime` must already contain prepared runtime assets/private configs,
with directory owner matching container UID 10000 and mode 0700. Volume ownership
preparation is a separate bootstrap step; the image does not silently chown,
initialize SQL, invent credentials, or create accounts. Rootless UID mappings
must be handled by that bootstrap. Use a read-only image/store with writes confined
to the ordinary world volume.

[[private-rathena-runtime]] documents the existing `build_from_bytes` preparation
and public assets source. Its copied offline binaries are not substituted for the
new store ELFs: execute the new package role against the prepared directory.
Actual full native config/NPC/db parsing, database initialization and startup have
not been exercised here; private bundle preparation alone does not prove those
steps succeed.

## Exercised boundary

`tests/test_playable_rathena_package.py` exercises real safe diagnostics in all
three ELFs, positive private-0700 roots from other CWDs/argv[0] spellings,
malformed custom flags, invalid runtime-mode roots, basename rejection, source
drift refusal, compiled profile and offline archive/closure readback.

Using the tiny flake's pinned Python/pytest, with the public checkout's source
path selected explicitly for its shared `conftest.py` (no dependency installation):

```sh
nix develop --offline "path:$PWD/nix/playable-world" \
  -c python3 -m pytest -o pythonpath=src tests/test_playable_rathena_package.py -q
```

The final scoped run passed **127 new package tests plus 133 unchanged offline
runtime-core regression tests** (260 total, no failures/errors/skips), including
120 safe native probes of the new ELFs. Scoped Ruff, Black and strict Mypy checks
of the new repository test file passed. This is not a whole-project configured
gate or independent review.

No valid runtime-mode native process, role CLI parser, SQL, socket/timer startup,
engine load/run, volume/network creation, account writes, provider inference or
gameplay was executed. There is no second independent clean rebuild or
independent acceptance yet. [[playable-world-acceptance]] retains the live-world
milestones; build success and diagnostics do not complete them.
