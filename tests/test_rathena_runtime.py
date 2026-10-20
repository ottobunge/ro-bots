"""Offline tracer uses public pinned assets and synthetic private inputs only."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from robots.adapters import rathena_runtime as runtime
from robots.adapters import rathena_runtime_assets as assets
from robots.adapters import rathena_runtime_io as bundle_io


def synthetic_config() -> dict[str, object]:
    return {
        "server_mode": "MAIN-pre-re-20180704",
        "db_host": "sql.synthetic.invalid",
        "db_port": 13306,
        "db_name": "synthetic_world",
        "db_user": "synthetic_user",
        "db_password": "SyntheticOnly!9",
        "inter_user": "synthetic_inter",
        "inter_password": "SyntheticOnly!8",
        "bind_ip": "192.0.2.10",
        "login_ip": "192.0.2.11",
        "char_ip": "192.0.2.12",
        "map_ip": "192.0.2.13",
        "login_port": 16900,
        "char_port": 16121,
        "map_port": 15121,
        "pincode_enabled": False,
    }


def private_input(root: Path) -> Path:
    path = root / "private.json"
    path.write_text(json.dumps(synthetic_config()))
    path.chmod(0o600)
    return path


def test_interserver_password_24_bytes_rejected(tmp_path):
    data = synthetic_config() | {"inter_password": "x" * 24}
    with pytest.raises(bundle_io.BundleRejectedError, match="unsupported private field length"):
        runtime.build_from_bytes("test", tmp_path / "test", json.dumps(data).encode())
    assert not (tmp_path / "test").exists()


def test_password_maxima_populated_bundle_readback(tmp_path):
    data = synthetic_config() | {"inter_password": "x" * 23, "db_password": "y" * 32}
    destination = tmp_path / "test"
    manifest = runtime.build_from_bytes("test", destination, json.dumps(data).encode())
    assert manifest == json.loads((destination / "manifest.json").read_text())
    assert manifest["launchable"] is False
    npc_files = manifest["npc_files"]
    checked_maps = manifest["mapcache_checked_maps"]
    assert isinstance(npc_files, int)
    assert npc_files > 100
    assert isinstance(checked_maps, int)
    assert checked_maps > 100
    for role in ("char", "map"):
        assert (
            f"passwd: {data['inter_password']}\n"
            in (destination / f"conf/{role}_athena.conf").read_text()
        )
    assert (
        f"login_server_pw: {data['db_password']}\n"
        in (destination / "conf/inter_athena.conf").read_text()
    )
    assert (destination / "bin/map-server").stat().st_mode & 0o777 == 0o600
    for field in ("inter_password", "db_password"):
        assert str(data[field]) not in json.dumps(manifest)


@pytest.mark.parametrize(
    ("field", "length"),
    [("inter_password", 24), ("inter_password", 32), ("inter_password", 33), ("db_password", 33)],
)
def test_password_length_rejected_before_assets_or_destination(
    tmp_path, monkeypatch, field, length
):
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid password reached public assets or destination creation")

    monkeypatch.setattr(runtime, "public_assets", forbidden)
    monkeypatch.setattr(runtime, "directory", forbidden)
    destination = tmp_path / "absent-parent" / "test"
    data = synthetic_config() | {field: "x" * length}
    with pytest.raises(bundle_io.BundleRejectedError, match="unsupported private field length"):
        runtime.build_from_bytes("test", destination, json.dumps(data).encode())
    assert not destination.parent.exists()


@pytest.mark.parametrize("use_stdin", [False, True], ids=["file", "stdin"])
@pytest.mark.parametrize(
    ("field", "length", "accepted"),
    [
        ("inter_password", 23, True),
        ("inter_password", 24, False),
        ("inter_password", 32, False),
        ("inter_password", 33, False),
        ("db_password", 32, True),
        ("db_password", 33, False),
    ],
)
def test_password_boundary_cli_redaction(tmp_path, use_stdin, field, length, accepted):
    data = synthetic_config() | {field: "x" * length}
    raw = json.dumps(data).encode()
    source = tmp_path / "boundary-input.json"
    source.write_bytes(raw)
    source.chmod(0o600)
    destination = tmp_path / "test"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robots.adapters.rathena_runtime",
            "--world",
            "test",
            "--destination",
            str(destination),
            "--secret-file",
            "-" if use_stdin else str(source),
        ],
        input=raw if use_stdin else None,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == (0 if accepted else 2)
    for private_field in ("db_password", "inter_password", "db_host", "db_user", "inter_user"):
        assert str(data[private_field]).encode() not in result.stdout + result.stderr
    assert destination.exists() is accepted
    if accepted:
        assert json.loads(result.stdout)["launchable"] is False
        assert (destination / "manifest.json").is_file()
        assert result.stderr == b""
    else:
        assert result.stdout == b""
        assert result.stderr == (
            b"offline bundle rejected; owned partial output may remain, never launch\n"
        )


def test_populated_bundle_readback(tmp_path):
    spec = importlib.util.find_spec("robots.adapters.rathena_runtime")
    assert spec is not None, "offline private runtime builder is missing"
    runtime = importlib.import_module("robots.adapters.rathena_runtime")
    destination = tmp_path / "test"
    manifest = runtime.build_bundle("test", destination, private_input(tmp_path))
    assert manifest == json.loads((destination / "manifest.json").read_text())
    assert manifest["launchable"] is False
    assert manifest["source_nar"] == "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI="
    assert manifest["npc_files"] > 100
    assert manifest["mapcache_checked_maps"] > 100
    assert manifest["configured_maps_missing_from_cache"] == []
    assert (destination / "db/pre-re/item_db.yml").is_file()
    assert (destination / "npc/pre-re/scripts_main.conf").is_file()
    assert (destination / "bin/map-server").is_file()
    assert not (destination / "sql-files").exists()
    for path in destination.rglob("*"):
        assert path.stat().st_uid == os.geteuid()
        assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600)
    summary = json.dumps(manifest)
    assert all(
        str(synthetic_config()[k]) not in summary
        for k in ("db_host", "db_user", "db_name", "db_password", "inter_user", "inter_password")
    )
    config = (destination / "conf/inter_athena.conf").read_text()
    for prefix in ("login_server", "char_server", "map_server", "log_db", "ipban_db"):
        assert f"{prefix}_pw: {synthetic_config()['db_password']}\n" in config
    assert "pincode_enabled: no\n" in (destination / "conf/char_athena.conf").read_text()
    assert not any(
        line.startswith("subnet:")
        for line in (destination / "conf/subnet_athena.conf").read_text().splitlines()
    ), "upstream loopback subnet must not override explicit endpoint configuration"
    assert all(
        b"Path: conf/import/" not in path.read_bytes()
        for path in (destination / "conf").glob("*.yml")
    ), "all selected configuration YAML imports must be resolved, not only inter_server"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("server_mode", "RE-20180704"),
        ("db_port", True),
        ("db_port", 0),
        ("map_port", 65536),
        ("db_host", "localhost"),
        ("db_host", "127.0.0.1"),
        ("db_host", "mysql://synthetic.invalid"),
        ("db_password", 'quote"hazard'),
        ("db_password", "line\nbreak"),
        ("inter_password", "semi;colon"),
        ("db_user", "import:evil"),
        ("db_name", "a" * 24),
        ("db_password", "a" * 33),
        ("inter_user", 12),
        ("pincode_enabled", 1),
        ("bind_ip", "0.0.0.0"),
        ("char_ip", "127.0.0.1"),
        ("map_ip", "invalid"),
    ],
)
def test_private_field_hazards_fail_before_creation(tmp_path, field, value):
    data = synthetic_config() | {field: value}
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", tmp_path / "test", json.dumps(data).encode())
    assert not (tmp_path / "test").exists()


@pytest.mark.parametrize(
    "raw", [b"{}", b"[]", b"{", b"\xff", b"{}" * 5000, b'{"db_user":"one","db_user":"two"}']
)
def test_schema_rejection(tmp_path, raw):
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", tmp_path / "test", raw)
    assert not (tmp_path / "test").exists()


@pytest.mark.parametrize("world", ["default", "prod", "test/other", "prod-", "debug\n"])
def test_world_identity_rejection(tmp_path, world):
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes(world, tmp_path / "test", json.dumps(synthetic_config()).encode())


def test_existing_target_preserved(tmp_path):
    target = tmp_path / "test"
    target.mkdir()
    sentinel = target / "unrelated"
    sentinel.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        runtime.build_bundle("test", target, private_input(tmp_path))
    assert sentinel.read_bytes() == b"preserve"
    assert list(target.iterdir()) == [sentinel]


def test_symlink_ancestors_and_input_rejected(tmp_path):
    source = private_input(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(NotADirectoryError):
        runtime.build_bundle("test", alias / "test", source)
    secret_alias = tmp_path / "secret-alias"
    secret_alias.symlink_to(source)
    with pytest.raises(OSError, match="Too many levels"):
        runtime.build_bundle("test", tmp_path / "test", secret_alias)
    assert not (tmp_path / "test").exists()


def test_private_input_modes(tmp_path):
    source = private_input(tmp_path)
    source.chmod(0o644)
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_bundle("test", tmp_path / "test", source)


def test_two_world_separation(tmp_path):
    first = runtime.build_bundle("test", tmp_path / "test", private_input(tmp_path))
    second_data = synthetic_config() | {
        "db_name": "synthetic_debug",
        "inter_password": "OtherSynthetic!",
    }
    second = runtime.build_from_bytes("debug", tmp_path / "debug", json.dumps(second_data).encode())
    assert first["world"] != second["world"]
    assert (tmp_path / "test/conf/inter_athena.conf").read_bytes() != (
        tmp_path / "debug/conf/inter_athena.conf"
    ).read_bytes()
    assert (tmp_path / "test/npc/pre-re/scripts_main.conf").stat().st_ino != (
        tmp_path / "debug/npc/pre-re/scripts_main.conf"
    ).stat().st_ino
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("debug", tmp_path / "test", json.dumps(second_data).encode())


def test_partial_io_retains_owned_frontier_and_origin(tmp_path, monkeypatch):
    unrelated = tmp_path / "unrelated"
    unrelated.write_bytes(b"preserve")
    real_write = bundle_io.write_at
    origin = KeyboardInterrupt("synthetic failure")

    def failing_write(fd, name, content):
        real_write(fd, name, content)
        if name == "LICENSE":
            raise origin

    monkeypatch.setattr(runtime, "write_at", failing_write)
    with pytest.raises(KeyboardInterrupt) as caught:
        runtime.build_bundle("test", tmp_path / "test", private_input(tmp_path))
    assert caught.value is origin
    assert unrelated.read_bytes() == b"preserve"
    assert (tmp_path / "test/INCOMPLETE").is_file()
    assert not (tmp_path / "test/manifest.json").exists()


def test_missing_public_asset_has_no_output(tmp_path, monkeypatch):
    original = bundle_io.read_path

    def missing_asset(path):
        if path.name == "Global_Functions.txt":
            raise FileNotFoundError
        return original(path)

    monkeypatch.setattr(assets, "read_path", missing_asset)
    with pytest.raises(FileNotFoundError):
        runtime.build_bundle("test", tmp_path / "test", private_input(tmp_path))
    assert not (tmp_path / "test").exists()


@pytest.mark.parametrize("use_stdin", [False, True])
def test_actual_cli_input_and_redaction(tmp_path, use_stdin):
    source = private_input(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robots.adapters.rathena_runtime",
            "--world",
            "test",
            "--destination",
            str(tmp_path / "test"),
            "--secret-file",
            "-" if use_stdin else str(source),
        ],
        input=source.read_bytes() if use_stdin else None,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["launchable"] is False
    for field in ("db_password", "inter_password", "db_host"):
        assert str(synthetic_config()[field]).encode() not in result.stdout + result.stderr
    assert (tmp_path / "test/manifest.json").is_file()


def test_cli_rejection_redacts_input(tmp_path):
    raw = json.dumps(synthetic_config() | {"db_password": "SensitiveSynthetic;Hazard"}).encode()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robots.adapters.rathena_runtime",
            "--world",
            "test",
            "--destination",
            str(tmp_path / "test"),
            "--secret-file",
            "-",
        ],
        input=raw,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert b"SensitiveSynthetic" not in result.stdout + result.stderr
    assert not (tmp_path / "test").exists()


def test_configuration_cycle_rejected(monkeypatch):
    monkeypatch.setattr(assets, "read_path", lambda _path: b"import: conf/cycle.conf\n")
    with pytest.raises(bundle_io.BundleRejectedError, match="cyclic"):
        assets.config_asset("conf/cycle.conf", {}, set())
