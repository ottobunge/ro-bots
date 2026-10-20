"""Read-only exact two-fixture baseline; no native clients or model inference."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

if sys.flags.optimize != 0:
    raise RuntimeError("optimized helper execution refused")

ROOT = Path("/home/otto/dev/ro-bots")
loc = json.loads(
    (ROOT / "run/reviews/scheduled-native-host-private-location.json").read_text()
)
paths = [Path(loc["config"]), Path(loc["host_manifest"])]
for path in paths:
    meta = path.stat()
    if meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o600:
        raise RuntimeError("private input permissions refused")
config, manifest = [json.loads(path.read_text()) for path in paths]
rows = manifest["accounts"]
pairs = config["exact_pairs"]
assert len(rows) == len(pairs) == 2
assert {row["persona_id"] for row in rows} == set(pairs)
assert manifest["login_host"] == "127.0.0.1" and manifest["login_port"] == 16900
pre = json.loads(
    (ROOT / "run/reviews/playing-mvp-fresh-engine-preflight.json").read_text()
)
assert pre["exact_four_volume_users"] and len(pre["containers"]) == 4
assert all(c["running"] for c in pre["containers"])
db = next(c for c in pre["containers"] if c["service"] == "mariadb")
assert db["health"] == "healthy"
current = subprocess.run(
    ["docker", "inspect", db["id"]], capture_output=True, text=True, check=True
)
observed = json.loads(current.stdout)[0]
if "Health" not in observed["State"] and "Healthcheck" in observed["State"]:
    observed["State"]["Health"] = observed["State"]["Healthcheck"]
assert observed["Id"] == db["id"] and observed["Image"] == db["image"]
assert (
    observed["State"]["Running"] and observed["State"]["Health"]["Status"] == "healthy"
)
assert observed["Config"]["Labels"]["com.docker.compose.project"] == "ro-bots-test"
assert all(
    m.get("Type") == "volume" and m.get("Name") == "ro-bots-world-test"
    for m in observed["Mounts"]
)
assert any(m.get("Destination") == "/var/lib/mysql" for m in observed["Mounts"])
ids = [int(pairs[row["persona_id"]][0]) for row in rows]
chars = [int(pairs[row["persona_id"]][1]) for row in rows]
assert len(set(ids)) == len(set(chars)) == 2 and all(v > 1 for v in ids + chars)
shell = 'set -eu; IFS= read -r MYSQL_PWD < /var/lib/ro-bots/secrets/db-root || test -n "$MYSQL_PWD"; export MYSQL_PWD; exec mariadb --protocol=socket --user=root --batch --skip-column-names ragnarok'
query = (
    "SELECT account_id,HEX(userid),HEX(user_pass),sex,group_id,state,HEX(pincode) FROM login WHERE account_id IN ("
    + ",".join(map(str, ids))
    + ");"
    "SELECT char_id,account_id,HEX(name),online,class,base_level,job_level,base_exp,job_exp,hp,sp,last_map,last_x,last_y FROM `char` WHERE char_id IN ("
    + ",".join(map(str, chars))
    + ");"
    "SELECT char_id,nameid,amount FROM inventory WHERE char_id IN ("
    + ",".join(map(str, chars))
    + ") ORDER BY char_id,nameid;"
)
query += " SELECT COUNT(*),COALESCE(SUM(online<>0),0) FROM `char`;"
proc = subprocess.run(
    ["docker", "exec", "-i", db["id"], "sh", "-c", shell],
    input=query,
    capture_output=True,
    text=True,
    timeout=20,
)
if proc.returncode:
    raise RuntimeError("owned read-only database baseline failed")
lines = [line.split("\t") for line in proc.stdout.splitlines()]
all_character_counts = [line for line in lines if len(line) == 2]
assert len(all_character_counts) == 1
total_character_count, online_character_count = map(int, all_character_counts[0])
assert online_character_count == 0
accounts = {int(line[0]): line for line in lines if len(line) == 7}
characters = {int(line[0]): line for line in lines if len(line) == 14}
assert len(accounts) == len(characters) == 2
for row in rows:
    aid, cid = map(int, pairs[row["persona_id"]])
    account = accounts[aid]
    assert bytes.fromhex(account[1]).decode() == row["account"]
    assert bytes.fromhex(account[2]).decode() == row["password"]
    assert account[3] != "S" and account[4:6] == ["0", "0"]
    assert bytes.fromhex(account[6]).decode() == row["pincode"]
    character = characters[cid]
    assert (
        int(character[1]) == aid
        and bytes.fromhex(character[2]).decode() == row["char_name"]
    )
    assert character[3] == "0"
result = {
    "passed": True,
    "read_only": True,
    "native_sessions_opened": 0,
    "inference_calls": 0,
    "exact_fixture_ownership_verified": True,
    "both_offline": True,
    "characters": [
        {
            "fixture_index": index,
            "raw_job": int(characters[cid][4]),
            "base_level": int(characters[cid][5]),
            "job_level": int(characters[cid][6]),
            "base_exp": int(characters[cid][7]),
            "job_exp": int(characters[cid][8]),
            "saved_hp": int(characters[cid][9]),
            "saved_sp": int(characters[cid][10]),
            "saved_map": characters[cid][11],
            "saved_position": [int(characters[cid][12]), int(characters[cid][13])],
            "inventory": [
                {"item_id": int(line[1]), "amount": int(line[2])}
                for line in lines
                if len(line) == 3 and int(line[0]) == cid
            ],
        }
        for index, cid in enumerate(chars)
    ],
    "secrets": "[REDACTED]",
    "native_gameplay_acceptance": False,
}
(ROOT / "run/reviews/playing-mvp-readonly-baseline.json").write_text(
    json.dumps(result, indent=2) + chr(10)
)
print(
    json.dumps(
        {
            "passed": result["passed"],
            "read_only": True,
            "exact_two_fixture_ownership_verified": True,
            "both_fixtures_offline": True,
            "all_online_character_count": online_character_count,
            "total_character_count": total_character_count,
            "native_sessions_opened": 0,
            "inference_calls": 0,
            "private_values": "[REDACTED]",
        },
        indent=2,
    )
)
