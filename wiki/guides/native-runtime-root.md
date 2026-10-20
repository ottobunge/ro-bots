---
title: Native filesystem runtime-root diagnostic
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [rathena, testing, ops]
---

# Native filesystem runtime-root diagnostic

This **separate offline package** adapts pinned rAthena Core's working directory.
All native startup remains unconditionally blocked. It is not a runnable world,
private-bundle validator, reviewed launch executor, or gameplay acceptance.
See [[rathena-nix-package]], [[private-rathena-runtime]], and
[[playable-world-acceptance]] for the separate boundaries.

## Actual artifact

- Revision: `e985006171d2eb320ee512a653f4c83aea3d81b6`.
- Public source NAR: `sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`.
- Package: `/nix/store/1sqxljh35rzdnhwn6sviqdjmjxqqrgy4-rathena-runtime-core-offline-20180704-e985006171d2`.
- Package NAR: `sha256-7BkzcAhxDB7kAKmbPULiUlxcFrRhmSCuAdguH3X7pQo=`.
- Three real compiled ELFs: `libexec/rathena/{login,char,map}-server`.
- Exact copied root lock: nixpkgs `a7868a727837f3c09cee2ce0ca671c76b1589fed`.
- No image, configuration bundle, database data, NPC assets, or world provisioning
  was created. Existing package/bundle files and their modes were not modified.

The file manifest, SHA256s, NARs, compiler recipes/oracles, source ordering,
TDD evidence, and sanitized actual native output are preserved in
`run/reviews/native-runtime-root.json` as the original implementation record. Independent offline review passed133 scoped cases and207 probes, including
actual ELF disassembly and calibrated failures/races. Parent reconciled26 frozen
source dependencies and19 artifacts with no mismatch before this acceptance note.
See `run/reviews/native-runtime-root-final-disposition.json`. Acceptance is only
for directory diagnostics; all server/SQL/world startup remains refused.

## Tiny source boundary and reproduction

`nix/runtime-core` contains **only** these declared public inputs:
`flake.nix`, `flake.lock`, `runtime-root.hpp`, `apply-runtime-root.py`,
`profile-evidence.py`. Validate that exact allowlist, ordinary-file status and
absence of symlinks **before every path-input evaluation**. The new lock is an
exact byte copy of the root lock; there is no root relock or whole-checkout path
import, including during attribute lookup.

From the checkout, after the allowlist check:

```sh
nix build 'path:./nix/runtime-core#runtime-core' \
  --no-update-lock-file --no-link --print-out-paths --cores 8 --max-jobs 1
nix develop 'path:./nix/runtime-core' --no-update-lock-file --cores 8 --max-jobs 1 \
  -c pytest tests/test_rathena_runtime_core.py
```

The tiny devShell pins Python, pytest, formatting tools and strace through the
same nixpkgs lock. Published tests can also use the recorded store artifact and
strace path; they do not evaluate/import a whole-root flake or need user-specific
configuration. Temporary synthetic directories live under `TMPDIR`.

## Native contract

- `--help` and `--version`: exit **0**, before initialization. Both deliberately
  describe the offline-only interface and the blocked startup boundary.
- Exactly `--check-runtime-root <literal-absolute-private-directory>`: exit **0**
  only for the filesystem-location diagnostic; otherwise exit **2**.
- Default invocation, unknown/malformed commands, `--serve`, `--run`, `--start`,
  extra arguments and attempted flag combinations: exit **78**, no fallback.
- No environment variable, manifest boolean, configuration value or source flag
  enables startup.

The diagnostic executes `bind_runtime_root` inside the real patched native Core.
That helper replaces the argv[0]-based CWD behavior; it is not a toy model. Role
basename identity remains in `SERVER_NAME`. There is no later `chdir(pwd)` that
could put relative reads back in the store executable directory.

The helper validates raw ASCII absolute spelling before opening: no empty,
dot/dotdot or repeated/trailing-separator components; no canonicalized aliases.
Each component is opened relative to its owned parent fd with directory/no-follow
flags. The final directory must be owned by the effective uid and exactly **0700**,
including absence of special mode bits. It calls `fchdir` on that descriptor,
checks actual `getcwd` spelling and relative `.` device/inode, then reopens the
requested path from `/` and verifies its inode/mode/owner and CWD again. Renamed
or replaced requested roots must not receive diagnostic success.

Owned fds use RAII. Explicit success-path closes are checked; a failed close
refuses success. Ownership is relinquished before close and never retried on
Linux EINTR, avoiding unconfirmed fd reuse. On an existing failure, destructor
close results do not replace the originating rejection; they cannot guarantee
kernel cleanup under arbitrary close faults. No server fallback is possible.

## Executed proof

1. **RED:** scratch-only tracer test failed because the actual new package was
   absent. No production code existed yet.
2. **GREEN:** built all three roles with eight Nix cores; build phase took
   **2 minutes 7 seconds**. The original test then passed six actual role/argv0
   combinations from a different process CWD.
3. Refactored that green tracer to pytest and added regression coverage. **133
   scoped tests passed** before publication; there are no skips or mock ELFs.
4. Nine separately recorded diagnostics exercised each role with absolute-store,
   controlled-absolute and basename-only argv0. Output device/inode matched the
   requested synthetic root, not process CWD or store bin; no raw root path was
   printed and roots remained empty.
5. Native traces for every role observed one `fchdir`, zero network calls and
   zero filesystem writes/mutating calls in the traced diagnostic. No SQL/parser,
   timer, socket or role initialization was invoked. Source ordering independently
   places all returns before those calls.
6. Tests delayed real `fchdir` return and renamed/replaced the requested root:
   all six cases refused. Native openat/fchdir/getcwd/close fault injection also
   refused. Injection counts were calibrated from actual native traces, rather
   than assuming shared-library-loader syscall counts.
7. Native profile oracles compiled and ran using the actual generated **common,
   login, char and map** Make object recipes: MAIN/pre-re20180704, PIN support,
   no Renewal/RE/ZERO, compiled obfuscation off. Labels/default headers alone
   are not the evidence; prior-fixture runtime-policy parity is not claimed.

Final `nix develop -c task check` passed: **1047 tests +65 subtests**, **93.58%**
Python coverage, black and all six configured static gates. The public source/test/
configuration fingerprints were unchanged across the gate (**105 files**).
`task audit` passed with no known dependency vulnerabilities. One existing
Starlette deprecation warning and nonfailing Bandit nosec warnings remain;
this is not whole-project/live-world approval.

In installed `core-start.cpp`, CLI dispatch starts at line335; unconditional
refusal is347, malloc358, SQL363, timer370, socket371 and role initialization377.

## Limits

Filesystem-location proof is a checked snapshot, not a namespace lock, durable
root lease, complete private bundle, configuration/parser validation, endpoint
ownership, trusted service exclusion or launch authorization. A rename after the
last checked syscall cannot be excluded forever. The owner predicate and owned
positive roots are exercised; an independently constructed foreign-owner0700
root was not created, because this worker has no ownership-changing authority.
Strace fault injection establishes rejection, not persistent fd-leak absence.

Full project gates are recorded separately in the JSON evidence, with concurrent
unowned-source drift disclosed. No server, database, container engine, provider,
account, SQL, seeder/reset or existing world was started or changed. A future
reviewed executor must reuse this root mechanism and independently satisfy
[[isolated-rathena-bootstrap-frontier]] and [[goals-ledger]]; removing the refusal
is a separate security-sensitive change, not an available command here.
