---
title: Isolated rAthena bootstrap — pinned-source implementation frontier
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, ops, testing]
---

# Isolated rAthena bootstrap: implementation frontier

Related: [[goals-ledger]], [[private-rathena-runtime]], [[test-world-inventory]].

**Status: offline design and pinned-source evidence only; launch, SQL writes, reset, and gameplay are NOT authorized or verified.** No engine, SQL client, server binary, world/E2E command, socket, private configuration, provider, or shared gateway was accessed during this review. The new runtime-builder work and the independent frozen package review are outside this report's authority.

## Evidence identities

`S` below means the immutable public source `/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source`, revision `e985006171d2eb320ee512a653f4c83aea3d81b6`. `nix hash path --sri S` actually returned `sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=`, matching `flake.nix:10-16,111`. `R` means `/home/otto/dev/ro-bots`. `P` means `/nix/store/bnacwjisnzz146j80sdha606j3j96ipc-rathena-server-20180704-e985006171d2`.

The machine-readable companion `R/run/reviews/isolated-rathena-bootstrap-authority.json` records exact public schema table/column/engine projections, file hashes, NPC import edges with line numbers, configuration import closure, map-cache hashes and parsed coverage, repository snapshot hashes, and the proposed admission states. This evidence is not an execution token.

Static parsing ran in the existing pinned `nix develop --offline --no-write-lock-file` environment. Nothing was installed globally. `P/share/rathena/build-evidence/map-cppflags.txt:1` reports C++17, `PACKETVER=20180704`, and `PRERE`; its `profile.json:1` reports MAIN 20180704, non-Renewal, non-RE, non-ZERO, packet obfuscation disabled, and PIN-code protocol support present. These are existing package evidence, not a new independent compiler/binary audit. A future runtime package must retain actual compiled-profile oracle assertions; Renewal needs a separately compiled artifact, not a configuration switch. [R/flake.nix:114-175; S/src/config/const.hpp:34-43]

## 1. Fresh schemas, not legacy migrations

For a new named world use **one fresh game schema** for login/character/map/IP-ban tables and **one separate fresh log schema** on the uniquely owned isolated DB instance. The schema names must be explicit and bound to the world/run identity. The current inert plan fixes `ragnarok` and the test world; a new differently named schema is a new contract, not something its caller can substitute silently. [R/scripts/seed_test_agents.py:20-81,206-218]

The exact public baseline is:

| Source file | Destination | Requirement |
|---|---|---|
| `S/sql-files/main.sql` | fresh game schema | All 56 tables; preserve complete current definitions, not a hand-written login/char subset. |
| `S/sql-files/logs.sql` | fresh log schema | All 10 log tables; `loginlog` is at lines 101-108. Login logging and SQL map logging must route here explicitly. |
| `S/sql-files/roulette_default_data.sql` | fresh game schema | Data for `db_roulette`; the default `feature.roulette: on` requires the deliberate data/feature decision. |
| `S/sql-files/web.sql` | fresh game schema | Four web tables for the upstream complete-new-install baseline. No web-server launch is proposed. For a deliberately web-less minimum they can be excluded only with a tested feature/reader audit, not by assuming the README makes them optional. |

Upstream installation documentation identifies the above baseline and marks SQL item/mob databases conditional on `use_sql_db`. Keep `use_sql_db: no`; use immutable shared plus `db/pre-re` YAML/text data. No `item_db*.sql`, `mob_db*.sql`, compatibility views, tools, or dated upgrades are part of this fresh baseline. Dated upgrades are for existing schemas; never run all upgrades against the current main schema. No schema/DB creation or grants occur in `main.sql`; the future provisioner must create and select the exact schemas itself, without a default socket/database fallback. [S/sql-files/README.md:7-51,53-75; S/conf/inter_athena.conf:174-180]

### Never import the standard server login unchanged

`S/sql-files/main.sql:796-799` contains an explicitly insecure standard server-account INSERT. Its login identifier and password are **[REDACTED]**. `S/conf/char_athena.conf` and `S/conf/map_athena.conf:12-14` contain matching public inter-server defaults, also **[REDACTED]**. Public SQL connection identifiers/passwords in `S/conf/inter_athena.conf:33-75` are **[REDACTED]**. The offline package's sparse assets/validator do not provision a replacement account: even syntactically valid private configuration cannot authenticate a character server against a missing replacement login row.

