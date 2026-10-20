---
title: Offline private rAthena runtime bundles
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, ops, testing]
---

# Populated offline bundles, not launch authority

This prerequisite supplies real private filesystem trees containing the attested
public rAthena NPC/database/config assets and existing offline package binaries.
It does **not** create a playable world. [[rathena-nix-package]] remains unchanged;
[[playable-world-acceptance]] and [[goals-ledger]] retain all native milestones.

## Separate offline entrypoint

Inside the existing pinned devShell:

```sh
UV_OFFLINE=1 UV_NO_SYNC=1 uv run python -m robots.adapters.rathena_runtime \
  --world test --destination /absolute/private-parent/test \
  --secret-file /absolute/private-input.json
```

`--secret-file -` instead reads bounded strict UTF-8 JSON from standard input;
UTF-16/32 auto-detection is not accepted. CLI path spelling is checked before
constructing `Path`: `/./`, `/../`, repeated separators and trailing separators
are refused before input/public reads. The typed `Path` API can only check the
spelling retained by `Path`; it cannot recover aliases normalized by its caller.
Never place
private values in command arguments/environment. No launcher/default task is
wired to this module. Importing it has no world/network/database effects.

The exact input fields are:

- `server_mode`: only `MAIN-pre-re-20180704`;
- `db_host`, `db_port`, `db_name`, `db_user`, `db_password`;
- `inter_user`, `inter_password`;
- `bind_ip`, `login_ip`, `char_ip`, `map_ip`;
- `login_port`, `char_port`, `map_port`;
- `pincode_enabled`: explicit JSON boolean.

The input file must be an owner-private regular 0400/0600 file, at most 8192
bytes, reached through literal absolute no-symlink paths. Unknown/duplicate fields,
invalid profiles, bool/noninteger/out-of-range ports, invalid identifiers, quotes,
controls and conf/import delimiters are rejected. Endpoint checks are lexical;
no host resolution, reachability, endpoint ownership or isolation is proven.
Native SQL/socket/loopback defaults are not inferred. The strict ASCII input
alphabet makes character count equal byte count: `inter_user` and `inter_password`
are each 1–23 bytes; `db_password` remains 1–32 bytes. Passwords outside these
limits fail before public artifact reads or destination creation, with no values
in errors. The interserver bound comes from pinned `src/char/char_clif.cpp:791–799`
(explicit NUL at index 23 before comparison) and `src/char/char.hpp:163–164`
(24-byte user/password arrays); the login handshake reader is separately visible
in `src/login/loginclif.cpp:397–449`. No credential truncation is performed.
IDs `test`, `debug`, or
`prod-NAME` label the output; these are **not** permission to execute anything.
`NAME` is 1–14 safe ASCII bytes, so the exact emitted `server_name` is at most
19 bytes. Pinned `src/char/char.hpp:165` has a 20-byte array and
`src/char/char.cpp:2941–2942` uses `safestrncpy`; larger labels are rejected before
artifact/directory work, never truncated, hashed or renamed. `prod-default`,
`test` and `debug` remain supported. SQL identity is not derived from display names.
The destination basename must exactly match that label and cannot be in the Nix
store. Existing destinations, symlink ancestors, and overwrite are refused.

## Source-derived configuration and asset closure

Both fixed public artifacts are actually attested with `nix hash path` before
copying; arbitrary local checkouts/private imports are not accepted:

- source revision `e985006171d2eb320ee512a653f4c83aea3d81b6`;
- source NAR `sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`;
- package NAR `sha256-j/yjHMH+WB16iaKl1GEnNpzqfu+EKSgcvPP0NnsrjhA=`.

The compiled profile is read from the attested package's native build evidence:
MAIN/pre-re20180704, no RE/ZERO, compiled obfuscation off, PIN support present.
Runtime PIN policy uses the actual `pincode_enabled` reader in `src/char/char.cpp`.
There is no invented obfuscation runtime key and **no fixture policy parity claim**.

The pinned source has `conf/script_athena.conf` and
`npc/pre-re/scripts_main.conf`, not `conf/scripts_athena.conf` or a generic
`npc/scripts_main.conf`. The selected pre-re primary chain recursively checks
`npc`, `delnpc` and `import` references, rejecting unknown directives, repeated/
cyclic config imports, missing files and outside-source paths. The copied closure
includes assets subsequently removed by `delnpc`; its count is not the final
native active NPC list. Script bodies remain public bytes, never evaluated.

Database assets select common/pre-re files. Only YAML import footers are parsed;
body/script bytes are preserved. Renewal/generator imports are removed, and
missing private custom imports are removed only when a corresponding attested
public template exists. Unknown modes/schema and missing selected dependencies
fail closed. Each omitted public reference is listed in the manifest. No public
SQL schemas, SQL execution, credential defaults or private import templates are
shipped. Native table/body parsing and bootstrap remain unverified.

Battle, script, socket and message imports are resolved from pinned public config.
Localized message bytes are preserved without pretending they are UTF-8. Custom
message/config imports are explicitly removed, not silently tolerated as missing
fallbacks. Map/char/login/inter configs are generated from explicit assignments:
`userid`/`passwd`, role SQL `_ip/_port/_id/_pw/_db` keys, and source reader endpoint
keys. All credential-bearing upstream server configurations are excluded.
Upstream loopback subnet overrides are replaced with an empty LAN policy;
GRF references are empty and `use_grf: no` explicitly selects public mapcache.
SQL gameplay DB source is disabled with `use_sql_db: no`; event SQL logging is
disabled with actual `sql_logs`/logging keys, not an invented logging switch.
These policies do not eliminate the server's operational SQL requirements.

