"""Private, insert-only SQL for two test novices; no execution or ownership authority.

Pinned rAthena e985006171d2eb320ee512a653f4c83aea3d81b6 main.sql and
src/char/char.cpp define the columns and initial novice HP/SP. This is a limb
fixture, not a mechanically certified build. Parent must authorize fresh exact
IDs, exclude clients/stop native roles, inspect conflicts and read every row back.
MyISAM inserts may partially succeed; no rollback, retry or exactly-once promise.
SQL bytes, including credential hex, are private. Never log them.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class FixtureAccount:
    """Caller-generated credentials and freshly allocated exact identities."""

    account_id: int
    char_id: int
    username: str
    password: str
    character: str
    pincode: str


def _hex(value: str) -> str:
    return "X'" + value.encode("ascii").hex() + "'"


def _reject() -> None:
    message = "invalid fixture input"
    raise ValueError(message)


def _text(value: str, pattern: str) -> None:
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        _reject()


def _validate_account(account: FixtureAccount) -> None:
    if type(account) is not FixtureAccount:
        _reject()
    for identity in (account.account_id, account.char_id):
        if type(identity) is not int or not 0 < identity < 2**32:
            _reject()
    if account.account_id == 1:
        _reject()
    _text(account.username, r"[A-Za-z0-9_]{1,23}")
    _text(account.password, r"[\x21-\x7e]{1,23}")
    _text(account.character, r"[A-Za-z0-9_]{1,23}")
    _text(account.pincode, r"[0-9]{4}")


def _validate(database: str, accounts: tuple[FixtureAccount, FixtureAccount]) -> None:
    _text(database, r"[A-Za-z0-9_]{1,23}")
    if type(accounts) is not tuple or len(accounts) != 2:
        _reject()
    for account in accounts:
        _validate_account(account)
    for field in ("account_id", "char_id", "username", "character"):
        values = [getattr(account, field) for account in accounts]
        values = [value.lower() if type(value) is str else value for value in values]
        if values[0] == values[1]:
            _reject()


def render(database: str, accounts: tuple[FixtureAccount, FixtureAccount]) -> bytes:
    """Render only; parent supplies selected database and private fixture manifest."""
    _validate(database, accounts)
    statements = [f"USE `{database}`;\n"]
    for index, account in enumerate(accounts):
        statements.extend(
            (
                (
                    "INSERT INTO `login` "
                    "(`account_id`, `userid`, `user_pass`, `sex`, `email`, `group_id`, `state`, "
                    "`pincode`, `pincode_change`) VALUES "
                ),
                (
                    f"({account.account_id}, {_hex(account.username)}, {_hex(account.password)}, "
                    f"'M', '', 0, 0, {_hex(account.pincode)}, UNIX_TIMESTAMP());\n"
                ),
            )
        )
        x = 150 + 2 * index
        statements.extend(
            (
                (
                    "INSERT INTO `char` "
                    "(`char_id`, `account_id`, `char_num`, `name`, `class`, "
                    "`base_level`, `job_level`, "
                    "`str`, `agi`, `vit`, `int`, `dex`, `luk`, `max_hp`, `hp`, `max_sp`, `sp`, "
                    "`last_map`, `last_x`, `last_y`, `save_map`, "
                    "`save_x`, `save_y`, `sex`, `online`) "
                ),
                (
                    f"VALUES ({account.char_id}, {account.account_id}, 0, "
                    f"{_hex(account.character)}, "
                    "0, 10, 10, 1, 1, 1, 1, 1, 1, 40, 40, 11, 11, "
                ),
                f"'prontera', {x}, 150, 'prontera', {x}, 150, 'M', 0);\n",
            )
        )
        statements.extend(
            (
                "INSERT INTO `skill` (`char_id`, `id`, `lv`, `flag`) ",
                f"VALUES ({account.char_id}, 1, 9, 0);\n",
            )
        )
    return "".join(statements).encode("ascii")