The safest design is a hash-checked, mechanically derived **public bootstrap variant** of `main.sql` that suppresses exactly the one standard `login` INSERT at line 799, leaving the DDL and official clan/clan-alliance data unchanged. Fail if the pinned statement count/shape differs. Do not interpolate secrets into Nix derivations, generated public SQL, output manifests, command arguments, shell tracing, or stdout. After DDL, while all game services remain unstarted and routes inaccessible, insert exactly one newly generated private server identity by a separate parameterized bootstrap operation. Read it back through a sanitized verifier before any launch. A compatibility alternative that imports then replaces the public row has a larger exposure window and should not be the default. Never overwrite an existing row using broad UPDATE/REPLACE/ON DUPLICATE KEY behavior.

Required server row invariants: `login.sex = 'S'`; an explicit small nonnegative server account ID less than compiled `MAX_SERVERS` (5 in `S/src/login/login.hpp:62`), unblocked/nonexpired state, and an exact private identifier/password matching BOTH character and map configuration. Client player IDs must not be taken from this low-ID namespace. Login-to-char admission checks server sex, ID-array bounds and unused slot; map-to-char admission compares the same inter-server credentials. The wire map login truncates identifier/password to 23 bytes; constrain both to at most 23 ASCII bytes for this profile, even though the package validator currently accepts a 32-character inter password. Login DB password storage permits 32 bytes but that is not the inter-server wire capacity. [S/src/login/loginclif.cpp:397-449; S/src/char/char_clif.cpp:786-815; S/sql-files/main.sql:770-794; R/flake.nix:83-90]

Read back the exact server ID, private-identifier equality (boolean only), sex, state, expiry/unban state, and private-secret match (boolean only); assert the suppressed public identity/row is absent and no unexpected `sex='S'` rows exist. Never print credentials, including public defaults. Keep `use_MD5_passwords`/its actual parser key policy consistent with generated account storage; do not run the global password conversion tool. Default player auto-registration remains disabled.

### Engines invalidate the transactional seeder premise

The actual pinned DDL yields **53 MyISAM + 3 InnoDB main tables**, **10 MyISAM log tables**, and **4 MyISAM web tables**. Only main `bonus_script`, `mail`, and `mail_attachments` use InnoDB. `login`, `char`, `skill`, `inventory`, `storage`, account registers, and most related tables use MyISAM. [S/sql-files/main.sql:121,209-296,716-755,770-794,805-856,1045-1052; S/sql-files/logs.sql; S/sql-files/web.sql]

Do not claim BEGIN/ROLLBACK or SELECT FOR UPDATE makes the current cleanup plan atomic. `R/scripts/seed_test_agents.py:175-203` is inert and mentions future transactional row locks; that requirement is not satisfied by the upstream engines. The supplied `convert_engine_innodb.sql` is not comprehensive for all current tables and comments out logs/roulette. InnoDB conversion, if chosen, is a separately reviewed fresh-world schema policy with actual engine readback and real failure/rollback tests; it must not migrate an existing world incidentally.

Prefer retaining upstream engine parity for the first fresh-world provision: write only to a demonstrably new, quarantined, unlaunched world; record each completed phase and actual readback; on partial failure mark it nonlaunchable. Never pretend a partial MyISAM bootstrap was rolled back. Do not destroy it automatically: any removal/reset is a separately scoped authorization.

## 2. Ownership and offline proof

A fresh database identity requires a separate provisioner-owned metadata schema/table: immutable world kind/name, random run ID, exact engine instance/container identity, schema names, source/profile/bootstrap hashes, and completed/quarantined phase. No upstream ownership metadata table is supplied. Credentials/manifests privately stored on the host are not alone proof of DB identity.

Before creating fixtures, prove exact desired account ID AND identifier absent and exact char ID/name/account associations absent. Before editing existing owned fixtures, prove the precise ID/identifier/char ID/name/slot tuple is still owned, there are no extra characters on those accounts, and every affected related record is within the declared scope. `login.userid` has an ordinary index, NOT a unique constraint; always query all matching IDs and identifiers and reject ambiguous/case-colliding matches. `char.name` is unique under the actual schema collation; `char` has only an account index and no account-slot uniqueness constraint. [S/sql-files/main.sql:209-296,770-794; R/scripts/seed_test_agents.py:84-172]

