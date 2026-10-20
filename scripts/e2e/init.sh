#!/usr/bin/env bash
# e2e-init: schema verification + default agent population for the e2e world.
#
# The schema itself (ragnarok tables + the interserver service account) was
# imported by mariadb's init hooks from the stage SQL on the fresh datadir; this
# task verifies that, then applies the private two-agent fixture (mirroring the
# reviewed two-bot fixture: Novice characters with the standard novice start,
# status_point 48 / skill_point 9 / Basic Skill lv 9) and reads the exact rows
# back from the DB. The fixture is generated once per stage with fresh random
# identities; never printed.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
e2e_load_inputs
e2e_require_up
export E2E_STAGE E2E_DB_CONTAINER WORLD_DB_NAME

echo "== e2e-init: schema verification =="
TABLES="$(e2e_db_query "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${WORLD_DB_NAME}';")"
if [[ "${TABLES}" -lt 60 ]]; then
  echo "e2e-init: FAIL: expected the imported ragnarok schema (~70 tables), found ${TABLES}" >&2
  exit 1
fi
echo "  schema: ${TABLES} tables in ${WORLD_DB_NAME}"
echo "  login rows before fixture: $(e2e_db_query 'SELECT COUNT(*) FROM login;')"

echo "== e2e-init: default agent population =="
FIXTURE_DIR="${E2E_STAGE}/fixture"
if [[ ! -f "${FIXTURE_DIR}/fixture.sql" ]]; then
  "${E2E_REPO}/.venv/bin/python" "${SCRIPT_DIR}/make_fixture.py" "${E2E_STAGE}"
fi
docker exec -i -e MYSQL_PWD="$(cat "${E2E_STAGE}/secrets/db-root")" \
  "${E2E_DB_CONTAINER}" mariadb -uroot "${WORLD_DB_NAME}" \
  < "${FIXTURE_DIR}/fixture.sql"
echo "  fixture.sql applied"

echo "== e2e-init: readback (fresh, from the DB) =="
"${E2E_REPO}/.venv/bin/python" - "${FIXTURE_DIR}/fixture.json" <<'PY'
import json
import os
import subprocess
import sys

fixture = json.load(open(sys.argv[1], encoding="utf-8"))
stage = os.environ["E2E_STAGE"]
container = os.environ["E2E_DB_CONTAINER"]
root_password = open(f"{stage}/secrets/db-root", encoding="utf-8").read().strip()
account_ids = sorted(int(a["account_id"]) for a in fixture["accounts"])
char_ids = sorted(int(a["char_id"]) for a in fixture["accounts"])
id_list = ",".join(str(v) for v in account_ids)
char_list = ",".join(str(v) for v in char_ids)


def query(sql: str) -> list[list[str]]:
    out = subprocess.run(
        ["docker", "exec", "-e", f"MYSQL_PWD={root_password}", container,
         "mariadb", "-uroot", "ragnarok", "-N", "-B", "-e", sql],
        capture_output=True, text=True, check=True,
    )
    return [line.split("\t") for line in out.stdout.strip().splitlines() if line]


rows = query(f"SELECT account_id, group_id, state FROM login WHERE account_id IN ({id_list});")
assert len(rows) == 2, f"expected 2 fixture accounts, got {len(rows)}"
assert all(int(r[1]) == 0 and int(r[2]) == 0 for r in rows), "accounts must be group 0, state 0"

rows = query(
    "SELECT char_id, account_id, name, class, base_level, job_level, status_point, "
    f"skill_point, online, last_map, last_x, last_y FROM `char` WHERE char_id IN ({char_list});"
)
assert len(rows) == 2, f"expected 2 fixture characters, got {len(rows)}"
for row in rows:
    assert row[3] == "0", f"class must be 0 (Novice), got {row[3]}"
    assert int(row[6]) == 48, f"status_point must be 48, got {row[6]}"
    assert int(row[7]) == 9, f"skill_point must be 9, got {row[7]}"
    assert int(row[8]) == 0, "characters must be offline after init"
    print("  char:", row[0], "account", row[1], "name", row[2],
          "base/job", row[4] + "/" + row[5], "status/skill_points", row[6] + "/" + row[7],
          "at", row[9], row[10] + "," + row[11])

rows = query(f"SELECT char_id, id, lv FROM skill WHERE char_id IN ({char_list}) ORDER BY char_id;")
assert len(rows) == 2 and all(r[1] == "1" and int(r[2]) == 9 for r in rows), \
    f"expected Basic Skill lv 9 per character, got {rows}"

foreign = query(f"SELECT COUNT(*) FROM `char` WHERE account_id NOT IN ({id_list});")
assert foreign and int(foreign[0][0]) == 0, "no foreign characters may exist in the e2e world"
print("e2e-init: fixture verified: 2 accounts, 2 novice characters, status_point 48, "
      "skill_point 9, Basic Skill lv 9, 0 online, no foreign rows")
PY
