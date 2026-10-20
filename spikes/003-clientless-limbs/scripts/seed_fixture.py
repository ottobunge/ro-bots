#!/usr/bin/env python3
"""Offline fixture validator / guarded SQL renderer. No database execution API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SPIKE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPIKE))
from test_limbs import load_fixture, validate_fixture


def validate_snapshot(fixture, snapshot):
    """Offline model only: database checks must still run inside the transaction."""
    validate_fixture(fixture)
    if any(
        snapshot.get("engines", {}).get(table) != "InnoDB" for table in ("login", "char", "skill")
    ):
        raise ValueError("all scoped tables must use InnoDB")
    for account in fixture["accounts"]:
        owners = [
            row
            for row in snapshot.get("login", [])
            if row.get("account_id") == account["account_id"]
        ]
        characters = [
            row
            for row in snapshot.get("char", [])
            if row.get("account_id") == account["account_id"]
        ]
        if len(owners) != 1 or owners[0].get("userid") != account["username"]:
            raise ValueError("fixture account ownership mismatch")
        if len(characters) != 1 or any(
            characters[0].get(key) != expected
            for key, expected in (
                ("char_id", account["char_id"]),
                ("name", account["character"]),
                ("online", 0),
            )
        ):
            raise ValueError("fixture ownership/offline mismatch")
    return True


def render_seed(fixture, *, servers_stopped):
    validate_fixture(fixture)
    if servers_stopped is not True:
        raise ValueError("explicit stopped isolated game-server assertion required")
    public = [
        {key: account[key] for key in ("account_id", "char_id", "username", "character")}
        for account in fixture["accounts"]
    ]
    encoded = json.dumps(public, ensure_ascii=False).encode().hex()
    return (
        "-- Rendered fixture scope, no authentication material.\n"
        "SET @limb_isolated_disposable = 1;\nSET @limb_servers_stopped = 1;\n"
        f"SET @limb_fixture = CONVERT(0x{encoded} USING utf8mb4);\n"
        + (SPIKE / "seed_test.sql").read_text()
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path, help="offline JSON snapshot; no SQL connection")
    mode.add_argument("--render", action="store_true", help="print guarded SQL; never execute")
    parser.add_argument("--servers-stopped", action="store_true")
    args = parser.parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        if args.snapshot:
            validate_snapshot(fixture, json.loads(args.snapshot.read_text()))
            print("OFFLINE SNAPSHOT PASS (not live database verification)")
        else:
            print(render_seed(fixture, servers_stopped=args.servers_stopped), end="")
    except OSError, ValueError, KeyError, TypeError:
        print("FAILED: fixture/snapshot/isolation validation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