**The upstream `login` table has NO `online` column.** Do not generate a query against an invented `login.online` field. The planner's account `online: False` is an abstract supplied observation, not a SQL column. Account-level offline proof must come from an exclusive no-game-client/no-game-service boundary and, for any running observer workflow, trusted server state. `char.online=0` alone is insufficient: startup/finalization can globally clear it. Character startup also cleans tables and login startup clears web tokens; starting binaries is a mutation, not read-only inspection. [S/src/char/char.cpp:249-255,1259,3151-3157,3189-3277; S/src/login/account.cpp:122-144,151-156,960; R/scripts/seed_test_agents.py:127-172]

For fixture readback require explicit account/character identity and slot; legal class/ruleset, levels, base stats, HP/SP, inventory slots; map/save point coverage and walkability; Basic Skill row sufficient for required sit/chat/party behavior; exact declared skill IDs/levels/flags; only declared inventory/cart/storage ownership; no unexpected party/guild/pet/homunculus/mercenary/elemental relations. Verify affected rows and complete selected field values after every write. A two-table char/login DELETE is not complete fixture cleanup: no cascading foreign-key cleanup is supplied, and relationships are spread across the full main schema. Prefer fresh worlds over deleting persisted fixtures.

## 3. Configuration and assets

### Configuration must be generated as a closed private runtime tree

`P` contains binaries, DB assets, battle subfiles and message files, but lacks the top-level launch configs, `conf/inter_server.yml`, NPC tree and SQL bootstrap. The companion lists the missing launch assets. [R/flake.nix:177-205; P/share/rathena/asset-manifest.json; S/src/common/cli.cpp:23-37]

Ship immutable public assets from **S only**, not the whole checkout or legacy `R/rathena`. Generate private allowlisted configs in an owned no-symlink runtime directory with private permissions. Explicitly cover `conf/login_athena.conf`, `char_athena.conf`, `map_athena.conf`, `inter_athena.conf`, `battle_athena.conf` plus all 18 battle imports, `script_athena.conf`, `log_athena.conf`, `packet_athena.conf`, `subnet_athena.conf`, `maps_athena.conf`, `inter_server.yml`, `channels.conf`, `groups.conf`, `atcommands.yml`, message files, MOTD/help and selected auxiliary files. Do not copy a public connection-bearing config and rely on appended overrides to neutralize every default.

Actual source has missing `conf/import/*` targets in the public checkout; create explicitly empty safe import files or suppress those import edges in the generated runtime config and inter-server YAML. Never copy legacy private `conf/import` or `db/import` content. Verify YAML footer imports across DB assets separately; the companion's generic config closure covers textual `import:` edges, not all YAML semantics. `conf/inter_server.yml` declares ordinary `storage`; its footer imports `conf/import/inter_server.yml`. [S/conf/inter_server.yml:35-46; S/src/char/inter.cpp:861-864,891-892,962-985]

A subtle default mismatch: C++ `cfgFile` starts as `inter_athena.yml` (`S/src/char/inter.cpp:42`) whereas active upstream `inter_server_conf: inter_server.yml` overrides it (`S/conf/inter_athena.conf:178`). The private generated inter config MUST include that override and `conf/inter_server.yml`; omission points at a nonexistent default file and can leave storage mappings missing.

Set every active SQL family explicitly: `login_server_{ip,port,id,pw,db}`, `ipban_db_{ip,port,id,pw,db}`, `char_server_{ip,port,id,pw,db}`, `map_server_{ip,port,id,pw,db}`, and `log_db_{ip,port,id,pw,db}`. Route only to the owned isolated DB identity; logs to the explicit log schema, IP bans to game schema. Web family must be explicit if ever enabled, otherwise forbid launching web. Login loads shared inter config through its own config imports; its account/IP-ban/log readers receive those keys. Keep reconnect bounded/fail-closed at the executor rather than inheriting indefinite reconnect to an unproven identity. [S/conf/inter_athena.conf:33-85; S/conf/login_athena.conf:193-194; S/src/login/login.cpp:730-739,853-903; S/src/map/map.cpp:4380-4413; S/src/char/inter.cpp:962-983]

Explicitly resolve `login_ip`, `char_ip`, `map_ip`, all role ports, `bind_ip` and subnet policy from the private isolated network topology. Login, character and map **advertised client addresses must be reachable from the chosen bot namespace**; publishing loopback host ports does not fix an internal advertised container IP. Never rely on source auto-detection or host-native SQL fallback. Existing compose is a template: mutable image tags, debug default, no schema init mount, legacy Dockerfile, and loopback published game ports do not constitute admitted identities or fresh initialization. [R/docker-compose.worlds.yml:8-55,57-97,142-167; S/src/char/char.cpp:3216-3232; S/src/map/map.cpp:5367-5386]

