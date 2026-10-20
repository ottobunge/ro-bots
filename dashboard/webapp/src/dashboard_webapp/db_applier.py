"""The narrow DB write path: apply a generated population fixture.

Security posture (the write-side twin of the read-only source):

- the fixture is parsed and every statement must be ``INSERT INTO`` the
  ``login``/``char``/``skill`` tables (or the fixture's leading ``USE`` of
  the configured database, which is recognised and skipped — the connection
  already targets it). Anything else — UPDATE, DELETE, DROP, SET, SELECT,
  another database, comments, multi-statement lines — raises
  :class:`SqlNotAllowed` *before* any connection is opened;
- credentials come from the secret file (``db-root`` pattern) at runtime and
  are never stored in reprs or logs;
- the connection is opened read-write (unlike the read-only source) but with
  autocommit and no other privilege use: only the allowlisted statements are
  ever executed.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from dashboard_webapp.mariadb_source import DbConfig
from dashboard_webapp.population import PopulationNotFound

ALLOWED_TABLES = ("login", "char", "skill")
POPULATION_ID_PATTERN = re.compile(r"pop-[a-z0-9._-]{1,64}")
WORLD_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_INSERT_PREFIX = re.compile(r"^INSERT INTO `([a-z_]+)` \(")
_USE = re.compile(r"^USE `([A-Za-z0-9_]+)`;$")


class SqlNotAllowed(Exception):
    """A fixture statement is outside the write allowlist (HTTP 403)."""


def parse_fixture(fixture_sql: str, database: str) -> list[str]:
    """Allowlisted statements only, in order; ``USE <database>`` is skipped."""
    statements: list[str] = []
    for raw_line in fixture_sql.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.endswith(";") or ";" in line[:-1]:
            raise SqlNotAllowed("multi-statement or unterminated SQL refused")
        if "/*" in line or line.startswith("--") or line.startswith("#"):
            raise SqlNotAllowed("comments refused in fixture SQL")
        used = _USE.match(line)
        if used is not None:
            if used.group(1) != database:
                raise SqlNotAllowed(f"USE refused for another database: {used.group(1)}")
            continue
        inserted = _INSERT_PREFIX.match(line)
        if inserted is not None and inserted.group(1) in ALLOWED_TABLES:
            statements.append(line)
            continue
        raise SqlNotAllowed(f"non-allowlisted statement refused: {line[:40]}")
    return statements


class DbApplier(Protocol):
    def apply(self, world: str, population_id: str) -> dict[str, Any]: ...


def _default_connect(**kwargs: Any) -> Any:
    """Real driver seam; imported lazily so tests never need pymysql."""
    import pymysql

    return pymysql.connect(**kwargs)


class MariaDbFixtureApplier:
    """Applies one generated fixture to the world's MariaDB."""

    def __init__(
        self,
        config: DbConfig,
        worlds_root: Path,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        self._config = config
        self._worlds_root = Path(worlds_root)
        self._connect = connect or _default_connect

    def __repr__(self) -> str:  # never include credentials
        return (
            f"MariaDbFixtureApplier(worlds_root={str(self._worlds_root)!r}, "
            f"config={self._config!r})"
        )

    __str__ = __repr__

    def _fixture_path(self, world: str, population_id: str) -> Path:
        if WORLD_ID_PATTERN.fullmatch(world) is None:
            raise PopulationNotFound(f"unknown world: {world}")
        if POPULATION_ID_PATTERN.fullmatch(population_id) is None:
            raise PopulationNotFound(f"unknown population: {population_id}")
        return self._worlds_root / world / "population" / population_id / "fixture.sql"

    def apply(self, world: str, population_id: str) -> dict[str, Any]:
        fixture = self._fixture_path(world, population_id)
        if not fixture.is_file():
            raise PopulationNotFound(f"unknown population: {population_id}")
        statements = parse_fixture(fixture.read_text(encoding="utf-8"), database=self._config.name)
        conn = self._connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password(),
            database=self._config.name,
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            cursor = conn.cursor()
            try:
                for statement in statements:
                    cursor.execute(statement)
            finally:
                cursor.close()
        finally:
            conn.close()
        return {
            "status": "applied",
            "accounts": sum(s.startswith("INSERT INTO `login`") for s in statements),
            "characters": sum(s.startswith("INSERT INTO `char`") for s in statements),
            "statements": len(statements),
            "fixture": str(fixture),
        }
