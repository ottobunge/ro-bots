"""Offline filesystem import contract; no engine or SQL execution."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from robots.adapters.rathena_runtime_assets import public_assets
from robots.adapters.world_compose import WorldSelection
from robots.adapters.world_prepare import PreparationSettings, create

SCRIPT = Path(__file__).resolve().parents[1] / "nix/world-init/import-stage.py"
SQL_NAMES = (
    "10-main.sql",
    "20-logs.sql",
    "30-web.sql",
    "40-roulette.sql",
    "50-interserver.sql",
)


def stage(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "prepared"
    for name in ("runtime/conf", "runtime/log", "memory/agents", "logs", "sql", "secrets"):
        (source / name).mkdir(parents=True, exist_ok=True)
    (source / "runtime/conf/fixture.conf").write_bytes(b"opaque-config")
    for name in SQL_NAMES:
        (source / "sql" / name).write_bytes(b"opaque-sql")
    for name in ("db-root", "db-user"):
        (source / "secrets" / name).write_bytes(b"opaque-secret")
    (source / "compose-inputs.json").write_bytes(b"not-to-be-copied")
    destination = tmp_path / "world"
    destination.mkdir()
    return source, destination


def invoke(source: Path, destination: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--runtime-uid",
            str(os.getuid()),
            "--runtime-gid",
            str(os.getgid()),
            "--mysql-uid",
            str(os.getuid()),
            "--mysql-gid",
            str(os.getgid()),
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_copies_private_tree_into_empty_volume(tmp_path):
    source, destination = stage(tmp_path)
    result = invoke(source, destination)
    assert result.returncode == 0
    assert stat.S_IMODE(destination.stat().st_mode) == 0o755
    assert {path.name for path in destination.iterdir()} == {
        "runtime",
        "memory",
        "logs",
        "db",
        "secrets",
        *SQL_NAMES,
    }
    assert not list((destination / "db").iterdir())
    for subtree in ("runtime", "memory", "logs", "secrets"):
        for path in [destination / subtree, *(destination / subtree).rglob("*")]:
            info = path.stat()
            assert (info.st_uid, info.st_gid) == (os.getuid(), os.getgid())
            assert stat.S_IMODE(info.st_mode) == (0o700 if path.is_dir() else 0o600)
            if path.is_file():
                assert bool(
                    path.read_bytes() == (source / path.relative_to(destination)).read_bytes()
                )
    for name in SQL_NAMES:
        path = destination / name
        assert bool(path.read_bytes() == (source / "sql" / name).read_bytes())
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "opaque" not in result.stdout + result.stderr


@pytest.mark.parametrize("kind", ["sentinel", "debug", "prod", "worlddata"])
def test_nonempty_destination_is_unchanged(tmp_path, kind):
    source, destination = stage(tmp_path)
    foreign = destination / kind
    foreign.write_bytes(b"foreign-data")
    mode = destination.stat().st_mode
    result = invoke(source, destination)
    assert result.returncode != 0
    assert {p.name for p in destination.iterdir()} == {kind}
    assert foreign.read_bytes() == b"foreign-data"
    assert destination.stat().st_mode == mode


@pytest.mark.parametrize(
    "kind",
    [
        "missing-tree",
        "missing-sql",
        "unknown-sql",
        "link-file",
        "link-tree",
        "fifo",
        "secret-extra",
        "empty-runtime",
        "runtime-elf",
        "sql-directory",
        "secret-directory",
        "required-directory-file",
        "root-link",
    ],
)
def test_invalid_source_rejected_before_target_mutation(tmp_path, kind):
    source, destination = stage(tmp_path)
    if kind == "missing-tree":
        (source / "logs").rmdir()
    elif kind == "missing-sql":
        (source / "sql" / SQL_NAMES[0]).unlink()
    elif kind == "unknown-sql":
        (source / "sql/99-unrecognized.sql").write_bytes(b"private-unrecognized")
    elif kind == "link-file":
        (source / "runtime/conf/alias").symlink_to("fixture.conf")
    elif kind == "link-tree":
        (source / "runtime/alias").symlink_to("conf", target_is_directory=True)
    elif kind == "fifo":
        os.mkfifo(source / "runtime/pipe")
    elif kind == "secret-extra":
        (source / "secrets/extra").write_bytes(b"private-extra")
    elif kind == "runtime-elf":
        (source / "runtime/native").write_bytes(b"\x7fELFprivate-binary")
    elif kind in ("sql-directory", "secret-directory"):
        path = source / ("sql/10-main.sql" if kind == "sql-directory" else "secrets/db-root")
        path.unlink()
        path.mkdir()
    elif kind == "required-directory-file":
        (source / "logs").rmdir()
        (source / "logs").write_bytes(b"private-not-dir")
    elif kind == "root-link":
        (source / "metadata-link").symlink_to("compose-inputs.json")
    else:
        (source / "runtime/conf/fixture.conf").unlink()
    mode = destination.stat().st_mode
    result = invoke(source, destination)
    assert result.returncode != 0
    assert not list(destination.iterdir())
    assert destination.stat().st_mode == mode
    assert "private" not in result.stdout + result.stderr


@pytest.mark.parametrize("kind", ["absent", "file", "symlink", "same-source"])
def test_destination_must_be_existing_empty_real_directory(tmp_path, kind):
    source, destination = stage(tmp_path)
    destination.rmdir()
    if kind == "file":
        destination.write_bytes(b"foreign")
    elif kind == "symlink":
        destination.symlink_to(source, target_is_directory=True)
    elif kind == "same-source":
        destination = source
    result = invoke(source, destination)
    assert result.returncode != 0
    assert (source / "compose-inputs.json").read_bytes() == b"not-to-be-copied"


def test_actual_preparation_copy_has_679_public_assets_and_seven_configs(tmp_path):

    source = tmp_path / "actual-prepared"
    summary = create(
        source,
        WorldSelection("test"),
        PreparationSettings(
            "fixture_world", "fixture_db", "d" * 32, "fixture_inter", "i" * 23, "r" * 32
        ),
    )
    destination = tmp_path / "actual-world"
    destination.mkdir()
    result = invoke(source, destination)
    assert result.returncode == 0
    counts = json.loads(result.stdout)
    assert counts["runtime_files"] == 683
    assert counts["sql_files"] == 5
    assert counts["secret_files"] == 2
    assets, asset_report = public_assets()
    assert summary["asset_files"] == len(assets) == 679
    assert summary["npc_files"] == asset_report["npc_files"]
    assert all(
        bool((destination / "runtime" / name).read_bytes() == content)
        for name, content in assets.items()
        if not name.startswith("bin/")
    )
    assert all(
        not (destination / "runtime/bin" / f"{role}-server").exists()
        for role in ("login", "char", "map")
    )
    assert (destination / "runtime/log").is_dir()
    assert not (destination / "manifest.json").exists()
    for path in destination.rglob("*"):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


def adapter() -> ModuleType:
    spec = importlib.util.spec_from_file_location("world_volume_import", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("error_type", [OSError, KeyboardInterrupt])
def test_copy_failure_preserves_origin_and_never_claims_success(tmp_path, monkeypatch, error_type):
    source, destination = stage(tmp_path)
    module = adapter()
    origin = error_type("opaque-origin")

    def fail(*args):
        raise origin

    monkeypatch.setattr(module.shutil, "copyfileobj", fail)
    with pytest.raises(error_type) as caught:
        module.import_stage(
            source,
            destination,
            runtime_uid=os.getuid(),
            runtime_gid=os.getgid(),
            mysql_uid=os.getuid(),
            mysql_gid=os.getgid(),
        )
    assert caught.value is origin
    assert list(destination.iterdir())
    assert not (destination / "manifest.json").exists()


@pytest.mark.parametrize("value", ["-1", "4294967296", "opaque-uid"])
def test_invalid_owner_configuration_is_opaque_and_preflighted(tmp_path, value):
    source, destination = stage(tmp_path)
    result = invoke(source, destination, "--mysql-uid", value)
    assert result.returncode != 0
    assert not list(destination.iterdir())
    assert "opaque" not in result.stdout + result.stderr
