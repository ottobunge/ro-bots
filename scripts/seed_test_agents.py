"""Fail-closed test-world seed preparation.

Only pure, offline plans are supported. A plan is not authorization to execute:
there is no trusted Docker/DB observation adapter or transactional executor yet.
No SQL, credential or account manifest is printed or written by this entrypoint.
"""

from __future__ import annotations

import re
import subprocess  # public side-effect spy seam
import sys
from typing import Any

__all__ = ["apply_sql", "cleanup_plan", "database_route", "main", "subprocess"]

type Data = dict[str, Any]
type Statement = tuple[str, tuple[int | str, ...]]

IDENTITY = {"world": "test", "project": "ro-bots-test", "volume": "ro-bots-world-test"}
GAME_SERVICES = {"rathena-login", "rathena-char", "rathena-map"}


def require(condition: bool) -> None:
    """Raise a non-secret error for incomplete or mismatched evidence."""
    if not condition:
        msg = "isolated plan blocked: missing, ambiguous or mismatched ownership/offline evidence"
        raise RuntimeError(msg)


def validate_world(config: Data, observed: Data) -> None:
    """Validate supplied observations for planning ONLY, not execution authority.

    Observations must eventually be acquired directly by a trusted adapter while
    holding an exclusive world lock. Caller-provided JSON is NOT live proof.
    """
    require(isinstance(config, dict) and isinstance(observed, dict))
    require(config.get("allow_isolated_plan") is True)
    require(all(config.get(key) == value for key, value in IDENTITY.items()))
    require(all(observed.get(key) == value for key, value in IDENTITY.items()))
    run_id = config.get("run_id")
    require(isinstance(run_id, str) and re.fullmatch(r"[a-f0-9]{32}", run_id) is not None)
    require(
        config.get("route")
        == {
            "kind": "compose-exec",
            "service": "mariadb",
            "database": "ragnarok",
        }
    )
    require(
        observed.get("volume_labels")
        == {
            "ro-bots.world": "test",
            "ro-bots.project": "ro-bots-test",
        }
    )
    require(observed.get("database_identity") == {"world": "test", "run_id": run_id})
    services: Any = observed.get("game_services")
    require(isinstance(services, dict) and set(services) == GAME_SERVICES)
    require(all(state == "stopped" for state in services.values()))
    container: Any = observed.get("db_container")
    require(isinstance(container, dict))
    container_id = container.get("id")
    require(
        isinstance(container_id, str) and re.fullmatch(r"[a-f0-9]{64}", container_id) is not None
    )
    require(container.get("service") == "mariadb")
    require(container.get("project") == "ro-bots-test" and container.get("world") == "test")
    require(
        container.get("mounts")
        == [
            {
                "type": "volume",
                "source": "ro-bots-world-test",
                "target": "/var/lib/mysql",
            }
        ]
    )
    require(container.get("published_ports") == [])
    require(container.get("network") == "ro-bots-test-world-local")


def validate_manifest(config: Data, manifest: Data) -> None:
    """Only a single, explicit character pair per run-namespaced account."""
    require(isinstance(manifest, dict))
    require(all(manifest.get(key) == value for key, value in IDENTITY.items()))
    require(manifest.get("run_id") == config["run_id"])
    rows: Any = manifest.get("accounts")
    require(isinstance(rows, list) and bool(rows))
    account_ids, char_ids, names, accounts = set(), set(), set(), set()
    prefix = "e2e_" + config["run_id"][:12] + "_"
    for row in rows:
        require(
            isinstance(row, dict)
            and set(row)
            == {
                "account_id",
                "account",
                "char_id",
                "char_name",
            }
        )
        aid, cid, account, name = (
            row[key]
            for key in (
                "account_id",
                "char_id",
                "account",
                "char_name",
            )
        )
        require(type(aid) is int and aid > 0 and type(cid) is int and cid > 0)
        require(
            isinstance(account, str)
            and re.fullmatch(re.escape(prefix) + r"[a-z0-9]{1,6}", account) is not None
        )
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]{1,23}", name) is not None)
        require(aid not in account_ids and cid not in char_ids)
        require(account not in accounts and name not in names)
        account_ids.add(aid)
        char_ids.add(cid)
        accounts.add(account)
        names.add(name)


def validate_ownership(manifest: Data, database: Data) -> None:
    """Require exact current identities, no extra characters, and offline rows."""
    require(isinstance(database, dict))
    accounts: Any = database.get("accounts")
    characters: Any = database.get("characters")
    require(isinstance(accounts, list) and isinstance(characters, list))
    require(all(isinstance(row, dict) for row in accounts + characters))
    for row in manifest["accounts"]:
        account_matches = [
            item
            for item in accounts
            if (
                item.get("account_id") == row["account_id"] or item.get("account") == row["account"]
            )
        ]
        character_matches = [
            item
            for item in characters
            if (
                item.get("account_id") == row["account_id"]
                or item.get("char_id") == row["char_id"]
                or item.get("char_name") == row["char_name"]
            )
        ]
        require(
            account_matches
            == [
                {
                    "account_id": row["account_id"],
                    "account": row["account"],
                    "online": False,
                }
            ]
        )
        require(
            character_matches
            == [
                {
                    "account_id": row["account_id"],
                    "char_id": row["char_id"],
                    "char_name": row["char_name"],
                    "online": False,
                }
            ]
        )
        require(account_matches[0]["online"] is False and character_matches[0]["online"] is False)


def cleanup_plan(
    config: Data, observed: Data, manifest: Data, database: Data
) -> tuple[Statement, ...]:
    """Describe exact owned pairs; never delete an account-id range.

    This is inert data. Running it requires locked fresh readback, transactional
    row locks, affected-row checks, and post-write verification not implemented here.
    """
    validate_world(config, observed)
    validate_manifest(config, manifest)
    validate_ownership(manifest, database)
    statements: list[Statement] = []
    for row in manifest["accounts"]:
        statements.extend(
            [
                (
                    (
                        "DELETE FROM `char` WHERE `account_id` = %s AND `char_id` = %s "
                        "AND `name` = %s AND `online` = 0"
                    ),
                    (row["account_id"], row["char_id"], row["char_name"]),
                ),
                (
                    "DELETE FROM `login` WHERE `account_id` = %s AND `userid` = %s",
                    (row["account_id"], row["account"]),
                ),
            ]
        )
    return tuple(statements)


def database_route(config: Data, observed: Data) -> tuple[str, str, str]:
    """Describe a pinned running container route, never connect or fall back."""
    validate_world(config, observed)
    container = observed["db_container"]
    require(container.get("state") == "running")
    return "container-exec", container["id"], "ragnarok"


def apply_sql(sql: str, socket: str | None) -> None:
    """Arbitrary SQL and native/TCP routes never acquire execution authority."""
    _ = sql, socket
    msg = "seed blocked: verified isolated transaction executor is unavailable"
    raise RuntimeError(msg)


def main() -> int:
    print(  # noqa: T201
        "[seed] blocked: shared-world seed/reset is not authorized; "
        "verified isolated ownership required",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
