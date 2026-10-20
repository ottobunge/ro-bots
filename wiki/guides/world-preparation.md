# Private host-side world preparation

`robots.adapters.world_prepare.create(target, selection, settings)` creates a
**new** operator-owned staging directory. It does not run Docker, SQL or native
servers, and it grants no launch/reset authority. Existing targets, including
empty directories and dangling symlinks, are refused.

Use `WorldSelection` from `world_compose` and the frozen `PreparationSettings`
from `world_prepare`. Required private settings are `db_name`, `db_user`,
`db_password`, `inter_user`, `inter_password` and `root_password`. Supply these
in-process from trusted generated values or a private caller-owned input file;
never place credentials on CLI arguments. The object deliberately has no
value-bearing repr. The API does not read or modify the input file.

Settings default to the pinned `MAIN-pre-re-20180704` profile, database service
`mariadb:3306`, container listener `0.0.0.0`, login peer `rathena-login`, map-role
char peer `rathena-char`, and host advertisements `127.0.0.1`. Advertisement
settings are **separate** from role connection addresses. Set
`advertised_char_ip` and `advertised_map_ip` explicitly when published ports
should advertise another host IPv4. Distinct role ports must be integers
1–65535, not booleans. PIN policy is an explicit boolean.

`display_name` defaults to `RO Bots` and allows 1–19 safe ASCII characters.
It is independent of the Compose world identity; long production world IDs
are not silently truncated. The existing offline bundle validator's more
restrictive endpoint/world contract remains unchanged and is not claimed to
accept these container settings.

Private field bounds reuse the existing receiver validator: identifiers are
1–23 ASCII alphanumeric/underscore characters, database and root passwords are
1–32 allowed ASCII characters, and interserver passwords are 1–23. Validation
finishes before public asset reads or allocation. Root secrets must be supplied
by the trusted caller; this API does not generate or reveal them.

Prepared layout:

```text
TARGET/
  runtime/       679 attested public assets plus seven private role configs
    log/         native relative log paths
  sql/           five ordered initialization files, one selected database
  secrets/
    db-root      private root password
    db-user      private database-user password
  memory/agents/
  logs/
```

All directories are 0700 and all files 0600, owned by the staging operator.
SQL keeps the 70 disjoint pinned tables and suppresses upstream default login
accounts. The last file inserts only the configured server-only account
(account ID 1, sex S, group 0), matching the native role credentials.

The result is a public summary of world/project/volume, asset/NPC/map counts,
profile and required container paths. It contains no private-field values or
private-file hashes. It explicitly reports provisioning, native parser
execution and host bind-mount readiness as false. There is no manifest,
publication marker, receipt catalog or fake agent/account seed.

## Remaining integration boundary

A separate authorized importer must install the runtime at `/world/runtime`,
set runtime ownership to UID 10000, and establish appropriate UID 999 database
and initialization-file readability before startup. Operator-private 0700/0600
host files are **not automatically readable by the MariaDB container**. Runtime
binaries are copied as private data, not made executable by this preparer.
Actual native parsing, SQL import/readback, volume import and lifecycle testing
remain separate work. Only fresh-database initialization is intended; these
SQL files are not migrations or resets.

The filesystem contract is ordinary trusted-user staging, not adversarial
same-user path protection. An existing parent directory is required. On source
failure no target is allocated. On write failure a private partial directory
may remain; the original exception propagates and no success is returned.
There is no rollback or automatic recovery claim.
