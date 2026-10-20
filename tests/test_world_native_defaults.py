"""Offline regression for pinned defaults; never initialize native roles or SQL."""

import re
import stat

from robots.adapters import world_prepare
from robots.adapters.rathena_bootstrap_assets import schema_projection
from robots.adapters.rathena_runtime_assets import SOURCE, public_assets
from robots.adapters.world_compose import WorldSelection


def config() -> world_prepare.PreparationSettings:
    return world_prepare.PreparationSettings(
        db_name="fixture_world",
        db_user="fixture_db",
        db_password="d" * 32,
        inter_user="fixture_inter",
        inter_password="i" * 23,
        root_password="r" * 32,
        login_port=16900,
        char_port=16121,
        map_port=15121,
    )


def fields(raw: bytes) -> dict[str, str]:
    values = {}
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("//"):
            continue
        key, separator, value = line.partition(":")
        if separator and value.strip():
            values[key] = value.strip()
    return values


def test_native_char_sql_defaults_resolve_every_parser_table(tmp_path):
    target = tmp_path / "new"
    world_prepare.create(target, WorldSelection("test"), config())
    actual = fields((target / "runtime/conf/inter_athena.conf").read_bytes())
    expected = fields((SOURCE / "conf/inter_athena.conf").read_bytes())
    parser = (SOURCE / "src/char/char.cpp").read_text()
    parser = parser.split("void char_sql_config_read", 1)[1].split("void char_set_default_sql", 1)[
        0
    ]
    keys = set(re.findall(r'strcmpi\(w1,\s*"([^"]+)"\)', parser)) - {
        "import",
        "start_status_points",
    }
    tables = {
        table["name"]
        for path in (target / "sql").glob("*.sql")
        for table in schema_projection(path.read_bytes())[0]
    }
    assert len(tables) == 70
    assert keys
    assert all(actual.get(key) == expected[key] for key in keys), "native SQL defaults missing"
    assert all(actual[key] in tables for key in keys)
    assert actual["clan_table"] == "clan"
    assert actual["clan_alliance_table"] == "clan_alliance"


def test_role_defaults_private_overrides_and_safe_complete_closure(tmp_path):
    settings = config()
    target = tmp_path / "roles"
    assets, _ = public_assets()
    summary = world_prepare.create(target, WorldSelection("test"), settings)
    runtime = target / "runtime"
    assert summary["asset_files"] == len(assets)
    roles = {
        role: fields((runtime / f"conf/{role}_athena.conf").read_bytes())
        for role in ("login", "char", "map", "inter")
    }
    assert roles["char"]["max_connect_user"] == "-1"
    assert (
        roles["char"]["start_point_pre"]
        == fields((SOURCE / "conf/char_athena.conf").read_bytes())["start_point_pre"]
    )
    # The native char display's zero means unlimited, not zero usable slots.
    char_source = (SOURCE / "src/char/char.cpp").read_text()
    assert "char_per_account = 0; //Maximum chars per account (default unlimited)" in char_source
    assert roles["char"]["login_ip"] == "rathena-login"
    assert roles["map"]["char_ip"] == "rathena-char"
    assert roles["char"]["char_ip"] == roles["map"]["map_ip"] == "127.0.0.1"
    assert roles["login"]["login_port"] == roles["char"]["login_port"] == "16900"
    assert roles["char"]["char_port"] == roles["map"]["char_port"] == "16121"
    assert roles["map"]["map_port"] == "15121"
    assert roles["login"]["use_web_auth_token"] == "no"
    assert roles["map"]["use_grf"] == roles["inter"]["use_sql_db"] == "no"
    for role in ("char", "map"):
        assert bool(roles[role]["userid"] == settings.inter_user)
        assert bool(roles[role]["passwd"] == settings.inter_password)
    for prefix in ("login_server", "ipban_db", "char_server", "map_server", "log_db", "web_server"):
        assert roles["inter"][prefix + "_ip"] == "mariadb"
        assert bool(roles["inter"][prefix + "_id"] == settings.db_user)
        assert bool(roles["inter"][prefix + "_pw"] == settings.db_password)
    for name in ("grf-files.txt", "subnet_athena.conf"):
        assert not fields((runtime / "conf" / name).read_bytes())
    assert roles["login"]["new_account"] == "no"
    assert fields((runtime / "conf/log_athena.conf").read_bytes())["sql_logs"] == "no"
    for path in runtime.rglob("*.conf"):
        imports = [
            line.partition(b":")[2].strip().decode("ascii")
            for line in path.read_bytes().splitlines()
            if line.startswith(b"import:")
        ]
        assert len(imports) == len(set(imports))
        assert all((runtime / name).is_file() for name in imports)
        assert not any("/import/" in name for name in imports)
    for path in [target, *target.rglob("*")]:
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


def test_merge_preserves_import_order_and_last_private_values():
    defaults = b"// ignore: comment\nlimit: 3\nimport: conf/first.conf\nlimit: 4\n"
    overrides = b"limit: 8\nimport: conf/last.conf\n"
    actual = world_prepare._merge_defaults(defaults, overrides)
    assert actual == b"import: conf/first.conf\n" + overrides
    assert fields(actual)["limit"] == "8"
