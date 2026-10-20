"""Offline CLI filesystem acceptance; never containers or SQL execution."""

import importlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from dataclasses import asdict
from types import ModuleType

import pytest

MODULE = "robots.adapters.world_prepare_cli"


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        [sys.executable, "-m", MODULE, *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )


def adapter() -> ModuleType:
    assert importlib.util.find_spec(MODULE) is not None, "world preparation CLI missing"
    return importlib.import_module(MODULE)


def test_actual_cli_prepares_private_tree_and_reusable_inputs(tmp_path):
    target = tmp_path / "fresh"
    result = cli(
        "--world",
        "test",
        "--destination",
        str(target),
        "--login-port",
        "16900",
        "--char-port",
        "16121",
        "--map-port",
        "15121",
    )
    assert result.returncode == 0, "world preparation CLI must succeed"
    summary = json.loads(result.stdout)
    assert summary["prepared"] is True
    assert summary["provisioning"] is summary["host_bind_mount_ready"] is False
    assert summary["asset_files"] == 679
    assert summary["stage"] == str(target)
    assert summary["pending"] == ["volume-import-runtime-uid-10000", "verified-mariadb-reader-uid"]
    inputs = json.loads((target / "compose-inputs.json").read_text())
    assert inputs["WORLD_KIND"] == "test"
    assert inputs["WORLD_PROJECT"] == "ro-bots-test"
    assert inputs["WORLD_VOLUME"] == "ro-bots-world-test"
    assert inputs["WORLD_DB_NAME"] == "ragnarok"
    assert inputs["WORLD_DB_USER"] == "ro_bots"
    assert inputs["WORLD_SCHEMA_DIR"] == str(target / "sql")
    for role, port in (("LOGIN", "16900"), ("CHAR", "16121"), ("MAP", "15121")):
        assert inputs[f"WORLD_{role}_PORT"] == port
    assert "AGENT_IMAGE" not in inputs
    assert inputs["WORLD_DB_ROOT_SECRET_FILE"] == str(target / "secrets/db-root")
    assert inputs["WORLD_DB_USER_SECRET_FILE"] == str(target / "secrets/db-user")
    assert sum(path.is_file() for path in target.rglob("*")) == 694
    for path in [target, *target.rglob("*")]:
        info = path.stat()
        assert info.st_uid == os.geteuid()
        assert stat.S_IMODE(info.st_mode) == (0o700 if path.is_dir() else 0o600)
    assert not result.stderr
    for filename in ("db-root", "db-user"):
        value = (target / "secrets" / filename).read_text()
        assert len(value) == 22
        assert bool(value not in result.stdout)
    assert "ro_bots" not in result.stdout


def test_private_settings_file_is_used_with_port_override(tmp_path):
    settings = adapter().generated_settings()
    source = tmp_path / "settings.json"
    source.write_text(json.dumps(asdict(settings)))
    source.chmod(0o600)
    target = tmp_path / "custom"
    result = cli(
        "--world",
        "debug",
        "--destination",
        str(target),
        "--settings-file",
        str(source),
        "--login-port",
        "16901",
    )
    assert result.returncode == 0, "private settings file must be accepted"
    assert bool((target / "secrets/db-user").read_text() == settings.db_password)
    inputs = json.loads((target / "compose-inputs.json").read_text())
    assert inputs["WORLD_LOGIN_PORT"] == "16901"
    assert bool(settings.db_password not in result.stdout + result.stderr)


def test_default_destination_two_worlds_have_fresh_distinct_credentials(
    tmp_path, monkeypatch, capsys
):
    module = adapter()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    credentials = []
    for world in ("test", "debug"):
        assert module.main(["--world", world]) == 0
        summary = json.loads(capsys.readouterr().out)
        target = tmp_path / "run/worlds" / world
        assert summary["stage"] == str(target)
        assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
        char = dict(
            line.split(": ", 1)
            for line in (target / "runtime/conf/char_athena.conf").read_text().splitlines()
            if ": " in line
        )
        values = [(target / "secrets" / name).read_text() for name in ("db-root", "db-user")]
        values.append(char["passwd"])
        assert len(set(values)) == 3
        assert all(len(value) == 22 for value in values)
        assert all(value not in repr(summary) for value in values)
        credentials.append(values)
    assert all(bool(first != second) for first, second in zip(*credentials, strict=True))


@pytest.mark.parametrize(
    "arguments",
    [
        ["--world", "TEST"],
        ["--world", "prod-bad_"],
        ["--world", "test", "--destination", "relative"],
        ["--world", "test", "--destination", "/invalid/../root"],
        ["--world", "test", "--destination", "/invalid//root"],
        ["--world", "test", "--map-port", "0"],
        ["--world", "test", "--char-port", "6900"],
    ],
)
def test_invalid_inputs_before_default_parent_creation(tmp_path, monkeypatch, capsys, arguments):
    module = adapter()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    assert module.main(arguments) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "private details withheld" in output.err
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--world", "test", "--force"],
        ["--world", "test", "--login-port", "private-not-in-output"],
        ["--world", "test", "--password", "private-not-in-output"],
    ],
)
def test_argparse_errors_are_sanitized(arguments, capsys):
    with pytest.raises(SystemExit) as caught:
        adapter().main(arguments)
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert "private-not-in-output" not in output.err


