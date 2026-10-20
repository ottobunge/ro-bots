"""Minimal real server stack; rendering only, never starts services."""

import json
import os
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "docker-compose.native.yml"


def test_native_stack_uses_only_database_and_three_real_roles(tmp_path):
    assert TEMPLATE.is_file(), "minimal native world Compose template missing"
    source = yaml.safe_load(TEMPLATE.read_text())
    assert set(source["services"]) == {"mariadb", "rathena-login", "rathena-char", "rathena-map"}
    db = source["services"]["mariadb"]
    assert (
        "--defaults-extra-file=/var/lib/ro-bots/db/.my-healthcheck.cnf" in db["healthcheck"]["test"]
    ), "healthcheck must read credentials from relocated datadir"
    assert db["environment"]["MARIADB_ROOT_PASSWORD_FILE"] == "/var/lib/ro-bots/secrets/db-root"
    assert db["environment"]["MARIADB_PASSWORD_FILE"] == "/var/lib/ro-bots/secrets/db-user"
    assert any(
        v.get("target") == "/docker-entrypoint-initdb.d"
        and v.get("type") == "volume"
        and v.get("read_only") is True
        for v in db["volumes"]
        if isinstance(v, dict)
    )
    env = dict(os.environ)
    env.update(
        WORLD_PROJECT="ro-bots-test",
        WORLD_VOLUME="ro-bots-world-test",
        WORLD_DB_USER="fixture_user",
        WORLD_DB_NAME="ragnarok",
        RATHENA_IMAGE="rathena-playable:20180704-e985006171d2",
        MARIADB_IMAGE="mariadb:11.4",
    )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(TEMPLATE),
            "config",
            "--format",
            "json",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, "native Compose rendering failed"
    data = json.loads(result.stdout)
    assert data["name"] == "ro-bots-test"
    assert data["volumes"]["world-data"]["name"] == "ro-bots-world-test"
    assert not data["services"]["mariadb"].get("ports")
    assert any(
        v["target"] == "/var/lib/mysql" and v["type"] == "volume" and v["source"] == "world-data"
        for v in data["services"]["mariadb"]["volumes"]
    ), "image-declared data volume would be anonymous"
    for role in ("login", "char", "map"):
        service = data["services"][f"rathena-{role}"]
        assert service["entrypoint"] == [f"/libexec/rathena/{role}-server"]
        assert service["command"] == ["--runtime-root", "/world/runtime"]
