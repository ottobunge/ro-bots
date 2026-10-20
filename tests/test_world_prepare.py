"""Private host-side preparation, never native startup or database execution."""

import importlib
import importlib.util
import os
import re
import stat
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from robots.adapters.rathena_bootstrap_assets import schema_projection
from robots.adapters.rathena_runtime_assets import public_assets
from robots.adapters.world_compose import WorldSelection

MODULE = "robots.adapters.world_prepare"


def adapter() -> ModuleType:
    assert importlib.util.find_spec(MODULE) is not None, "host world preparation API missing"
    return importlib.import_module(MODULE)


def settings(module: ModuleType, **changes: object) -> Any:
    values: dict[str, object] = {
        "db_name": "fixture_world",
        "db_user": "fixture_database",
        "db_password": "d" * 32,
        "inter_user": "fixture_inter",
        "inter_password": "i" * 23,
        "root_password": "r" * 32,
    }
    values.update(changes)
    return module.PreparationSettings(**values)


def fields(path: Path) -> dict[str, str]:
    return dict(
        line.split(": ", 1) for line in path.read_text("ascii").splitlines() if ": " in line
    )


def test_actual_pinned_stage_has_container_roles_and_matching_private_bootstrap(tmp_path):
    assets, report = public_assets()
    assert len(assets) == 679
    module = adapter()
    config = settings(module)
    target = tmp_path / "fixture-stage"
    summary = module.create(target, WorldSelection("test"), config)
    runtime = target / "runtime"
    assert all((runtime / name).read_bytes() == raw for name, raw in assets.items())
    assert summary["asset_files"] == len(assets)
    assert summary["npc_files"] == report["npc_files"]
    assert summary["mapcache_checked_maps"] == report["mapcache_checked_maps"]
    assert summary["world"] == "test"
    assert summary["provisioning"] is False
    assert summary["native_parser_ran"] is False
    assert summary["host_bind_mount_ready"] is False
    assert summary["container_paths"]["runtime"] == "/world/runtime"
    login = fields(runtime / "conf/login_athena.conf")
    char = fields(runtime / "conf/char_athena.conf")
    map_role = fields(runtime / "conf/map_athena.conf")
    assert all(role["bind_ip"] == "0.0.0.0" for role in (login, char, map_role))
    assert char["login_ip"] == "rathena-login"
    assert char["char_ip"] == map_role["map_ip"] == "127.0.0.1"
    assert map_role["char_ip"] == "rathena-char"
    assert char["server_name"] == "RO Bots"
    inter = fields(runtime / "conf/inter_athena.conf")
    for prefix in ("login_server", "ipban_db", "char_server", "map_server", "log_db", "web_server"):
        assert inter[prefix + "_ip"] == "mariadb"
        assert inter[prefix + "_port"] == "3306"
        assert bool(inter[prefix + "_db"] == config.db_name)
        assert bool(inter[prefix + "_pw"] == config.db_password)
    check_private_bootstrap(target, config, char)
    assert (runtime / "log").is_dir()
    assert (target / "memory/agents").is_dir()
    for path in [target, *target.rglob("*")]:
        info = path.stat()
        assert info.st_uid == os.geteuid()
        assert stat.S_IMODE(info.st_mode) == (0o700 if path.is_dir() else 0o600)
    assert config.db_password not in repr(config)
    assert config.inter_password not in repr(summary)
    assert "public_assets" not in summary
    assert not (target / "manifest.json").exists()


def check_private_bootstrap(target: Path, config: Any, char: dict[str, str]) -> None:
    sql_files = sorted((target / "sql").glob("*.sql"))
    assert len(sql_files) == 5
    tables = [
        table["name"] for path in sql_files for table in schema_projection(path.read_bytes())[0]
    ]
    assert len(tables) == len(set(tables)) == 70
    prefix = f"USE `{config.db_name}`;\n".encode("ascii")
    assert all(path.read_bytes().startswith(prefix) for path in sql_files)
    assert b"INSERT INTO `login`" not in sql_files[0].read_bytes()
    account = sql_files[-1].read_bytes()
    match = re.search(rb"VALUES \(1, X'([0-9a-f]+)', X'([0-9a-f]+)', 'S', '', 0, 0\);", account)
    assert match is not None
    assert bool(bytes.fromhex(match[1].decode()).decode() == char["userid"] == config.inter_user)
    assert bool(
        bytes.fromhex(match[2].decode()).decode() == char["passwd"] == config.inter_password
    )
    assert bool((target / "secrets/db-root").read_text() == config.root_password)
    assert bool((target / "secrets/db-user").read_text() == config.db_password)


