"""Offline fixture SQL contracts; all inputs here are synthetic, never live secrets."""

import importlib
import re
from dataclasses import replace
from pathlib import Path

import pytest

from robots.adapters.world_test_fixture import FixtureAccount, render


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_id", True),
        ("account_id", 0),
        ("account_id", 1),
        ("account_id", 2**32),
        ("char_id", False),
        ("char_id", -1),
        ("char_id", 2**32),
        ("username", ""),
        ("username", "x" * 24),
        ("username", "bad'user"),
        ("username", "é"),
        ("username", None),
        ("password", ""),
        ("password", "x" * 24),
        ("password", "bad\n"),
        ("password", "é"),
        ("password", True),
        ("character", ""),
        ("character", "x" * 24),
        ("character", "bad name"),
        ("pincode", "123"),
        ("pincode", "12345"),
        ("pincode", "\uff11\uff12\uff13\uff14"),
        ("pincode", "1x34"),
        ("pincode", 1234),
        ("pincode", True),
    ],
)
def test_invalid_fields_are_rejected_without_echo(field, value):
    first = FixtureAccount(2000000, 150000, "run_one", "Synthetic!", "Run_One", "1357")
    second = FixtureAccount(2000001, 150001, "run_two", "Synthetic!", "Run_Two", "2468")
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render("ragnarok", (replace(first, **{field: value}), second))


@pytest.mark.parametrize("database", ["", "x" * 24, "a`;DROP", "é", None, True])
def test_database_is_bounded_identifier(database):
    first = FixtureAccount(2, 1, "run_one", "Synthetic!", "Run_One", "1357")
    second = FixtureAccount(3, 2, "run_two", "Synthetic!", "Run_Two", "2468")
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render(database, (first, second))


@pytest.mark.parametrize("field", ["account_id", "char_id", "username", "character"])
def test_duplicate_identities_are_rejected(field):
    first = FixtureAccount(2, 1, "run_one", "Synthetic!", "Run_One", "1357")
    second = FixtureAccount(3, 2, "run_two", "Synthetic!", "Run_Two", "2468")
    value = getattr(first, field)
    if type(value) is str:
        value = value.swapcase()
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render("ragnarok", (first, replace(second, **{field: value})))


@pytest.mark.parametrize("count", [0, 1, 3])
def test_exactly_two_accounts_required(count):
    first = FixtureAccount(2, 1, "run_one", "Synthetic!", "Run_One", "1357")
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render("ragnarok", (first,) * count)


def test_two_insert_only_novices_match_pinned_schema():
    module = importlib.import_module("robots.adapters.world_test_fixture")
    accounts = tuple(
        module.FixtureAccount(
            2000000 + i, 150000 + i, f"run_test_{i}", "Synthetic!", f"Run_Test_{i}", "1357"
        )
        for i in range(2)
    )
    sql = module.render("ragnarok", accounts).decode("ascii")
    assert sql.startswith("USE `ragnarok`;\n")
    assert len(re.findall(r"INSERT INTO `login`", sql)) == 2
    assert len(re.findall(r"INSERT INTO `char`", sql)) == 2
    assert len(re.findall(r"INSERT INTO `skill`", sql)) == 2
    assert not re.search(r"\b(UPDATE|DELETE|REPLACE|IGNORE|DUPLICATE|DROP|TRUNCATE)\b", sql)
    assert "Synthetic!" not in sql
    source = Path(
        "/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/sql-files/main.sql"
    ).read_text()
    for table, columns in re.findall(r"INSERT INTO `(\w+)` \(([^)]+)\)", sql):
        ddl = source.split(f"CREATE TABLE IF NOT EXISTS `{table}` (", 1)[1].split(") ENGINE=", 1)[0]
        assert all(f"`{column}`" in ddl for column in re.findall(r"`([^`]+)`", columns))
    assert "`pincode_change`" in sql
    assert sql.count("UNIX_TIMESTAMP()") == 2
    assert sql.count("'M'") == 4
    assert sql.count("150, 150") == 2
    assert sql.count("152, 150") == 2
    assert sql.count(", 1, 9, 0);") == 2
    assert "Synthetic!" not in repr(accounts)
    decoded = [bytes.fromhex(value).decode("ascii") for value in re.findall(r"X'([0-9a-f]+)'", sql)]
    assert decoded == [
        value
        for account in accounts
        for value in (account.username, account.password, account.pincode, account.character)
    ]
    assert "PRIMARY KEY  (`account_id`)" in source
    assert "UNIQUE KEY `name_key` (`name`)" in source
    assert "PRIMARY KEY  (`char_id`,`id`)" in source
    assert sql.count("0, 10, 10, 1, 1, 1, 1, 1, 1, 40, 40, 11, 11") == 2
    root = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
    skill = (root / "db/pre-re/skill_db.yml").read_text()
    tree = (root / "db/pre-re/skill_tree.yml").read_text()
    assert "- Id: 1\n    Name: NV_BASIC\n    Description: Basic Skill\n    MaxLevel: 9" in skill
    assert "- Job: Novice\n    Tree:\n      - Name: NV_BASIC\n        MaxLevel: 9" in tree


def test_receiver_boundaries_hex_quotes_and_low_ids():
    first = FixtureAccount(2, 1, "a" * 23, "'\\\";" + "x" * 19, "A" * 23, "0000")
    second = FixtureAccount(2**32 - 1, 2**32 - 1, "b" * 23, "x" * 23, "B" * 23, "9999")
    sql = render("x" * 23, (first, second)).decode("ascii")
    assert bytes.fromhex(re.findall(r"X'([0-9a-f]+)'", sql)[1]).decode("ascii") == first.password
    assert len(sql.splitlines()) == 7


@pytest.mark.parametrize("invalid", [None, [], (), (None, None)])
def test_nonprimitive_account_containers_are_rejected(invalid):
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render("ragnarok", invalid)


def test_string_subclasses_rejected_before_encoding():
    class Strange(str):
        def encode(self, *_args, **_kwargs):
            pytest.fail("untrusted encoding called")

    first = FixtureAccount(2, 1, Strange("run_one"), "Synthetic!", "Run_One", "1357")
    second = FixtureAccount(3, 2, "run_two", "Synthetic!", "Run_Two", "2468")
    with pytest.raises(ValueError, match=r"^invalid fixture input$"):
        render("ragnarok", (first, second))
