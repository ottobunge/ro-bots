"""Pinned DB artifacts, inspected offline; never invokes any DB tool or engine."""

import json
import os
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("RO_BOTS_ROOT", Path(__file__).resolve().parents[1]))


def artifact(target: str) -> Path:
    flake = ROOT / "nix/db-image/flake.nix"
    assert flake.is_file(), "isolated pinned database flake is missing"
    result = subprocess.run(
        [
            "nix",
            "build",
            "--no-write-lock-file",
            "--no-link",
            "--print-out-paths",
            f"path:{ROOT / 'nix/db-image'}#{target}^out",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert result.returncode == 0, "pinned database artifact cannot build"
    return Path(result.stdout.strip())


def test_package_uses_root_pin_and_contains_actual_db_software():
    package = artifact("rathena-db")
    root_lock = json.loads((ROOT / "flake.lock").read_text())
    db_lock = json.loads((ROOT / "nix/db-image/flake.lock").read_text())
    assert db_lock == root_lock
    for name in ("mariadbd", "mariadb"):
        binary = package / "bin" / name
        assert binary.read_bytes()[:4] == b"\x7fELF"
        assert os.access(binary, os.X_OK)
    assert (package / "bin/mariadb-install-db").is_file()
    assert not (package / "var/lib/mysql").exists()


def test_docker_archive_is_nonroot_offline_software_not_a_provisioned_world():
    package = artifact("rathena-db")
    image = artifact("rathena-db-image")
    with tarfile.open(image) as archive:
        manifest_stream = archive.extractfile("manifest.json")
        assert manifest_stream is not None
        manifest = json.load(manifest_stream)
        assert len(manifest) == 1
        config_stream = archive.extractfile(manifest[0]["Config"])
        assert config_stream is not None
        config = json.load(config_stream)
        expected_created = datetime.fromisoformat("1970-01-01T00:00:01Z")
        assert datetime.fromisoformat(config["created"]) == expected_created
        settings = config["config"]
        assert settings["User"] == "10001:10001"
        assert settings["Entrypoint"] == [str(package / "bin/mariadbd")]
        assert settings["Cmd"] == ["--no-defaults", "--version"]
        assert settings["WorkingDir"] == "/"
        assert not settings.get("ExposedPorts")
        assert not settings.get("Volumes")
        assert not settings.get("Healthcheck")
        labels = settings["Labels"]
        pin = json.loads((ROOT / "flake.lock").read_text())["nodes"]["nixpkgs"]["locked"]
        assert labels["org.ro-bots.nixpkgs.revision"] == pin["rev"]
        assert labels["org.ro-bots.nixpkgs.nar-hash"] == pin["narHash"]
        assert labels["org.opencontainers.image.version"] == package.name.split("server-")[1]
        assert labels["org.opencontainers.image.revision"] == pin["rev"]
        assert (
            datetime.fromisoformat(labels["org.opencontainers.image.created"]) == expected_created
        )
        assert labels["org.ro-bots.image.format"] == "docker-archive"
        assert not any(
            token in value.upper()
            for value in settings.get("Env", [])
            for token in ("PASSWORD", "SECRET", "MYSQL_HOME", "MARIADB_HOME")
        )


def test_archive_layers_contain_public_native_closure_without_world_state():
    package = artifact("rathena-db")
    image = artifact("rathena-db-image")
    with tarfile.open(image) as archive:
        manifest_stream = archive.extractfile("manifest.json")
        assert manifest_stream is not None
        manifest = json.load(manifest_stream)
        files = {}
        for name in manifest[0]["Layers"]:
            layer_stream = archive.extractfile(name)
            assert layer_stream is not None
            with tarfile.open(fileobj=layer_stream) as layer:
                for member in layer:
                    path = member.name.removeprefix("./").strip("/")
                    assert not path.startswith(("home/otto", "var/lib/mysql", "run/", "models/"))
                    assert not member.isdev()
                    assert not member.isfifo()
                    assert Path(path).name not in ("my.cnf", ".my.cnf", ".mylogin.cnf")
                    assert not path.endswith((".pid", ".sock", ".ibd", ".MYD", ".MYI"))
                    content = None
                    if member.isfile() and path.endswith(("/etc/passwd", "/etc/group")):
                        stream = layer.extractfile(member)
                        assert stream is not None
                        content = stream.read()
                    files[path] = (member.isfile(), member.linkname, content)
        for name, expected in (("passwd", b"db:x:10001:10001:"), ("group", b"db:x:10001:")):
            entry = files[f"etc/{name}"]
            target = entry if entry[0] else files[entry[1].lstrip("/")]
            assert target[2] is not None
            assert expected in target[2]
        for name in ("mariadbd", "mariadb", "mariadb-install-db", "my_print_defaults"):
            assert files[str(package / "bin" / name).lstrip("/")][0]
        closure = subprocess.run(
            ["nix-store", "--query", "--requisites", str(package)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        assert all(path.lstrip("/") in files for path in closure.stdout.splitlines())