@pytest.mark.parametrize(
    "payload",
    [
        b'{"db_password":"private-canary",',
        b'{"unexpected":"private-canary"}',
        b"[]",
        b'{"db_port":true}',
        b'{"db_name":1}',
        b"{}",
        b'{"db_name":"one","db_name":"two"}',
        b"\xff",
        b" " * 32769,
    ],
)
def test_invalid_private_settings_are_sanitized_before_creation(tmp_path, payload, capsys):
    source = tmp_path / "settings.json"
    source.write_bytes(payload)
    source.chmod(0o600)
    target = tmp_path / "new"
    assert (
        adapter().main(
            ["--world", "test", "--settings-file", str(source), "--destination", str(target)]
        )
        == 2
    )
    output = capsys.readouterr()
    assert not output.out
    assert "private-canary" not in output.err
    assert not target.exists()


@pytest.mark.parametrize("kind", ["public", "readonly", "symlink", "ancestor", "directory", "fifo"])
def test_settings_files_require_private_regular_nonsymlink_path(tmp_path, kind, capsys):
    source = tmp_path / "input"
    if kind == "directory":
        source.mkdir()
    elif kind == "fifo":
        os.mkfifo(source, 0o600)
    else:
        source.write_bytes(b"{}")
        source.chmod(0o600)
        if kind in ("public", "readonly"):
            source.chmod(0o644 if kind == "public" else 0o400)
        elif kind == "symlink":
            link = tmp_path / "link"
            link.symlink_to(source)
            source = link
        else:
            link = tmp_path / "linked-dir"
            link.symlink_to(tmp_path, target_is_directory=True)
            source = link / "input"
    target = tmp_path / "new"
    assert (
        adapter().main(
            ["--world", "test", "--settings-file", str(source), "--destination", str(target)]
        )
        == 2
    )
    assert not target.exists()
    assert not capsys.readouterr().out


def test_private_json_positive_direct_main_and_native_matching_ports(tmp_path, capsys):
    module = adapter()
    settings = module.generated_settings()
    source = tmp_path / "private.json"
    source.write_text(json.dumps(asdict(settings)) + " " * 10000)
    source.chmod(0o600)
    target = tmp_path / "positive"
    assert (
        module.main(
            [
                "--world",
                "prod-example",
                "--settings-file",
                str(source),
                "--destination",
                str(target),
                "--login-port",
                "16900",
                "--char-port",
                "16121",
                "--map-port",
                "15121",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["world"] == "prod-example"
    inputs = json.loads((target / "compose-inputs.json").read_text())
    for role, filename in (("LOGIN", "login"), ("CHAR", "char"), ("MAP", "map")):
        raw = (target / f"runtime/conf/{filename}_athena.conf").read_text()
        assert f"{role.lower()}_port: {inputs[f'WORLD_{role}_PORT']}" in raw


@pytest.mark.parametrize("kind", ["empty", "sentinel", "symlink"])
def test_existing_destination_never_adopted(tmp_path, kind, capsys):
    target = tmp_path / "existing"
    if kind == "symlink":
        target.symlink_to(tmp_path / "absent")
    else:
        target.mkdir()
        if kind == "sentinel":
            (target / "sentinel").write_bytes(b"unchanged")
    assert adapter().main(["--world", "test", "--destination", str(target)]) == 2
    assert not capsys.readouterr().out
    if kind == "sentinel":
        assert (target / "sentinel").read_bytes() == b"unchanged"
    elif kind == "empty":
        assert not list(target.iterdir())
    else:
        assert target.is_symlink()


@pytest.mark.parametrize("origin", [KeyboardInterrupt(), SystemExit(7)])
def test_interrupts_preserve_original_origin(tmp_path, monkeypatch, origin):
    module = adapter()

    def fail(*args):
        raise origin

    monkeypatch.setattr(module.world_prepare, "create", fail)
    with pytest.raises(type(origin)) as caught:
        module.main(["--world", "test", "--destination", str(tmp_path / "unused")])
    assert caught.value is origin


def test_metadata_failure_has_no_success_and_partial_stage_is_private(
    tmp_path, monkeypatch, capsys
):
    module = adapter()

    def fail(*args):
        raise OSError(5, "private-canary")

    monkeypatch.setattr(module, "write_at", fail)
    target = tmp_path / "partial"
    assert module.main(["--world", "test", "--destination", str(target)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "errno=5" in output.err
    assert "private-canary" not in output.err
    assert target.is_dir()
    assert not (target / "compose-inputs.json").exists()


def test_module_help_is_safe_and_requires_no_world():
    result = cli("--help")
    assert result.returncode == 0
    assert "--settings-file" in result.stdout
    assert "--password" not in result.stdout
    assert not result.stderr
