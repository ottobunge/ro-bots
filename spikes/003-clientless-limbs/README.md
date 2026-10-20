# Spike 003 — clientless player limbs

## Status: repaired offline; live acceptance remains unverified

The original harness reported two native-server runs on October 5, 2026. These
historical records are retained, **not revalidated by this repair**. Review found
that a stale two-member roster or an accepted result for a wrong nickname could
satisfy the old party limb. Those reports do not establish current invitation
acceptance, nor do they validate a general live adapter.

| Limb | Historical run 1 | Historical run 2 | Original reported evidence |
|---|---:|---:|---|
| Chat relay | PASS, 1.02s | PASS, 1.01s | B received A's message on `0x008d` |
| Movement visibility | PASS, 1.11s | PASS, 1.11s | B observed A's `0x09fd` destination |
| Sit/stand | PASS, 1.31s | PASS, 1.31s | B received action types 2 then 3 on `0x08c8` |
| Party | PASS, 1.81s | PASS, 1.81s | `0x0ae4` named SpikeBot02; `0x02c5` result=2; roster |

Historical totals were 13.26s and 13.25s. No new game connection, native server,
provider, or SQL execution was performed for this repair. Deterministic tests use
synthetic packets, a fake monotonic clock, and offline seed snapshots. They are
not live protocol/database acceptance evidence.

## Second bounded protocol repair cycle (offline only)

The obsolete `scripts/probe_map.py` and `scripts/gen_packetdb.py` now import
without connections or source evaluation and exit nonzero when invoked. They
have no legacy implementation/credential fallback. Use the guarded fixture
harness or the strict `packetdb.py` parser instead; neither is authorization to
run a live smoke.

`tests/test_protocol_rereview_repairs.py` covers the seven rereview blockers:
account/wire actor identity (including a wrong-actor negative), exception-class
independent 30-second failed-handshake boundaries across attempts/limbs,
unconditional participant cleanup, preserved origin exceptions, sparse wire
character slots, and native walking names. Cleanup failure or retained resources
invalidates evidence and permanently prohibits subsequent limbs for that budget;
failed readers/sockets stay referenced rather than being reused. Cleanup
classifications and exception notes omit exception messages/credentials.
`tests/test_temporary_handshake_cleanup.py` extends that boundary to temporary
login/character transports: ownership and framing remain until socket cleanup
returns normally; interrupted or failed cleanup blocks reuse, retries and PASS.
All owned temporary/map transports and readers receive independent cleanup
attempts. This is a cooperative cleanup contract, not protection against process
termination/power loss or proof of kernel descriptor release by an arbitrary
transport abstraction.

The pinned compiler oracle hashes `config.log`, `common/packets.hpp`, and
`map/packets_struct.hpp`, then uses the actual MAIN 20180704/pre-renewal defines.
It includes the full common header and unaltered target map struct excerpts
(not a successful full map-header build). Verified layout: CHARACTER_INFO
size 155, name@88, CharNum@118; walking size 110, AID@5, GID@9, MoveData@63,
name@86; spawn size 103/name@79; idle size 104/name@80. The old walking-name
fixture was corrected without weakening its name assertion. Actor size metadata
now uses these native sizes. Manifest FIFO opening is nonblocking and fails the
regular/private-file check.

```sh
nix develop --offline -c uv run --offline --no-sync pytest -o addopts= -q \
  tests/test_protocol_rereview_repairs.py tests/test_client_protocol.py \
  tests/test_limb_evidence.py tests/test_packet_conditions.py \
  spikes/003-clientless-limbs/test_packetdb.py
```

Independent parent rereview is still required. Any further blocking review in
this second bounded cycle requires explicit stop/escalation, not another
unbounded fix loop. Native `0x083e` refusal decoding remains unsupported and
fails closed. Party freshness still uses tuple identity: possible allocator ID
reuse can exclude new evidence (a false negative); a future monotonic sequence
repair is not implemented here. No packet-causal proof, credential rotation,
SQL acceptance, live gameplay, or unrelated working-tree acceptance is claimed.

## Explicit private fixture scope

There are no login/password defaults in `test_limbs.py`. The operator must supply
an owned, regular, private manifest (mode `0600`, no symlink ancestors). Keep it
outside the repository in a controlled private directory; never put credentials
in CLI flags, shell history, reports, or commits. Required JSON fields:

- `schema`: integer `1`; `isolated_disposable`: boolean `true` (explicit opt-in).
- `login_host`: literal loopback IP; `login_port`: explicit integer port.
- `accounts`: exactly two distinct pairs, each with operator-supplied `username`,
  `password`, exact-case `character`, positive integer `account_id` and `char_id`.
  Wire strings must occupy 1–23 UTF-8 bytes, without NUL.

Connected account/character IDs must match BOTH manifest pairs before limb
mutations. Character/map-server redirects must also be loopback. Loopback and
opt-in cannot prove real-world isolation or disposable ownership: the operator
must verify that scope, never infer it from familiar names or target humans.
The manifest reader rejects symlinks observed at inspection; an operator-controlled
private directory is required (ancestor traversal is not a race-proof openat walk).

## Offline verification (safe; no live actions)

From the repository root:

```sh
nix develop --offline -c .venv/bin/pytest tests/test_limb_evidence.py -v
nix develop --offline -c python3 spikes/003-clientless-limbs/test_packetdb.py
```

New regressions cover stale party evidence, wrong recipients/invitations, exact
fixture IDs, loopback redirects, private/isolation configuration, overall deadline
exhaustion, lock-aware retries across limbs, receive errors, and seed
ownership/offline/engine mismatches. The independent client regression file is
separate from the repository's main pytest testpaths.

## Seed preparation: render only, no automatic execution

`scripts/seed_fixture.py` has **no database execution API**. It requires the private
manifest and an explicit `--servers-stopped` assertion for rendering. Game servers
must actually be stopped, not merely characters disconnected: `char.online=0`
cannot detect sessions held in server memory. Offline snapshots are preflight
models only, never authorization to skip transaction-time checks.

```sh
# Operator-produced JSON snapshot; no database connection.
nix develop --offline -c python3 spikes/003-clientless-limbs/scripts/seed_fixture.py \
  --fixture "$PRIVATE_FIXTURE" --snapshot "$PRIVATE_SNAPSHOT"
# Prints guarded scoped SQL WITHOUT passwords. Do NOT pipe to mysql.
nix develop --offline -c python3 spikes/003-clientless-limbs/scripts/seed_fixture.py \
  --fixture "$PRIVATE_FIXTURE" --render --servers-stopped
```

Snapshot fields: `engines` maps `login`, `char`, `skill` to engines; `login` contains
`account_id`/`userid` rows; `char` contains `char_id`/`account_id`/`name`/`online` rows.
Each fixture account must own exactly ONE character. Wrong IDs, case, ownership,
missing rows, extra characters, online state or non-InnoDB engines fail preflight.
A snapshot can be stale or forged: the SQL repeats authoritative checks.

`seed_test.sql` is a **MariaDB anonymous compound block**, not portable MySQL SQL.
It refuses missing scope, locks and verifies BOTH pairs under SERIALIZABLE before
any fixture write, and rolls back/signals on mismatch or SQL failure. It checks
`login.userid`, exact `char_id`/`account_id`, binary case-sensitive `char.name`,
`char.online=0`, and single-character account scope. Only then does it seed job
level 10, Basic Skill id 1 level 9, and neighboring Prontera cells. Readback is
checked before commit and printed afterward. No account creation, password changes,
global resets, or party SQL. Run only in a dedicated SQL session, without
`mysql --force`, concurrent schema changes or other fixture writers.

**Source authority/blocker:** local `rathena/sql-files/main.sql` defines ownership,
`char.online`, and the account-id index. Its `login`, `char`, `skill` defaults are
**MyISAM**. START TRANSACTION does not make those writes atomic. This seed refuses
them and never converts engines. A separately authorized disposable InnoDB fixture
is needed. SQL parsing/execution, rollback and concurrency have NOT been exercised
against MariaDB in this repair; Python preflight/static SQL checks do not prove them.

## Live smoke entry point (NOT run during this repair)

Only after the operator verifies the isolated disposable fixture and its seed:

```sh
timeout -k 3 65 nix develop --offline -c python3 -u \
  spikes/003-clientless-limbs/test_limbs.py --fixture "$PRIVATE_FIXTURE" --budget 59
```

