"""Fresh-world initialization bytes; no database or engine operations."""

import importlib
import importlib.util
from types import ModuleType

import pytest

MODULE = "robots.adapters.world_bootstrap_sql"


def adapter() -> ModuleType:
    assert importlib.util.find_spec(MODULE) is not None, "fresh-world SQL renderer missing"
    return importlib.import_module(MODULE)


def test_actual_pinned_schemas_use_one_selected_world_database() -> None:
    module = adapter()
    files = module.initialization_sql("test_world", "test_inter", "x" * 23)
    assert set(files) == {
        "10-main.sql",
        "20-logs.sql",
        "30-web.sql",
        "40-roulette.sql",
        "50-interserver.sql",
    }
    assert all(raw.startswith(b"USE `test_world`;\n") for raw in files.values())
    assert b"INSERT INTO `login`" not in files["10-main.sql"]
    assert files["50-interserver.sql"].count(b"INSERT INTO `login`") == 1


@pytest.mark.parametrize("field", ["database", "inter_user", "inter_password"])
@pytest.mark.parametrize("bad", ["", "x" * 24, "a'b", "a\\b", "a\nb", "é", None, True])
def test_invalid_fields_rejected_before_public_asset_reads(monkeypatch, field, bad) -> None:
    module = adapter()

    def forbidden():
        pytest.fail("invalid input reached public asset derivation", pytrace=False)

    monkeypatch.setattr(module, "derive", forbidden)
    values = {"database": "test_world", "inter_user": "test_inter", "inter_password": "x"}
    values[field] = bad
    with pytest.raises(ValueError, match="invalid bootstrap field"):
        module.initialization_sql(**values)


@pytest.mark.parametrize(
    ("output", "source"),
    [
        ("10-main.sql", "main.sql"),
        ("20-logs.sql", "logs.sql"),
        ("30-web.sql", "web.sql"),
        ("40-roulette.sql", "roulette_default_data.sql"),
    ],
)
def test_schema_body_preserves_actual_attested_public_bytes(output, source) -> None:
    module = adapter()
    files = module.initialization_sql("test_world", "test_inter", "x")
    assert files[output].removeprefix(b"USE `test_world`;\n") == module.derive()[source]


def test_server_row_is_not_a_player_or_privileged_account() -> None:
    raw = adapter().initialization_sql("test_world", "test_inter", "x")["50-interserver.sql"]
    assert raw == (
        b"USE `test_world`;\nINSERT INTO `login` "
        b"(`account_id`, `userid`, `user_pass`, `sex`, `email`, `group_id`, `state`) "
        b"VALUES (1, X'746573745f696e746572', X'78', 'S', '', 0, 0);\n"
    )
    assert b"IGNORE" not in raw
    assert b"REPLACE" not in raw


def test_actual_schema_projection_contains_seventy_disjoint_tables() -> None:
    module = adapter()
    schemas = importlib.import_module("robots.adapters.rathena_bootstrap_assets")
    files = module.initialization_sql("test_world", "test_inter", "x")
    tables = [
        table["name"] for raw in files.values() for table in schemas.schema_projection(raw)[0]
    ]
    assert len(tables) == len(set(tables)) == 70


@pytest.mark.parametrize("field", ["database", "inter_user", "inter_password"])
def test_string_subclasses_are_rejected_before_derivation(monkeypatch, field) -> None:
    module = adapter()

    class Substring(str):
        pass

    def forbidden():
        pytest.fail("string subclass reached public asset derivation", pytrace=False)

    monkeypatch.setattr(module, "derive", forbidden)
    values = {"database": "test_world", "inter_user": "test_inter", "inter_password": "x"}
    values[field] = Substring(values[field])
    with pytest.raises(ValueError, match="invalid bootstrap field"):
        module.initialization_sql(**values)


@pytest.mark.parametrize("error_type", [ValueError, KeyboardInterrupt])
def test_asset_derivation_failure_preserves_origin(monkeypatch, error_type) -> None:
    module = adapter()
    origin = error_type("synthetic public derivation failure")

    def failed():
        raise origin

    monkeypatch.setattr(module, "derive", failed)
    with pytest.raises(error_type) as caught:
        module.initialization_sql("test_world", "test_inter", "x")
    assert caught.value is origin