Explicit profile policies include `use_sql_db: no`, `use_grf: no`, `new_account: no`, PIN disabled for the clientless harness or real PIN support, runtime packet obfuscation policy consistent with the compiled absence, and charset/collation checked against actual server/name constraints. The default PIN is enabled/forced, while compiled protocol supports PIN; changing the policy is not a packet-layout change. [S/conf/map_athena.conf:71-80; S/conf/login_athena.conf:54-56; S/conf/char_athena.conf:214-238; P/share/rathena/build-evidence/profile.json:1]

### CWD is a launch blocker, not a cosmetic wrapper detail

Upstream `Core::start` derives the executable directory from **argv[0] and changes CWD there**, before SQL/socket initialization. Executing `/nix/store/.../libexec/rathena/map-server` from a private runtime CWD still relocates into the store and breaks relative `conf/`, `npc/`, and hardcoded `db/` cache paths. A runtime-capable package needs a reviewed early runtime-root mechanism/patch (or explicitly controlled safe basename argv[0] exec contract), plus tests for actual argv/CWD behavior. Merely `cd` then exec an absolute binary is incorrect. Keep offline-package refusal unchanged. [S/src/common/core.cpp:333-376; R/flake.nix:129-146]

### Ruleset NPC and map cache closure

The map server unconditionally selects `npc/pre-re/scripts_main.conf` when not compiled Renewal; changing the CLI map config does not select a different NPC root. It recursively reads `import` and `npc` directives. The pinned pre-re closure has **540 distinct files, 527 NPC directive edges, no missing referenced files**. The separate Renewal closure has **849 distinct files, 835 NPC edges, no missing referenced files**, but is NOT executable support in P. Both exact path/hash/line-edge manifests are in the companion. Preserve global functions first, shared scripts and the selected ruleset imports in their original order; leave custom/test scripts disabled. [S/src/map/map.cpp:4216-4267; S/npc/pre-re/scripts_main.conf:20-48]

This is static import-closure evidence, not successful native script initialization. A byte scan of selected pre-re NPC files found only `unloadnpc` amongst the searched dynamic file/SQL-reader primitives; it is not a complete proof that OnInit cannot mutate world state. Mixed encodings exist in the broader scripts: preserve asset bytes and avoid silently rewriting them as UTF-8.

With `use_grf: no`, source reads caches in override order `db/import/map_cache.dat`, `db/pre-re/map_cache.dat`, `db/map_cache.dat`, using **literal relative `db/` paths**, not the configurable `db_path`. `db/map_index.txt` is mandatory; import index is optional. Missing map entries/index IDs silently remove maps from the configured set, so a generic readiness line cannot prove a playable map. [S/src/map/map.cpp:3911-3979; S/src/common/mapindex.cpp:131-155]

Public caches were actually parsed/decompressed offline with bounds/length assertions under the x86_64 little-endian source layout (`S/src/map/map.cpp:155-167,3672-3705`; `S/src/common/mmo.hpp:163`): shared cache **1,288 maps**, selected pre-re override **8 maps**. The selected override supplies `alberta`, `izlude`, `morocc`, `prontera`, `prt_church`, `prt_fild05`, `prt_fild08`, `prt_in`; it is NOT a replacement for the shared cache. Package both caches, the shared index, shared/selected-ruleset databases and `conf/maps_athena.conf`. An explicitly empty import cache is optional; suppressing it may produce a misleading fatal-level missing-file message that actually continues. Do not fetch proprietary GRFs or generate maps from unavailable game assets for this path.

## 4. Trusted admission states and authorization boundary

Proposed state machine (not implemented):

