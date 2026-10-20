"""MariaDB read-only source tests: SQL guard, row mapping, connection wiring.

All tests run against a fake connection/cursor (no server). The real driver is
imported lazily so the suite never needs pymysql installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dashboard_webapp.config import SecretFileError, read_secret
from dashboard_webapp.mariadb_source import (
    AGENT_SQL,
    INVENTORY_SQL,
    DbConfig,
    MariaDbAgentSource,
    ReadOnlyViolation,
    assert_read_only,
)


def test_assert_read_only_allows_reads() -> None:
    assert_read_only("SELECT 1")
    assert_read_only("  select `char_id` from `char`")
    assert_read_only("SHOW TABLES")
    assert_read_only("DESCRIBE `char`")


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE `char` SET online=1",
        "DELETE FROM `char`",
        "INSERT INTO `char` VALUES (1)",
        "DROP TABLE `char`",
        "ALTER TABLE `char` ADD COLUMN x INT",
        "CREATE TABLE t (id INT)",
        "SET GLOBAL x=1",
        "GRANT ALL ON *.* TO 'x'",
        "REPLACE INTO `char` VALUES (1)",
        "TRUNCATE `char`",
        "CALL something()",
        "",
        "/* sneaky */ UPDATE `char` SET online=1",
        "; DELETE FROM `char`",
    ],
)
def test_assert_read_only_rejects_writes(sql: str) -> None:
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql)


def test_shipped_sql_constants_are_read_only() -> None:
    assert_read_only(AGENT_SQL)
    assert_read_only(INVENTORY_SQL)
    assert "FROM `char`" in AGENT_SQL
    assert "WHERE char_id" in INVENTORY_SQL


class FakeCursor:
    """Routes fetch results by the SQL just executed, like a real driver would."""

    def __init__(
        self, agent_rows: list[dict[str, Any]], inventory_rows: list[dict[str, Any]]
    ) -> None:
        self._agent_rows = agent_rows
        self._inventory_rows = inventory_rows
        self.executed: list[tuple[str, tuple]] = []

    def execute(self, sql: str, args: tuple = ()) -> None:
        self.executed.append((sql, args))

    def _rows(self) -> list[dict[str, Any]]:
        last_sql = self.executed[-1][0] if self.executed else ""
        if "`inventory`" in last_sql:
            return self._inventory_rows
        return self._agent_rows

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows()

    def fetchone(self) -> dict[str, Any] | None:
        rows = self._rows()
        return rows[0] if rows else None

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(
        self, agent_rows: list[dict[str, Any]], inventory_rows: list[dict[str, Any]] | None = None
    ) -> None:
        self.cursor_obj = FakeCursor(agent_rows, inventory_rows or [])
        self.kwargs: dict[str, Any] = {}
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def close(self) -> None:
        self.closed = True


def _agent_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "char_id": 150001,
        "account_id": 2000001,
        "name": "Fx_0",
        "class": 0,
        "base_level": 9,
        "job_level": 7,
        "hp": 55,
        "sp": 12,
        "max_hp": 60,
        "max_sp": 22,
        "last_x": 152,
        "last_y": 150,
        "last_map": "prontera",
        "online": 1,
        "str": 5,
        "agi": 6,
        "vit": 7,
        "int": 8,
        "dex": 9,
        "luk": 10,
        "zeny": 50,
        "status_point": 48,
        "skill_point": 9,
    }
    row.update(overrides)
    return row


def _config(tmp_path: Path) -> DbConfig:
    secret = tmp_path / "db-root"
    secret.write_text("pw-from-file\n")
    return DbConfig(
        host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=secret
    )


def test_list_agents_maps_rows(tmp_path: Path) -> None:
    conn = FakeConnection(
        [_agent_row(), _agent_row(char_id=150002, name="Fx_1", online=0, last_map="prt_fild08")]
    )
    source = MariaDbAgentSource(_config(tmp_path), connect=lambda **_kw: conn)

    agents = source.list_agents()

    assert agents[0].char_id == 150001
    assert agents[0].name == "Fx_0"
    assert agents[0].char_class == 0
    assert agents[0].online is True
    assert agents[0].map == "prontera"
    assert agents[0].x == 152
    assert agents[0].y == 150
    assert agents[0].goal is None
    assert agents[0].plan is None
    assert agents[1].online is False
    # the executed SQL is the shipped read-only one
    assert conn.cursor_obj.executed[0][0] == AGENT_SQL


def test_summary_mapping_tolerates_missing_columns(tmp_path: Path) -> None:
    conn = FakeConnection([{"char_id": 1, "name": "Minimal"}])
    source = MariaDbAgentSource(_config(tmp_path), connect=lambda **_kw: conn)

    (agent,) = source.list_agents()
    assert agent.char_class is None
    assert agent.online is False
    assert agent.map == ""


def test_agent_detail_maps_inventory_and_stats(tmp_path: Path) -> None:
    conn = FakeConnection(
        [_agent_row()],
        inventory_rows=[
            {"nameid": 909, "amount": 12, "equip": 0, "identify": 1, "refine": 0, "attribute": 0},
            {"nameid": 1201, "amount": 1, "equip": 2, "identify": 1, "refine": 5, "attribute": 0},
        ],
    )
    source = MariaDbAgentSource(_config(tmp_path), connect=lambda **_kw: conn)

    detail = source.agent_detail(150001)

    assert detail.agent.char_id == 150001
    assert [i.nameid for i in detail.inventory] == [909, 1201]
    assert detail.inventory[1].refine == 5
    assert detail.stats["str"] == 5
    assert detail.stats["int"] == 8
    assert detail.stats["max_hp"] == 60
    assert detail.stats["zeny"] == 50
    # inventory fetch used the shipped parameterized read-only query
    inventory_calls = [call for call in conn.cursor_obj.executed if "`inventory`" in call[0]]
    assert inventory_calls == [(INVENTORY_SQL, (150001,))]
    assert conn.closed is True


def test_detail_unknown_agent_raises(tmp_path: Path) -> None:
    conn = FakeConnection([])
    source = MariaDbAgentSource(_config(tmp_path), connect=lambda **_kw: conn)

    from dashboard_webapp.repository import UnknownAgentError

    with pytest.raises(UnknownAgentError):
        source.agent_detail(424242)


def test_connect_receives_secret_password_and_read_only_init(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_connect(**kw: Any) -> FakeConnection:
        captured.update(kw)
        return FakeConnection([_agent_row()])

    MariaDbAgentSource(_config(tmp_path), connect=fake_connect).list_agents()

    assert captured["host"] == "mariadb"
    assert captured["port"] == 3306
    assert captured["database"] == "ragnarok"
    assert captured["user"] == "root"
    assert captured["password"] == "pw-from-file"
    assert captured["charset"] == "utf8mb4"
    assert captured["autocommit"] is True
    assert captured["init_command"] == "SET SESSION TRANSACTION READ ONLY"


def test_db_config_password_reads_file_and_repr_hides_it(tmp_path: Path) -> None:
    secret = tmp_path / "db-root"
    secret.write_text("topsecret")
    cfg = DbConfig(host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=secret)

    assert cfg.password() == "topsecret"
    assert "topsecret" not in repr(cfg)
    assert "topsecret" not in str(cfg)
    assert str(secret) in repr(cfg)


def test_missing_secret_file_propagates_path_error(tmp_path: Path) -> None:
    cfg = DbConfig(
        host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=tmp_path / "nope"
    )
    with pytest.raises(SecretFileError) as excinfo:
        cfg.password()
    assert str(tmp_path / "nope") in str(excinfo.value)


def test_read_secret_helper_matches_config_contract(tmp_path: Path) -> None:
    secret = tmp_path / "db-root"
    secret.write_text("v\n")
    assert read_secret(secret) == "v"