@pytest.mark.parametrize(
    "field", ["db_name", "db_user", "db_password", "inter_user", "inter_password", "root_password"]
)
@pytest.mark.parametrize("bad", ["", "a'b", "a\\b", "a\nb", "é", None, True])
def test_unsafe_private_fields_reject_before_assets_or_allocation(
    tmp_path, monkeypatch, field, bad
):
    module = adapter()

    def forbidden():
        pytest.fail("invalid input reached assets", pytrace=False)

    monkeypatch.setattr(module, "public_assets", forbidden)
    target = tmp_path / "not-created"
    with pytest.raises(ValueError, match=r"required|unsafe|unsupported|bounded|private"):
        module.create(target, WorldSelection("debug"), settings(module, **{field: bad}))
    assert not target.exists()


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("db_name", "x" * 24),
        ("db_user", "x" * 24),
        ("inter_user", "x" * 24),
        ("db_password", "x" * 33),
        ("inter_password", "x" * 24),
        ("root_password", "x" * 33),
        ("display_name", "x" * 20),
        ("display_name", "bad\nlabel"),
        ("server_mode", "Renewal"),
        ("server_mode", None),
        ("db_host", "localhost"),
        ("db_port", 3307),
        ("db_port", True),
        ("bind_ip", "127.0.0.1"),
        ("login_host", "127.0.0.1"),
        ("char_host", "other"),
        ("advertised_char_ip", "rathena-char"),
        ("advertised_map_ip", "rathena-map"),
        ("advertised_char_ip", "0.0.0.0"),
        ("advertised_map_ip", "224.0.0.1"),
        ("login_port", True),
        ("char_port", 0),
        ("map_port", 65536),
        ("map_port", "5121"),
        ("map_port", 6121),
        ("pincode_enabled", 1),
        ("display_name", ""),
    ],
)
def test_compose_contract_rejects_invalid_inputs_before_reads(tmp_path, monkeypatch, field, bad):
    module = adapter()

    def forbidden():
        pytest.fail("invalid input reached assets", pytrace=False)

    monkeypatch.setattr(module, "public_assets", forbidden)
    target = tmp_path / "not-created"
    with pytest.raises(ValueError, match=r"required|unsafe|unsupported|bounded|private"):
        module.create(target, WorldSelection("test"), settings(module, **{field: bad}))
    assert not target.exists()


@pytest.mark.parametrize("kind", ["empty", "foreign", "file", "dangling"])
def test_existing_target_refused_before_public_reads(tmp_path, monkeypatch, kind):
    module = adapter()
    target = tmp_path / "existing"
    if kind in ("empty", "foreign"):
        target.mkdir()
        if kind == "foreign":
            (target / "sentinel").write_bytes(b"foreign-data")
    elif kind == "file":
        target.write_bytes(b"foreign-data")
    else:
        target.symlink_to(tmp_path / "missing")

    def forbidden():
        pytest.fail("existing target reached public reads", pytrace=False)

    monkeypatch.setattr(module, "public_assets", forbidden)
    with pytest.raises(FileExistsError):
        module.create(target, WorldSelection("test"), settings(module))
    if kind == "foreign":
        assert (target / "sentinel").read_bytes() == b"foreign-data"
    if kind == "file":
        assert target.read_bytes() == b"foreign-data"
    if kind == "dangling":
        assert target.is_symlink()


