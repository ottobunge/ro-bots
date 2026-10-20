---
title: First live native test world
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [ops, testing, rathena]
---

# First live native test world

This records verified service startup, **not** completed playable-world or bot
acceptance. See [[goals-ledger]], [[simple-world-compose]] and [[world-preparation]].

## Scope and authorization

The user authorized creating only the new `ro-bots-test` Compose project and
`ro-bots-world-test` volume, loading built images, private-file import, fresh
DB initialization and localhost native-role checks. Existing host servers were
left untouched. Because their default ports were occupied, the user separately
approved login/char/map ports **16900 / 16121 / 15121**.

No debug or production reset, human-account modification or paid inference ran.
Service credentials remain private and are omitted here: [REDACTED].

## Observed result

- The selected cached database image is healthy. Actual init hooks processed all
  five SQL files. SQL readback confirms **70 tables**, one server-only account,
  zero human accounts and zero characters.
- Three separately packaged runnable native roles use UID 10000 and
  `/world/runtime`; they remain running after delayed checks and the final
  configured quality gate. Char connects to login, map connects to char, and
  char reports the map server registered with **1265 maps**.
- Map logs report **1265 maps loaded and 13036 NPCs loaded**. TCP checks reached
  all three approved localhost ports. These are readiness observations, not
  character login, movement, combat, loot or human-client proof.
- Seven private configuration paths were updated and read back byte-for-byte
  while only the owned native roles were stopped. Modes/UID remained 0600/10000.
  Database volume and account rows were preserved; no reset was used.

## Live-discovered corrections

1. Import root0711 allowed known-file reads but prevented UID999 from listing
   the init directory. Root0755 fixes directory listing; private files stay0600
   and private subdirectories0700. Actual UID999 enumeration/readback passed.
2. The official healthcheck autodetects credentials under its default datadir.
   Explicit `--defaults-extra-file=/var/lib/ro-bots/db/.my-healthcheck.cnf` fixes
   the relocated datadir. The live command failed without it and passed with it.
3. Minimal role overrides omitted native SQL table defaults. Host preparation
   now merges pinned defaults before private overrides, restoring 40 char-table
   mappings including distinct clan/clan_alliance. The logged char limit0 is
   **unlimited**, not a zero-slot error; no arbitrary slot override was added.

The corrected initializer archive was rebuilt and its script bytes verified;
that newer archive is not yet loaded. This existing test volume was repaired
explicitly rather than re-imported.

## Evidence and gates

Reports are under `run/reviews/`:

- `world-native-defaults-parent-verification.json`:163 parent cases,100% preparation
  coverage; implementer sources/current dependencies reconciled.
- `world-live-bootstrap-delta-review.json`:independent28-case bootstrap PASS;
  ten current frozen inputs matched. No new independent live execution claimed.
- `first-test-world-native-config-update.json`:exact target write/readback.
- `first-test-world-native-defaults-delayed.json`:peers/maps/NPC observations and
  preserved database readback.
- `first-test-world-post-gate-status.json`:four owned services still running.
- `native-defaults-final-task-check.json/.log`:**1839 tests +65 subtests /94.32%**,
  exit0,134 public fingerprints unchanged.
- `native-defaults-dependency-audit.json`:configured audit exit0, no known
  vulnerabilities reported by that run.

Independent defaults-source review passed:162 unique cases/100% preparation
coverage, ten current source/dependency hashes and JUnit matched by parent.
Recorded in `world-native-defaults-final-disposition.json`; approval remains
source/configuration-scoped, not full gameplay acceptance.

## Remaining acceptance

- Source/log diagnostics still mention optional imported mapcache, mob-appearance
  and barter data; determine their intended absence from pinned source before
  silencing or adding files. Service survival does not prove every data feature.
- Two controlled non-human fixture accounts/characters were subsequently
  provisioned under separate explicit authorization and actual client entry,
  chat/destination-message/sit-stand/party verification passed twice. See
  [[two-bot-live-limbs]] for evidence and the unaccepted arrival/persistence gap.
  This does not authorize unrestricted seeding or fixture resets.
- Integrate native preparation/import/lifecycle into the convenient Task routes;
  the minimal native Compose stack was exercised directly, not full `task e2e`.
- Verify bots, memories, social play, dashboard, legal progression and benchmarks.
  None of the six complete standing milestones is closed by this startup report.
