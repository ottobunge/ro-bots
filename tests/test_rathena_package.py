"""Offline packaging contract; never starts a server or an engine.

The artifact assertion is intentional: build the tracked root flake first.
"""

import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"


def package_path() -> Path:
    configured = os.environ.get("RATHENA_PACKAGE")
    if configured:
        path = Path(configured)
    else:
        result = subprocess.run(
            ["nix", "build", ".#rathena-server", "--no-link", "--print-out-paths"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        assert result.returncode == 0, "pinned rAthena package artifact is missing or cannot build"
        path = Path(result.stdout.strip())
    assert path.is_dir(), "pinned rAthena package artifact is missing"
    return path


def test_pinned_package_contains_three_native_servers():
    package = package_path()
    metadata = json.loads((package / "share/rathena/package.json").read_text())
    assert metadata["revision"] == REVISION
    assert metadata["packetver"] == 20180704
    assert metadata["client_family"] == "MAIN"
    assert metadata["ruleset"] == "pre-re"
    for role in ("login", "char", "map"):
        binary = package / "libexec/rathena" / f"{role}-server"
        assert binary.read_bytes()[:4] == b"\x7fELF"
        assert os.access(binary, os.X_OK)
    assert (package / "share/rathena/db/pre-re/item_db.yml").is_file()
    assert not (package / "share/rathena/db/re").exists()
    assert not (package / "share/rathena/sql-files").exists()


def test_native_help_and_version_exit_before_sql_initialization(tmp_path):
    package = package_path()
    evidence = (package / "share/rathena/build-evidence/core-start.cpp").read_text()
    assert evidence.index("rathena_package_offline_cli") < evidence.index("Sql_Init();")
    for role in ("login", "char", "map"):
        binary = package / "libexec/rathena" / f"{role}-server"
        for option in ("--help", "--version"):
            result = subprocess.run(
                [str(binary), option],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert result.returncode == 0
            assert "SQL" not in result.stderr
            assert "rAthena" in result.stdout
        refused = subprocess.run(
            [str(binary)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert refused.returncode == 78
        assert "launch executor is blocked" in refused.stderr
    assert list(tmp_path.iterdir()) == []


def test_compiled_profile_is_proved_by_native_preprocessor():
    package = package_path()
    proof = json.loads((package / "share/rathena/build-evidence/profile.json").read_text())
    assert proof == {
        "packetver": 20180704,
        "main": 20180704,
        "renewal": False,
        "re": False,
        "zero": False,
        "obfuscation": False,
        "pincode": True,
    }
    flags = (package / "share/rathena/build-evidence/map-cppflags.txt").read_text()
    assert "-DPACKETVER=20180704" in flags
    assert "-DPRERE" in flags


def invoke_package(*args: str) -> subprocess.CompletedProcess[str]:
    package = package_path()
    entry = package / "bin/rathena-package"
    assert entry.is_file(), "offline private-config validator is missing"
    return subprocess.run(
        [str(entry), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_launch_requires_explicit_private_secret_file():
    result = invoke_package("launch", "map")
    assert result.returncode == 2
    assert "explicit private secret file is required" in result.stderr


def secret_payload() -> dict[str, str | int]:
    return {
        "server_mode": "MAIN-pre-re-20180704",
        "db_host": "isolated-db",
        "db_port": 3306,
        "db_name": "owned_world",
        "db_user": "owned_user",
        "db_password": "Synthetic_Test_Only_17",
        "inter_user": "owned_inter",
        "inter_password": "Synthetic_Test_Only_29",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"server_mode": "RE"},
        {"db_host": "localhost"},
        {"db_host": "127.0.0.1"},
        {"db_password": 'bad"quote'},
        {"db_password": "bad\ncontrol"},
        {"db_password": "bad:directive"},
        {"db_password": "bad//comment"},
        {"db_port": True},
        {"db_port": 0},
        {"extra": "unsupported"},
    ],
)
def test_secret_validator_rejects_unsafe_fields_without_disclosure(tmp_path, change):
    data = secret_payload() | change
    secret = tmp_path / "private.json"
    secret.write_text(json.dumps(data))
    secret.chmod(0o600)
    result = invoke_package("validate", "--secret-file", str(secret))
    assert result.returncode == 2
    assert "private configuration rejected" in result.stderr
    assert "Synthetic_Test_Only" not in result.stdout + result.stderr
    assert str(change) not in result.stdout + result.stderr


def test_valid_configuration_is_not_launch_authority(tmp_path):
    secret = tmp_path / "private.json"
    secret.write_text(json.dumps(secret_payload()))
    secret.chmod(0o600)
    validated = invoke_package("validate", "--secret-file", str(secret))
    assert validated.returncode == 0
    assert "does not authorize launch" in validated.stdout
    refused = invoke_package("launch", "map", "--secret-file", str(secret))
    assert refused.returncode == 78
    assert "launch executor is blocked" in refused.stderr
    assert "Synthetic_Test_Only" not in refused.stdout + refused.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == ["private.json"]


def test_secret_file_permissions_and_symlinks_are_rejected(tmp_path):
    secret = tmp_path / "private.json"
    secret.write_text(json.dumps(secret_payload()))
    secret.chmod(0o644)
    assert invoke_package("validate", "--secret-file", str(secret)).returncode == 2
    secret.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.symlink_to(secret)
    assert invoke_package("validate", "--secret-file", str(alias)).returncode == 2


def test_asset_manifest_excludes_runtime_and_credential_configs():
    package = package_path()
    manifest = json.loads((package / "share/rathena/asset-manifest.json").read_text())
    actual = sorted(
        str(p.relative_to(package / "share/rathena"))
        for p in (package / "share/rathena").rglob("*")
        if p.is_file()
        and str(p.relative_to(package / "share/rathena")).startswith(("db/", "conf/"))
    )
    assert manifest == actual
    assert any(p.startswith("conf/battle/") for p in actual)
    assert not any(p.split("/")[1] in ("import", "import-tmpl", "re") for p in actual)
    assert not any(p.endswith((".log", ".pid", ".sql", ".jsonl")) for p in actual)
    assert not any(
        p.endswith(
            ("login_athena.conf", "inter_athena.conf", "char_athena.conf", "map_athena.conf")
        )
        for p in actual
    )


def test_nix_image_defaults_to_offline_help_and_contains_native_closure():
    result = subprocess.run(
        ["nix", "build", ".#rathena-image", "--no-link", "--print-out-paths"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, "Nix-built offline image artifact is missing"
    image = Path(result.stdout.strip())
    with tarfile.open(image) as archive:
        manifest_file = archive.extractfile("manifest.json")
        assert manifest_file is not None
        manifest = json.load(manifest_file)
        config_file = archive.extractfile(manifest[0]["Config"])
        assert config_file is not None
        config = json.load(config_file)["config"]
        assert config["Cmd"] == ["--help"]
        assert config["Entrypoint"] == [str(package_path() / "bin/rathena-package")]
        assert config["User"] == "10001:10001"
        assert not config.get("ExposedPorts")
        assert not config.get("Volumes")
        assert config["Labels"]["org.opencontainers.image.revision"] == REVISION
        assert not any(
            "PASSWORD=" in value or "SECRET=" in value for value in config.get("Env", [])
        )
        native_binaries = set()
        for layer_name in manifest[0]["Layers"]:
            layer_file = archive.extractfile(layer_name)
            assert layer_file is not None
            with tarfile.open(fileobj=layer_file) as layer:
                for member in layer:
                    assert not member.name.startswith(("home/otto", "models/", "mysql-data/"))
                    if member.isfile() and "/libexec/rathena/" in member.name:
                        native_binaries.add(Path(member.name).name)
        assert native_binaries == {"login-server", "char-server", "map-server"}