@pytest.mark.parametrize("field", ["selection", "settings"])
def test_wrong_api_schema_rejected_before_reads(tmp_path, monkeypatch, field):
    module = adapter()
    values = {"selection": WorldSelection("test"), "settings": settings(module)}
    values[field] = None

    def forbidden():
        pytest.fail("wrong API schema reached public reads", pytrace=False)

    monkeypatch.setattr(module, "public_assets", forbidden)
    target = tmp_path / "no-output"
    with pytest.raises(ValueError, match=r"required|unsafe|unsupported|bounded|private"):
        module.create(target, **values)
    assert not target.exists()


def test_endpoint_error_does_not_echo_private_input(tmp_path):
    module = adapter()
    bad = "sensitive-invalid-address"
    with pytest.raises(ValueError, match="advertised host IPv4 required") as caught:
        module.create(
            tmp_path / "no-output", WorldSelection("test"), settings(module, advertised_char_ip=bad)
        )
    assert bad not in str(caught.value)


@pytest.mark.parametrize("seam", ["public_assets", "initialization_sql"])
@pytest.mark.parametrize("error_type", [ValueError, KeyboardInterrupt])
def test_source_failure_preserves_origin_without_allocating(
    tmp_path, monkeypatch, seam, error_type
):
    module = adapter()
    origin = error_type("synthetic source failure")

    def failed(*args):
        raise origin

    monkeypatch.setattr(module, seam, failed)
    target = tmp_path / "no-output"
    with pytest.raises(error_type) as caught:
        module.create(target, WorldSelection("test"), settings(module))
    assert caught.value is origin
    assert not target.exists()


def test_write_failure_preserves_origin_and_does_not_claim_rollback(tmp_path, monkeypatch):
    module = adapter()
    origin = OSError("synthetic write failure")
    original = module._write
    calls = 0

    def failed(root, name, raw):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise origin
        original(root, name, raw)

    monkeypatch.setattr(module, "_write", failed)
    target = tmp_path / "partial"
    with pytest.raises(OSError, match="synthetic write failure") as caught:
        module.create(target, WorldSelection("test"), settings(module))
    assert caught.value is origin
    assert target.is_dir()
    assert sum(path.is_file() for path in target.rglob("*")) == 1
    assert not (target / "manifest.json").exists()


def test_long_world_identity_separate_display_and_custom_host_advertisements(tmp_path):
    module = adapter()
    selection = WorldSelection("prod-" + "x" * 58)
    config = settings(
        module,
        display_name="x" * 19,
        advertised_char_ip="192.0.2.10",
        advertised_map_ip="192.0.2.11",
        pincode_enabled=False,
        login_port=16900,
        char_port=16121,
        map_port=15121,
    )
    target = tmp_path / "long-world"
    previous = os.umask(0o777)
    try:
        summary = module.create(target, selection, config)
    finally:
        os.umask(previous)
    char = fields(target / "runtime/conf/char_athena.conf")
    map_role = fields(target / "runtime/conf/map_athena.conf")
    assert summary["world"] == selection.world
    assert char["server_name"] == "x" * 19
    assert char["char_ip"] == "192.0.2.10"
    assert map_role["map_ip"] == "192.0.2.11"
    assert map_role["char_ip"] == "rathena-char"
    assert char["pincode_enabled"] == "no"
    assert char["login_port"] == "16900"
    assert char["char_port"] == map_role["char_port"] == "16121"
    assert map_role["map_port"] == "15121"
    for path in [target, *target.rglob("*")]:
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize(
    "field",
    [
        "db_name",
        "db_user",
        "db_password",
        "inter_user",
        "inter_password",
        "root_password",
        "display_name",
        "char_host",
        "server_mode",
    ],
)
def test_private_string_subtypes_rejected_before_assets(tmp_path, monkeypatch, field):
    module = adapter()

    class Substring(str):
        pass

    config = settings(module)

    def forbidden():
        pytest.fail("string subtype reached source reads", pytrace=False)

    monkeypatch.setattr(module, "public_assets", forbidden)
    with pytest.raises(ValueError, match=r"required|unsafe|unsupported|bounded|private"):
        module.create(
            tmp_path / "no-output",
            WorldSelection("test"),
            settings(module, **{field: Substring(getattr(config, field))}),
        )