1. **OFFLINE_VALIDATED**: immutable source/profile/bootstrap/config/NPC/cache manifests validated with side-effect-denial tests. No engine or SQL authority exists.
2. **FRESH_RESOURCE_ADMITTED**: after separate user approval, trusted observer acquires and holds an exclusive world lock; proves the exact permitted fresh volume does not exist (or is newly created by this run), no prior DB/game/user data, all volume users globally accounted for, unique engine/full container/image/mount identities, exact isolated internal network and members, no host/shared mounts/routes, no published DB ports, no foreign/unknown attachments, and no game/bot processes. A host advisory file lock only serializes cooperative executors; exclusive management/access outside that lock must also be established. Never adopt a matching-labelled existing volume as fresh.
3. **DB_QUARANTINED**: start ONLY the admitted isolated DB, without game services; acquire trusted container-exec route and attest actual schema/world instance. DB may run while game services are offline. No host default socket, host TCP substitute, arbitrary caller endpoint or credential-only identity proof.
4. **BOOTSTRAPPED_OFFLINE**: fresh DDL/data/server row/fixture operations execute with exact phase readback; actual table engines and ownership metadata checked; public defaults absent; failed phase permanently blocks launch until explicitly reconciled. Fresh fixture creation is distinct from deletion of existing fixtures.
5. **LAUNCH_ADMITTED**: reacquire/refresh identity/network/mount/volume-user evidence under the retained lock immediately before every state change. Authorize only admitted login, char, map roles, in that order, with bounded readiness and verified inter-server registration/map availability. Supervisor retains lock, identities, process ownership and private runtime tree throughout launch/use/cleanup. Readiness is not gameplay acceptance.
6. **GAMEPLAY_ACCEPTED**: only after separate real tests with live provenance: exact owned account/char selection; login/char/map handshake; actual chat relay, observed walking, sit/stand, party acceptance with both participants/receive loops alive; mobs damaged and loot in real inventory if claimed; disconnect and SQL readback; immediate repeat without unsafe cleanup. No fixture event counts/stubs/protocol-send-only claims.

The existing inventory adapter performs two fixed read-only snapshots and sets `mutation_authorized: False`; it observes project containers and all users of the exact test volume but does NOT prove DB ownership, network membership, absence of online players, an exclusive lock or launch permission. Keep it read-only and do not widen its accepted result into authority. [R/src/robots/adapters/world_inventory.py:12-35,125-156,159-197]

**Reset is a separate destructive operation**. The inert reset plan targets only an exactly owned stopped test DB container and named test volume, requires all volume users to match, and removes the external volume explicitly; `compose down -v` does not remove it. Reset requires separate explicit approval for that existing data/resource, verified stopped identities, backup/retention decision, exact account/data ownership and fresh immediate observations under exclusive authority. Unknown/debug/prod/human/shared resources are always refused. A fresh provision refusal must not silently fall through into reset. [R/scripts/e2e_runner.py:21-56; R/scripts/world.sh:1-9; R/scripts/e2e.sh:1-7]

## 5. Acceptance requirements and remaining blockers

Offline implementation can proceed without another live-authorization discussion: add the source-only runtime asset/config builder, a public default-suppressed bootstrap derivation, closed config schema with 23-byte inter-secret limits, a trusted-observer interface/state machine, pure admission/failure tests, and exact manifests. Do not remove existing fail-closed entrypoints merely because those pieces pass.

Before the live boundary, tests must cover: source/hash/profile drift; config unknown/duplicate keys and injection; symlink/owner/mode/private-secret handling; no secret leakage on SQL/engine/native errors; all import edges and selected cache coverage/index/walkable fixture points; actual CWD/argv semantics; no engine/SQL/socket call on any refused admission; concurrent lock/drift/foreign-volume/foreign-network/unowned-row/name collision; fresh-versus-existing separation; schema count/columns/bootstrap statement parity; denied/public-default server logins; inter-secret lengths 23 accepted and 24 rejected; all role SQL families with no fallback; MyISAM partial failures explicitly quarantined rather than rolled back; exact readback after each mutation; reconnect/cleanup process ownership; repeatable real gameplay only after authorized integration.

Remaining launch blockers are concrete: P intentionally returns 78 before startup; runtime-capable build and CWD mechanism are separate work; launch asset closure/config rendering not installed; fresh bootstrap derivation and private server account executor absent; no trusted lock/engine/network/DB authority adapter; no readback executor/engine policy; existing seeder and E2E lifecycle intentionally blocked. Repository files were dirty and some other delegates may modify root/runtime files; this report records its own read-only snapshot hashes and must not be presented as frozen review approval for their later changes.

**Only at the live boundary request user authorization** for the exact isolated fresh resource names, engine/container/image/network identities, permitted DB/schema/account writes, private credential generation/consumption, allowed game/client processes and any port publication. Reset/overwrite of an existing world needs a distinct approval. None of those permissions was granted here. No whole-goal or launch-safety claim follows from this report.
