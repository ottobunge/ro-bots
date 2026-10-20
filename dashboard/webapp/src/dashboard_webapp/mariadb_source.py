"""Read-only MariaDB source for the agent/character list and detail.

Security posture:

- credentials come from the secret file (``db-root`` pattern), read at runtime,
  never stored in the config object's repr and never logged;
- every statement passes :func:`assert_read_only` (SELECT/SHOW/DESCRIBE only,
  no semicolons, no comment smuggling);
- the connection opens with ``SET SESSION TRANSACTION READ ONLY``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dashboard_webapp.config import read_secret
from dashboard_webapp.models import AgentDetail, AgentSummary, InventoryItem
from dashboard_webapp.repository import AgentSource, DataSourceError, UnknownAgentError

_READ_ONLY_FIRST_WORD = re.compile(r"^\s*(?:/\*.*?\*/\s*)*", re.DOTALL)
_ALLOWED = {"select", "show", "describe", "desc"}

_CHAR_COLUMNS = (
    "char_id, account_id, name, class, base_level, job_level, hp, sp, max_hp, max_sp, "
    "last_x, last_y, last_map, online, str, agi, vit, `int`, dex, luk, zeny, "
    "status_point, skill_point"
)
AGENT_SQL = f"SELECT {_CHAR_COLUMNS} FROM `char` ORDER BY char_id"
AGENT_BY_ID_SQL = f"SELECT {_CHAR_COLUMNS} FROM `char` WHERE char_id = %s"
INVENTORY_SQL = (
    "SELECT nameid, amount, equip, identify, refine, attribute, card0 "
    "FROM `inventory` WHERE char_id = %s ORDER BY id"
)

_STAT_COLUMNS = (
    "str",
    "agi",
    "vit",
    "int",
    "dex",
    "luk",
    "zeny",
    "status_point",
    "skill_point",
    "max_hp",
    "max_sp",
)


class ReadOnlyViolation(DataSourceError):
    pass


def assert_read_only(sql: str) -> None:
    """Refuse anything that is not a plain single read statement."""
    stripped = _READ_ONLY_FIRST_WORD.sub("", sql, count=1).lstrip()
    if not stripped:
        raise ReadOnlyViolation("empty statement")
    if ";" in sql:
        raise ReadOnlyViolation("multi-statement SQL refused")
    first = stripped.split(None, 1)[0].strip("`\"'").lower()
    if first not in _ALLOWED:
        raise ReadOnlyViolation(f"non-read statement refused: {first or '?'}")


class DbConfig:
    """MariaDB coordinates; the password lives only in the secret file."""

    def __init__(
        self, host: str, port: int, name: str, user: str, root_secret_file: Path | str
    ) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.user = user
        self.root_secret_file = Path(root_secret_file)

    def password(self) -> str:
        return read_secret(self.root_secret_file)

    def __repr__(self) -> str:  # never include the password
        return (
            f"DbConfig(host={self.host!r}, port={self.port!r}, name={self.name!r}, "
            f"user={self.user!r}, root_secret_file={str(self.root_secret_file)!r})"
        )

    __str__ = __repr__


def _default_connect(**kwargs: Any) -> Any:
    """Real driver seam; imported lazily so tests never need pymysql.

    Rows are consumed as mappings, so the real driver gets ``DictCursor``.
    """
    import pymysql
    from pymysql.cursors import DictCursor

    return pymysql.connect(**kwargs, cursorclass=DictCursor)


class MariaDbAgentSource(AgentSource):
    def __init__(self, config: DbConfig, connect: Callable[..., Any] | None = None) -> None:
        self._config = config
        self._connect = connect or _default_connect

    def _open(self) -> Any:
        return self._connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password(),
            database=self._config.name,
            charset="utf8mb4",
            autocommit=True,
            init_command="SET SESSION TRANSACTION READ ONLY",
        )

    def list_agents(self) -> list[AgentSummary]:
        assert_read_only(AGENT_SQL)
        conn = self._open()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(AGENT_SQL)
                rows = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            conn.close()
        return [_to_summary(row) for row in rows]

    def agent_detail(self, char_id: int) -> AgentDetail:
        assert_read_only(AGENT_BY_ID_SQL)
        assert_read_only(INVENTORY_SQL)
        conn = self._open()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(AGENT_BY_ID_SQL, (char_id,))
                row = cursor.fetchone()
                if row is None:
                    raise UnknownAgentError(f"unknown agent: {char_id}")
                cursor.execute(INVENTORY_SQL, (char_id,))
                inventory_rows = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            conn.close()
        return AgentDetail(
            agent=_to_summary(row),
            inventory=[_to_inventory(item) for item in inventory_rows],
            stats={column: row.get(column) for column in _STAT_COLUMNS},
            memory_files=[],
            memory_root=None,
        )


def _to_summary(row: dict[str, Any]) -> AgentSummary:
    raw_id = row.get("char_id")
    return AgentSummary(
        char_id=int(raw_id) if isinstance(raw_id, int) else 0,
        name=str(row.get("name") or ""),
        char_class=row.get("class"),
        base_level=row.get("base_level"),
        job_level=row.get("job_level"),
        hp=row.get("hp"),
        sp=row.get("sp"),
        x=row.get("last_x"),
        y=row.get("last_y"),
        map=str(row.get("last_map") or ""),
        online=bool(row.get("online")),
    )


def _to_inventory(row: dict[str, Any]) -> InventoryItem:
    return InventoryItem(
        nameid=row.get("nameid"),
        amount=row.get("amount"),
        identify=row.get("identify"),
        equip=row.get("equip"),
        refine=row.get("refine"),
        attribute=row.get("attribute"),
    )
