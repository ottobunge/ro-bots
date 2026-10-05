"""ADR-010: deterministic test-world seed.

Builds the SAME SocietyRoster shape the dashboard uses (SocietyRoster.build
with a fixed seed), then maps the roster onto real rAthena rows:

- one login account per persona (SQL INSERT into ``login``),
- one character per persona (SQL INSERT into ``char``, matching the
  account via account_id),
- a JSON manifest at run/test-world-manifest.json: accounts, personas,
  groups — the e2e runner and the dashboard both read this.

The roster for the test world: 2 friend groups + 1 solo (3 groups, the
last built group is always a solo), 5 personas with playstyles.

SQL is applied over TCP 127.0.0.1:3306 as ragnarok/ragnarok by default;
pass --socket to use a unix socket (run/mysql.sock) instead. Uses the
mysql CLI (no python mysql driver dependency).

Usage:
  python3 scripts/seed_test_agents.py            # TCP localhost
  python3 scripts/seed_test_agents.py --socket run/mysql.sock
  python3 scripts/seed_test_agents.py --print    # SQL to stdout, no DB
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import subprocess
import sys

# Make src/ importable when run from a checkout without installing.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from robots.society.models import SocietyPersona  # noqa: E402
from robots.society.society import SocietyRoster  # noqa: E402

SEED = 42
N_GROUPS = 3  # 2 friend groups + the always-solo last group
DB = "ragnarok"

# rAthena job ids (class column of `char`): 0 novice, 1 swordsman,
# 2 mage, 3 archer, 4 acolyte, 5 merchant, 6 thief.
PLAYSTYLE_CLASS = {
    "tank": 1,  # swordsman
    "melee": 1,  # swordsman
    "mage": 2,
    "hunter": 3,  # archer
    "healer": 4,  # acolyte
    "support": 4,  # acolyte
}

# First account id auto_increment baseline of the rAthena login table.
ACCOUNT_BASE = 2_100_000
CHAR_BASE = 160_000

MANIFEST_PATH = pathlib.Path(__file__).resolve().parent.parent / "run" / "test-world-manifest.json"


def build_roster() -> SocietyRoster:
    """The fixed-seed test society: 2 friend groups + 1 solo, 5 personas."""
    return SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)


def account_name(persona: SocietyPersona) -> str:
    """Login account for a persona: e2e_<PersonaId> (ASCII, <=23 chars)."""
    return f"e2e_{persona.name.replace('-', '')}"


def seed_sql(roster: SocietyRoster) -> tuple[str, list[dict]]:
    """SQL INSERTs for the roster + the manifest rows describing them."""
    lines = [
        "-- ADR-010 deterministic test-world seed (SocietyRoster.build"
        f" (random.Random({SEED}), n_groups={N_GROUPS}))",
        "-- Idempotent: existing e2e_* accounts/chars are removed first.",
        "DELETE FROM `char` WHERE account_id >= %d;" % ACCOUNT_BASE,
        "DELETE FROM `login` WHERE account_id >= %d;" % ACCOUNT_BASE,
    ]
    accounts: list[dict] = []
    personas_manifest: list[dict] = []
    groups_manifest: list[dict] = []

    aid = ACCOUNT_BASE
    cid = CHAR_BASE
    for group in roster.groups:
        members: list[dict] = []
        for pid in group.member_ids:
            persona = roster.personas[pid]
            acct = account_name(persona)
            char_name = persona.name.replace("-", "")  # RO names: no dashes
            cls = PLAYSTYLE_CLASS.get(persona.playstyle.value, 0)
            lines.append(
                "INSERT INTO `login` (`account_id`, `userid`, `user_pass`, `sex`,"
                " `email`, `group_id`, `character_slots`)"
                " VALUES (%d, '%s', 'e2epass', 'M', '%s@example.invalid', 0, 3);"
                % (aid, acct, acct)
            )
            lines.append(
                "INSERT INTO `char` (`char_id`, `account_id`, `char_num`, `name`,"
                " `class`, `base_level`, `job_level`, `last_map`, `last_x`, `last_y`,"
                " `save_map`, `save_x`, `save_y`)"
                " VALUES (%d, %d, 0, '%s', %d, 1, 1, 'prontera', 156, %d,"
                " 'prontera', 156, %d);"
                % (cid, aid, char_name, cls, 145 + (cid - CHAR_BASE) % 8, 145 + (cid - CHAR_BASE) % 8)
            )
            row = {
                "account_id": aid,
                "account": acct,
                "password": "e2epass",
                "char_id": cid,
                "char_name": char_name,
                "persona_id": persona.persona_id,
                "playstyle": persona.playstyle.value,
                "attitude": persona.attitude.value,
                "chattiness": round(persona.chattiness, 4),
                "level_band": list(persona.level_band),
            }
            accounts.append(row)
            members.append(row)
            personas_manifest.append(
                {
                    "persona_id": persona.persona_id,
                    "name": persona.name,
                    "playstyle": persona.playstyle.value,
                    "attitude": persona.attitude.value,
                    "chattiness": round(persona.chattiness, 4),
                    "account": acct,
                    "char_name": char_name,
                }
            )
            aid += 1
            cid += 1
        groups_manifest.append(
            {
                "group_id": group.group_id,
                "attitude": group.attitude.value,
                "members": [m["persona_id"] for m in members],
                "accounts": [m["account"] for m in members],
            }
        )

    manifest = {
        "seed": SEED,
        "n_groups": N_GROUPS,
        "accounts": accounts,
        "personas": personas_manifest,
        "groups": groups_manifest,
    }
    return "\n".join(lines) + "\n", manifest


def apply_sql(sql: str, socket: str | None) -> None:
    """Pipe the SQL into MariaDB (TCP ragnarok/ragnarok, or --socket as root)."""
    if socket:
        cmd = ["mariadb", "--no-defaults", "--skip-ssl", "-S", socket, "-u", "root", DB]
    else:
        cmd = ["mariadb", "--no-defaults", "--skip-ssl", "-h", "127.0.0.1", "-P", "3306",
               "-u", "ragnarok", "-praragnarok", DB]
    # fall back to the mysql binary name if mariadb is absent
    if not socket:
        try:
            subprocess.run(["which", "mariadb"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            cmd = ["mysql", "--no-defaults", "--skip-ssl", "-h", "127.0.0.1", "-P", "3306",
                   "-u", "ragnarok", "-praragnarok", DB]
    proc = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"seed SQL failed ({' '.join(cmd[:3])}...): {proc.stderr.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--socket", help="MariaDB unix socket (default: TCP 127.0.0.1:3306)")
    ap.add_argument("--print", dest="print_sql", action="store_true",
                    help="print the SQL to stdout and skip the DB")
    args = ap.parse_args()

    roster = build_roster()
    sql, manifest = seed_sql(roster)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[seed] manifest -> {MANIFEST_PATH}"
          f" ({len(manifest['accounts'])} accounts, {len(manifest['groups'])} groups)")
    for g in manifest["groups"]:
        print(f"[seed] group {g['group_id']!r} ({g['attitude']}): {', '.join(g['members'])}")

    if args.print_sql:
        print(sql)
        return 0
    try:
        apply_sql(sql, args.socket)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"[seed] ERROR: {exc}", file=sys.stderr)
        print("[seed] is MariaDB up? (task world:up, or spikes/002-rathena-up/start.sh)",
              file=sys.stderr)
        return 1
    print(f"[seed] SQL applied: {len(manifest['accounts'])} accounts + chars in '{DB}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