Mapcache layout derives from `src/map/map.cpp`, `src/common/mmo.hpp` (12-byte map
names) and `src/map/map.hpp` (512x512 maximum). The checker verifies file/record
frontiers and decompressed cell lengths, then requires every configured map to
exist in common/pre-re mapcache. This is a narrow offline check, **not** whole
rAthena parser acceptance or executable/gameplay validation.

## Private writes, readback and failure frontier

Directories are 0700; all files, including copied binaries, are 0600. Files are
created exclusively through no-follow directory-fd anchored opens and read back
through retained fds before completion. A deterministic manifest contains hashes
of public assets only: no private config values or credential-derived hashes.
The builder compares generated private file bytes without publishing their values.

An `INCOMPLETE` marker precedes file writes. The opened root is checked against
the post-exclusive-mkdir inode, owner, exact 0700 mode and empty construction
frontier before private writes. A substituted sentinel tree is not adopted or
relabelled. Actual output readback verifies regular files, owner, exact 0600 mode
and created-file inode; a final no-follow tree pass verifies every directory and
file. The requested literal parent/root inode bindings are rechecked before
publication and after publication/descriptor cleanup; retained fds do not alone
prove that the requested pathname still names the bundle.

Failure leaves the owned partial tree; there is **no recursive cleanup or deletion
of pre-existing files**. The original exception identity and traceback, including
`KeyboardInterrupt`, survive independent stream/descriptor cleanup faults.
Cleanup is attempted once, never retried on a possibly released descriptor;
a cleanup error without an origin is a reported failure. A manifest is written
last and read back. If marker unlink, final directory fsync or final close fails,
marker restoration targets the retained owned fd, or a newly opened inode-proven
owned root after the old fd was closed. Replacement trees are never repaired.

This remains completion-marker publication, not an atomic hidden staging rename.
Supported reached faults retain or restore the marker; API failure is never usable
launch evidence. Compound loss of the retained fd/path binding together with a
marker-restoration failure cannot guarantee an on-disk marker: the origin gains
a sanitized quarantine-required note, and this is an explicit residual frontier,
not an approval or automatic recovery claim. Checks are deterministic same-user
interleavings, not arbitrary hostile UID mutation or disk/power-loss durability.

## First bounded corrective cycle

`run/reviews/rathena-runtime-first-repair.json` records reached vertical RED/GREEN
coverage for the eight independent findings and the remaining publication frontier.
Original review/probe files remain unchanged. The scoped run exercised 58 existing
runtime + 27 new failure + 18 package cases (103 passed), genuine synthetic bundles,
original control/import/stream-fault probe bodies and fresh public attestations.
Final whole-project static checks passed; `task check` was terminated at its
240-second bound during the test phase, so no completed whole-suite count or
coverage is claimed. This is corrective evidence awaiting independent review,
not closure/approval of all failure combinations or any native/live milestone.

## Exercised result and exact frontier

`run/reviews/rathena-runtime-first-slice.json` records synthetic-only absolute bundle
paths, public hashes, reader fingerprints, tests and readback results. The synthetic
SQL host/endpoints are deliberately nonoperational; no real credentials were used.
Two worlds use different private configs and physically separate files.

Observed vertical RED→GREEN: missing builder; missing mapcache checks; cyclic config
imports; inherited loopback subnet override. Additional regressions cover real
file/stdin CLI inputs, two worlds, modes, existing target preservation, symlink
ancestors, unsafe fields, missing assets, partial I/O interruption and redaction.
Scoped suite: 40 passed; aggregate new-module coverage 88% (original slice).

`run/reviews/rathena-runtime-wire-fix.json` records the narrowly scoped
RUNTIME-WIRE-001 correction: a real 24-byte API input first failed the expected
rejection assertion, then passed after the two-bound validator change. Added
regressions exercise genuine populated bundles at interserver 23 / SQL 32 bytes,
interserver 24/32/33 and SQL 33 refusals before public assets or destination
creation, and the same boundary classifications/redaction through file/stdin CLI.
The final runtime/package scoped gate passes 76 cases with scoped formatting,
lint and type checks. A whole-suite run passed 878 tests plus 65 subtests at
92.96% coverage; the full static gate encountered the concurrent bootstrap
module/test work, not independent approval of this runtime. Exact snapshot and
concurrency limits are recorded in the correction evidence. All launch blockers
below remain unchanged.

Remaining blockers are explicit in every bundle manifest:

1. Native binaries still refuse all startup with exit 78 before SQL/socket init.
   Their 0600 private copies additionally cannot be executed directly.
2. Native config/NPC/database-body/mapcache parser acceptance has not occurred.
3. Isolated schema/bootstrap and interserver/player accounts are not provisioned.
4. Fresh trusted engine/network/database ownership and offline isolation proof is absent.
5. Exclusive world lock, authorization and trusted launch executor remain absent.

No server, container, SQL connection, schema/account operation, model inference,
live gameplay or lifecycle guard bypass occurred. Successful offline construction
must not be relabeled as a completed native milestone.
