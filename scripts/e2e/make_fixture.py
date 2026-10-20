#!/usr/bin/env python3
"""Generate the private e2e fixture: SQL rows, fixture metadata, host manifest.

Mirrors run/worlds/test-first-live-86e7c36895db/two-bot-e09b999a23/fixture.sql
(two Novice characters, standard novice start: status_point 48, skill_point 9,
Basic Skill lv 9, one field save point and one town save point) with fresh
account/char identities for the isolated e2e world.

Writes (mode 0600) into <stage>/fixture/:
  fixture.sql        INSERT rows for `login`, `char`, `skill` (ASCII hex scalars)
  fixture.json       offline fixture metadata (accounts, ids, start cells)
  host-manifest.json the window operator's host manifest (login host/port)

Never prints credential material.
"""

from __future__ import annotations

import json
import os
import secrets
import string
import sys
import time
from pathlib import Path

ACCOUNT_ID_BASE = 2_000_100
CHAR_ID_BASE = 150_100
SKILL_BASIC = 1  # NV_BASIC, granted at lv 9 = the complete novice skill plan
STATUS_POINT_GRANT = 48  # the standard novice start (STR 9 + DEX 9 budget)
SKILL_POINT_GRANT = 9
ALPHABET = string.ascii_letters + string.digits + "_-"


def hex_literal(value: str) -> str:
    """ASCII hex literal for private scalar values (never a quoted credential)."""
    return "X'" + value.encode("ascii").hex() + "'"


def start_cells() -> list[dict[str, object]]:
    """Mirror the reviewed fixture: agent 0 saves on the field, agent 1 in town."""
    return [
        {
            "last_map": "prontera",
            "last_x": 150,
            "last_y": 150,
            "save_map": "prt_fild08",
            "save_x": 167,
            "save_y": 352,
        },
        {
            "last_map": "prontera",
            "last_x": 152,
            "last_y": 150,
            "save_map": "prontera",
            "save_x": 152,
            "save_y": 150,
        },
    ]


def write_private(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    stage = Path(sys.argv[1] if argv is None else argv[0]).resolve()
    tag = secrets.token_hex(5)  # 10 hex chars; usernames stay <= 24 ASCII chars
    cells = start_cells()
    accounts: list[dict[str, object]] = []
    sql_parts: list[str] = ["USE `ragnarok`;"]
    for index in range(2):
        account_id = ACCOUNT_ID_BASE + index
        char_id = CHAR_ID_BASE + index
        username = f"fx_{tag}_{index}"
        password = "".join(secrets.choice(ALPHABET) for _ in range(20))
        pincode = f"{secrets.randbelow(10000):04d}"
        char_name = f"Fx_{tag}_{index}"
        cell = cells[index]
        sql_parts.append(
            "INSERT INTO `login` (`account_id`, `userid`, `user_pass`, `sex`, `email`, "
            "`group_id`, `state`, `pincode`, `pincode_change`) VALUES "
            f"({account_id}, {hex_literal(username)}, {hex_literal(password)}, 'M', '', 0, 0, "
            f"{hex_literal(pincode)}, UNIX_TIMESTAMP());"
        )
        sql_parts.append(
            "INSERT INTO `char` (`char_id`, `account_id`, `char_num`, `name`, `class`, "
            "`base_level`, `job_level`, `str`, `agi`, `vit`, `int`, `dex`, `luk`, `max_hp`, "
            "`hp`, `max_sp`, `sp`, `last_map`, `last_x`, `last_y`, `save_map`, `save_x`, "
            "`save_y`, `sex`, `online`, `status_point`, `skill_point`) VALUES "
            f"({char_id}, {account_id}, 0, {hex_literal(char_name)}, 0, 10, 10, "
            f"1, 1, 1, 1, 1, 1, 40, 40, 11, 11, "
            f"'{cell['last_map']}', {cell['last_x']}, {cell['last_y']}, "
            f"'{cell['save_map']}', {cell['save_x']}, {cell['save_y']}, 'M', 0, "
            f"{STATUS_POINT_GRANT}, {SKILL_POINT_GRANT});"
        )
        sql_parts.append(
            "INSERT INTO `skill` (`char_id`, `id`, `lv`, `flag`) VALUES "
            f"({char_id}, {SKILL_BASIC}, 9, 0);"
        )
        accounts.append(
            {
                "persona_id": f"e2e_fixture_{index}",
                "account": username,
                "password": password,
                "character": char_name,
                "pincode": pincode,
                "account_id": account_id,
                "char_id": char_id,
                "start": dict(cell),
            }
        )
    fixture_dir = stage / "fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    write_private(fixture_dir / "fixture.sql", ("\n".join(sql_parts) + "\n").encode("ascii"))
    write_private(
        fixture_dir / "fixture.json",
        (
            json.dumps(
                {
                    "schema": 1,
                    "isolated_disposable": True,
                    "login_host": "127.0.0.1",
                    "login_port": 26900,
                    "accounts": accounts,
                },
                indent=1,
            )
            + "\n"
        ).encode("utf-8"),
    )
    write_private(
        stage / "host-manifest.json",
        (
            json.dumps(
                {
                    "login_host": "127.0.0.1",
                    "login_port": 26900,
                    "accounts": [
                        {
                            "persona_id": entry["persona_id"],
                            "account": entry["account"],
                            "password": entry["password"],
                            "char_name": entry["character"],
                            "pincode": entry["pincode"],
                        }
                        for entry in accounts
                    ],
                },
                indent=1,
            )
            + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "generated": True,
                "fixture_dir": str(fixture_dir),
                "accounts": len(accounts),
                "status_point": STATUS_POINT_GRANT,
                "skill_point": SKILL_POINT_GRANT,
                "run_tag": tag,
                "at": int(time.time()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
