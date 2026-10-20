"""The narrow DB write path: fixture allowlist guard + secret-file applier.

Only ``INSERT INTO ``login``/``char``/``skill``` statements from a generated
population fixture (plus the fixture's leading ``USE`` of the configured
database) are ever executed; anything else is refused before a connection is
opened.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dashboard_webapp.db_applier import (
    POPULATION_ID_PATTERN,
    MariaDbFixtureApplier,
    SqlNotAllowed,
    parse_fixture,
)
from dashboard_webapp.mariadb_source import DbConfig
from dashboard_webapp.population import PopulationNotFound

LOGIN = (
    "INSERT INTO `login` (`account_id`, `userid`, `user_pass`, `sex`, `email`, "
    "`group_id`, `state`, `pincode`, `pincode_change`) VALUES (2200000, "
    "X'7030', X'7030', 'M', '', 0, 0, X'31323334', UNIX_TIMESTAMP());"
)
CHAR = (
    "INSERT INTO `char` (`char_id`, `account_id`, `char_num`, `name`) VALUES "
    "(300000, 2200000, 0, X'7030');"
)
SKILL = "INSERT INTO `skill` (`char_id`, `id`, `lv`, `flag`) VALUES (300000, 1, 9, 0);"
FIXTURE = f"USE `ragnarok`;\n{LOGIN}\n{CHAR}\n{SKILL}\n"


# --------------------------------------------------------------- parse_fixture


def test_parse_fixture_keeps_inserts_in_order() -> None:
    statements = parse_fixture(FIXTURE, database="ragnarok")

    assert statements == [LOGIN, CHAR, SKILL]


def test_parse_fixture_refuses_update() -> None:
    with pytest.raises(SqlNotAllowed):
        parse_fixture("UPDATE `char` SET base_level = 99;\n", database="ragnarok")


def test_parse_fixture_refuses_delete_drop_and_truncate() -> None:
    for bad in (
        "DELETE FROM `char`;\n",
        "DROP TABLE `skill`;\n",
        "TRUNCATE `login`;\n",
    ):
        with pytest.raises(SqlNotAllowed):
            parse_fixture(bad, database="ragnarok")


def test_parse_fixture_refuses_use_of_another_database() -> None:
    with pytest.raises(SqlNotAllowed):
        parse_fixture("USE `mysql`;\n", database="ragnarok")


def test_parse_fixture_refuses_set_and_select() -> None:
    for bad in ("SET FOREIGN_KEY_CHECKS = 0;\n", "SELECT * FROM `char`;\n"):
        with pytest.raises(SqlNotAllowed):
            parse_fixture(bad, database="ragnarok")


def test_parse_fixture_refuses_multi_statement_line() -> None:
    with pytest.raises(SqlNotAllowed):
        parse_fixture(f"{LOGIN} {CHAR}\n", database="ragnarok")


def test_parse_fixture_refuses_comment_smuggling() -> None:
    for bad in (
        "/* sneaky */ INSERT INTO `login` (`account_id`) VALUES (1);\n",
        "-- sneaky\nINSERT INTO `login` (`account_id`) VALUES (1);\n",
    ):
        with pytest.raises(SqlNotAllowed):
            parse_fixture(bad, database="ragnarok")


def test_parse_fixture_refuses_insert_into_other_tables() -> None:
    for table in ("inventory", "guild", "login_log"):
        with pytest.raises(SqlNotAllowed):
            parse_fixture(f"INSERT INTO `{table}` (`id`) VALUES (1);\n", database="ragnarok")


def test_parse_fixture_skips_blank_lines() -> None:
    statements = parse_fixture(f"\n{LOGIN}\n\n{SKILL}\n", database="ragnarok")

    assert statements == [LOGIN, SKILL]


# -------------------------------------------------------- MariaDbFixtureApplier


class FakeCursor:
    def __init__(self, recorder: list[str]) -> None:
        self._recorder = recorder

    def execute(self, statement: str, *_args: Any) -> None:
        self._recorder.append(statement)

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self, recorder: list[str], kwargs: dict[str, Any]) -> None:
        self._recorder = recorder
        self.kwargs = kwargs
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._recorder)

    def close(self) -> None:
        self.closed = True


def _applier(tmp_path: Path, recorder: list[str], **overrides: Any) -> MariaDbFixtureApplier:
    secret = tmp_path / "db-root"
    secret.write_text("s3cret-password\n", encoding="utf-8")
    config = DbConfig(
        host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=secret
    )
    kwargs = {
        "config": config,
        "worlds_root": tmp_path / "worlds",
        "connect": lambda **kw: FakeConnection(recorder, kw),
    }
    kwargs.update(overrides)
    return MariaDbFixtureApplier(**kwargs)


def _stage_population(tmp_path: Path, fixture: str = FIXTURE) -> tuple[str, str]:
    world = tmp_path / "worlds" / "w1" / "population" / "pop-abcd00000001"
    world.mkdir(parents=True)
    (world / "fixture.sql").write_text(fixture, encoding="utf-8")
    return "w1", "pop-abcd00000001"


def test_applier_executes_only_allowlisted_inserts(tmp_path: Path) -> None:
    recorder: list[str] = []
    applier = _applier(tmp_path, recorder)
    world, population_id = _stage_population(tmp_path)

    result = applier.apply(world, population_id)

    assert recorder == [LOGIN, CHAR, SKILL]  # the USE line is never executed
    assert result == {
        "status": "applied",
        "accounts": 1,
        "characters": 1,
        "statements": 3,
        "fixture": str(
            tmp_path / "worlds" / "w1" / "population" / "pop-abcd00000001" / "fixture.sql"
        ),
    }


def test_applier_refuses_fixture_before_connecting(tmp_path: Path) -> None:
    recorder: list[str] = []
    applier = _applier(tmp_path, recorder)
    world, population_id = _stage_population(tmp_path, fixture="DROP DATABASE ragnarok;\n")

    with pytest.raises(SqlNotAllowed):
        applier.apply(world, population_id)

    assert recorder == []  # no connection was ever opened


def test_applier_missing_population_is_404_style(tmp_path: Path) -> None:
    applier = _applier(tmp_path, [])

    with pytest.raises(PopulationNotFound):
        applier.apply("w1", "pop-missing000001")


@pytest.mark.parametrize("bad_id", ["../escape", "a/b", ".", "..", "pop x"])
def test_applier_refuses_traversal_ids(tmp_path: Path, bad_id: str) -> None:
    applier = _applier(tmp_path, [])

    with pytest.raises(PopulationNotFound):
        applier.apply("w1", bad_id)


def test_applier_refuses_traversal_worlds(tmp_path: Path) -> None:
    applier = _applier(tmp_path, [])

    with pytest.raises(PopulationNotFound):
        applier.apply("../w1", "pop-abcd00000001")


def test_applier_reads_password_from_secret_file_only(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    secret = tmp_path / "db-root"
    secret.write_text("s3cret-password\n", encoding="utf-8")

    def connect(**kwargs: Any) -> FakeConnection:
        captured.update(kwargs)
        return FakeConnection([], kwargs)

    config = DbConfig(
        host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=secret
    )
    applier = MariaDbFixtureApplier(config=config, worlds_root=tmp_path / "worlds", connect=connect)
    world, population_id = _stage_population(tmp_path)

    applier.apply(world, population_id)

    assert captured["password"] == "s3cret-password"
    assert captured["database"] == "ragnarok"
    assert "s3cret-password" not in repr(config)
    assert "s3cret-password" not in repr(applier)


def test_applier_default_connect_is_lazy_so_tests_need_no_pymysql(tmp_path: Path) -> None:
    secret = tmp_path / "db-root"
    secret.write_text("x\n", encoding="utf-8")
    config = DbConfig(
        host="mariadb", port=3306, name="ragnarok", user="root", root_secret_file=secret
    )

    applier = MariaDbFixtureApplier(config=config, worlds_root=tmp_path / "worlds")

    assert applier._connect is not None  # seam exists, driver imported only on use


def test_id_patterns_reject_separators_and_traversal() -> None:
    assert POPULATION_ID_PATTERN.fullmatch("pop-abcd00000001")
    assert not POPULATION_ID_PATTERN.fullmatch("../escape")
    assert not POPULATION_ID_PATTERN.fullmatch("a/b")
    assert not POPULATION_ID_PATTERN.fullmatch("..")
