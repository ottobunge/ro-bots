"""Render fresh Compose database initialization; never execute SQL."""

import re

from robots.adapters.rathena_bootstrap_assets import derive


def initialization_sql(database: str, inter_user: str, inter_password: str) -> dict[str, bytes]:
    """Use one world database, including logs/web, and one server-only login row.

    Mount these private files in the MariaDB image's fresh-database init directory.
    They are not a migration or an account reset for an existing database.
    """
    patterns = (
        (database, r"[A-Za-z0-9_]{1,23}"),
        (inter_user, r"[A-Za-z0-9_]{1,23}"),
        (inter_password, r"[A-Za-z0-9_!@$%^&*+=.,?-]{1,23}"),
    )
    for value, pattern in patterns:
        if type(value) is not str or re.fullmatch(pattern, value) is None:
            message = "invalid bootstrap field"
            raise ValueError(message)
    prefix = f"USE `{database}`;\n".encode("ascii")
    assets = derive()
    files = {
        "10-main.sql": prefix + assets["main.sql"],
        "20-logs.sql": prefix + assets["logs.sql"],
        "30-web.sql": prefix + assets["web.sql"],
        "40-roulette.sql": prefix + assets["roulette_default_data.sql"],
    }
    # ASCII hex literals keep private values out of SQL quoting and escape modes.
    user_hex = inter_user.encode("ascii").hex().encode("ascii")
    password_hex = inter_password.encode("ascii").hex().encode("ascii")
    files["50-interserver.sql"] = b"".join(
        (
            prefix,
            b"INSERT INTO `login` ",
            b"(`account_id`, `userid`, `user_pass`, `sex`, `email`, `group_id`, `state`) ",
            b"VALUES (1, X'",
            user_hex,
            b"', X'",
            password_hex,
            b"', 'S', '', 0, 0);\n",
        )
    )
    return files