One monotonic budget (default 59s, maximum 60s) spans connects, limb polling,
cooldowns and retries. Login-lock results 2/8 are classified; known or conservatively
lock-capable failures require at least 30s before reconnect, including subsequent
limbs. If the delay cannot fit, no connection retry occurs. Successful teardowns
impose a shared 3s reconnect cooldown. OS scheduling, process startup and blocking
teardown are not hard real-time guarantees; external timeout is separate containment.
The client must implement `connect(deadline=absolute_monotonic_float)`; no unbounded
legacy fallback. A dead thread, `rx_error`, or `dispatch_errors` forbids PASS.

## Packet version and source authority

The historical native build's `rathena/config.log` recorded
`-DPACKETVER=20180704 -DPRERE`; do not infer compiled flags from default headers.
The inherited `packetdb.py` numeric table is a historical **20211103 snapshot** with
20180704 MAIN corrections, not an exhaustive regenerated/validated table.

Registrations come from `clif_packetdb.hpp`, then final `clif_shuffle.hpp` mappings.
Struct-only lengths also require `src/map/packets.hpp`, `packets_struct.hpp`, and
`src/common/packets.hpp`. Numeric registrations alone cannot validate them.

| Operation | Historical tested wire ID / length | Trap |
|---|---|---|
| Move | `0x035f`, 5 bytes | Final `WalkToXY` mapping |
| Sit/stand | `0x0437`, 7 bytes | Reply source is account ID |
| Tick | `0x0360`, 6 bytes | `0x0363` is DropItem |
| Party create | `0x01e8`, 28 bytes | Wait async ack/roster |
| Party invite | `0x086d`, 26 bytes | Exact-case name[24] |
| Party reply | `0x02c7`, 7 bytes | uint32 party ID + accept byte |
| Party config | `0x02c9`, 3 bytes | Not 2 |
| General config | `0x02da`, 3 bytes | Not 2 |
| Attack range | `0x013a`, 4 bytes | Not 2 |
| PIN status | `0x08b9`, 12 bytes | May arrive with PIN disabled |
| Skill list | `0x010f`, variable | MAIN differs from newer RE |
| Self movement ack | `0x0087`, 12 bytes | Framing is not arrival tracking |

Other historical corrections: `0x0141`, `0x080e`, `0x0acb`, `0x00bd`, `0x0110`,
`0x0a30`, `0x02c5`, `0x0105`, `0x0107`; `0x0a0d` has a total-length word.
Consult per-override source structs. `0x0986` is not a party opcode.

## Party evidence and remaining limits

Leave persisted fixture parties via `0x0100`, create a unique name (`0x01e8`), wait
for `0x00fa` result 0 and creation roster, invite exact B (`0x086d`), then require
a **fresh B `0x02c6` containing that party name and a nonzero party ID** before
replying `0x02c7`. Local `rathena/src/map/clif.cpp` documents that `0x02c6` carries
a PARTY NAME, not the inviter nickname despite the client's attribute name.

PASS requires inviter A's post-reply `0x02c5` result 2 for exact B AND post-reply
`0x0ae4` with exact B account/character IDs, character name, current party name,
and online member flag. Cached rosters and creation-time joins cannot pass.
Only records appended after `party_reply` returns qualify; a very fast valid
response may be excluded (conservative false negative). Packets have no invitation
nonce: this is correlation in a fresh unique isolated party, not a cryptographic
causal proof against arbitrary delayed/injected traffic. Bounded logs may also
lose evidence. The final fixture party persists; next runs leave via protocol.

- Login lock authority: `rathena/src/login/login.hpp` defines `AUTH_TIMEOUT 30000`;
  `loginclif.cpp` documents results 2/8 and schedules that timeout.
- Sitting and party creation require seeded Basic Skill; chat is range-limited.
- Movement uses a neighboring cell other than B's occupied west cell; walkability
  and robust navigation/arrival tracking remain outside this smoke harness.
- `RBUFPOS2` destinations span bytes 2–4 of six-byte move data, not a second
  independent three-byte PosDir. The historical (165,145)->(168,145) decoder bug
  remains a separate regression in the client tests.
- No claim of autonomous grinding, inventory farming, quests, guilds or WoE.
