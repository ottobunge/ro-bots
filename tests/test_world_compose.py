"""Simple world naming and command routing, not live lifecycle acceptance."""

import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml


def test_world_selection_derives_disjoint_names_without_yaml_stanzas():
    module = importlib.import_module("robots.adapters.world_compose")
    selections = [module.WorldSelection(name) for name in ("debug", "test", "prod", "prod-blue")]
    assert [item.world for item in selections] == ["debug", "test", "prod-default", "prod-blue"]
    assert [item.project for item in selections] == [f"ro-bots-{item.world}" for item in selections]
    assert [item.volume for item in selections] == [
        f"ro-bots-world-{item.world}" for item in selections
    ]
    assert len({item.project for item in selections}) == 4
    assert len({item.volume for item in selections}) == 4


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Prod-blue",
        "prod-",
        "prod-a_b",
        "test;id",
        "../test",
        " test",
        "prod-a\n",
        1,
        None,
        True,
    ],
)
def test_world_selection_rejects_raw_invalid_names(name):
    module = importlib.import_module("robots.adapters.world_compose")
    with pytest.raises(ValueError, match="world"):
        module.WorldSelection(name)


REPO = Path(__file__).resolve().parents[1]


def test_compose_template_uses_one_world_volume_for_persistent_paths():
    template = yaml.safe_load((REPO / "docker-compose.worlds.yml").read_text())
    assert template["name"] == "${WORLD_PROJECT:?derived world project required}"
    assert template["volumes"] == {
        "world-data": {"name": "${WORLD_VOLUME:?derived world volume required}"}
    }
    assert "networks" not in template
    services = template["services"]
    assert "--datadir=/var/lib/ro-bots/db" in services["mariadb"]["command"]
    assert not services["mariadb"].get("ports")
    for role in ("rathena-login", "rathena-char", "rathena-map", "agent", "worldfeed"):
        assert "world-data:/world" in services[role]["volumes"]
        assert "build" not in services[role]
    assert services["rathena-login"]["working_dir"] == "/world/runtime"
    assert services["worldfeed"]["image"] == "${WORLDFEED_IMAGE:?real WorldFeed image required}"
    assert "entrypoint" not in services["worldfeed"]  # supplied real image, never demo/stub module


@pytest.mark.parametrize(
    ("operation", "tail"),
    [
        ("config", ["config", "--format", "json"]),
        ("up", ["up", "-d", "--no-build", "--pull", "never"]),
        ("down", ["down"]),
        ("status", ["ps", "--format", "json"]),
    ],
)
def test_lifecycle_command_arrays_scope_exact_selected_project(operation, tail):
    module = importlib.import_module("robots.adapters.world_compose")
    selection = module.WorldSelection("prod-blue")
    commands = module.commands(selection, operation)
    assert commands == [
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(REPO / "docker-compose.worlds.yml"),
            "-p",
            "ro-bots-prod-blue",
            *tail,
        ]
    ]


def test_wipe_test_stops_only_test_project_then_deletes_exact_volume():
    module = importlib.import_module("robots.adapters.world_compose")
    selection = module.WorldSelection("test")
    commands = module.commands(selection, "wipe-test")
    assert commands[0][-1] == "down"
    assert "-v" not in commands[0]
    assert commands[1] == ["docker", "volume", "rm", "ro-bots-world-test"]
    for name in ("debug", "prod", "prod-blue"):
        with pytest.raises(ValueError, match="test"):
            module.commands(module.WorldSelection(name), "wipe-test")
    with pytest.raises(ValueError, match="operation"):
        module.commands(selection, "evil")


@pytest.fixture
def world_env(tmp_path):
    env = dict.fromkeys(
        ("RATHENA_IMAGE", "AGENT_IMAGE", "WORLDFEED_IMAGE", "DASHBOARD_IMAGE"), "example/real:fixed"
    )
    env["PATH"] = os.environ["PATH"]
    env["HOME"] = os.environ["HOME"]
    env["WORLD_DB_USER"] = "world_owned"
    schema = tmp_path / "schema"
    schema.mkdir()
    (schema / "schema.sql").write_text("-- synthetic public schema, config validation only\n")
    env["WORLD_SCHEMA_DIR"] = str(schema)
    for key in ("WORLD_DB_ROOT_SECRET_FILE", "WORLD_DB_USER_SECRET_FILE"):
        file = tmp_path / key
        file.write_text("synthetic-config-test-only")
        file.chmod(0o600)
        env[key] = str(file)
    return env


def test_preflight_selects_names_without_mutating_input(world_env):
    module = importlib.import_module("robots.adapters.world_compose")
    world_env.update(WORLD_PROJECT="evil", WORLD_VOLUME="shared", COMPOSE_PROFILES="evil")
    original = world_env.copy()
    env = module.environment(module.WorldSelection("prod-blue"), world_env)
    assert env["WORLD_PROJECT"] == "ro-bots-prod-blue"
    assert env["WORLD_VOLUME"] == "ro-bots-world-prod-blue"
    assert "COMPOSE_PROFILES" not in env
    assert world_env == original


@pytest.mark.parametrize(
    "value", ["-1", "0", "65536", "6900;id", " 6900", "\uff16\uff19\uff10\uff10", 6900, True]
)
def test_invalid_ports_refused_before_runner(world_env, value):
    module = importlib.import_module("robots.adapters.world_compose")
    world_env["WORLD_LOGIN_PORT"] = value
    with pytest.raises(ValueError, match="WORLD_LOGIN_PORT"):
        module.environment(module.WorldSelection("test"), world_env)


@pytest.mark.parametrize(
    "key",
    [
        "RATHENA_IMAGE",
        "WORLD_DB_USER",
        "WORLD_DB_ROOT_SECRET_FILE",
        "WORLD_DB_USER_SECRET_FILE",
        "WORLD_SCHEMA_DIR",
    ],
)
def test_missing_inputs_never_default_to_authentication(world_env, key):
    module = importlib.import_module("robots.adapters.world_compose")
    del world_env[key]
    with pytest.raises(ValueError, match=key):
        module.environment(module.WorldSelection(), world_env)


def test_nonprivate_secret_file_is_refused(world_env):
    module = importlib.import_module("robots.adapters.world_compose")
    Path(world_env["WORLD_DB_ROOT_SECRET_FILE"]).chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        module.environment(module.WorldSelection(), world_env)


def test_real_compose_config_is_readonly_and_world_specific(world_env):
    module = importlib.import_module("robots.adapters.world_compose")
    for name in ("debug", "test", "prod-blue", "prod-green"):
        selection = module.WorldSelection(name)
        result = module.dispatch(selection, "config", world_env)
        assert result["project"] == selection.project
        assert result["volumes"] == {"world-data": selection.volume}
        assert result["networks"] == {"default": f"{selection.project}_default"}
        for role in ("rathena-login", "rathena-char", "rathena-map", "agent", "worldfeed"):
            assert {"type": "volume", "source": "world-data", "target": "/world"} in result[
                "mounts"
            ][role]
        assert {"type": "volume", "source": "world-data", "target": "/var/lib/ro-bots"} in result[
            "mounts"
        ]["mariadb"]
        assert "synthetic-config-test-only" not in json.dumps(result)
        assert "environment" not in json.dumps(result)


@pytest.mark.parametrize("operation", ["up", "down", "status", "wipe-test"])
def test_dispatch_uses_runner_seam_not_live_lifecycle(world_env, operation):
    module = importlib.import_module("robots.adapters.world_compose")
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    selection = module.WorldSelection("test")
    module.dispatch(selection, operation, world_env, runner=runner)
    assert [args for args, _ in calls] == module.commands(selection, operation)
    assert all(kwargs["capture_output"] and kwargs["timeout"] == 60 for _, kwargs in calls)
    assert all(kwargs["env"]["WORLD_VOLUME"] == "ro-bots-world-test" for _, kwargs in calls)


def test_down_failure_never_reaches_volume_deletion(world_env):
    module = importlib.import_module("robots.adapters.world_compose")
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, stdout="private-output", stderr="private-error")

    with pytest.raises(RuntimeError, match="exit 1") as error:
        module.dispatch(module.WorldSelection("test"), "wipe-test", world_env, runner=runner)
    assert len(calls) == 1
    assert "private" not in str(error.value)


def test_config_sanitizes_secret_bearing_provider_output(world_env):
    module = importlib.import_module("robots.adapters.world_compose")

    def runner(args, **kwargs):
        payload = {
            "name": "ro-bots-test",
            "volumes": {"world-data": {"name": "ro-bots-world-test"}},
            "services": {"mariadb": {"environment": {"PASSWORD": "never-print"}, "volumes": []}},
            "secrets": {"secret": {"file": "private-path"}},
        }
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps(payload), stderr="never-print"
        )

    safe = module.dispatch(module.WorldSelection("test"), "config", world_env, runner=runner)
    assert "never-print" not in json.dumps(safe)
    assert "private-path" not in json.dumps(safe)


@pytest.mark.parametrize(
    "args",
    [
        ["up"],
        ["down"],
        ["wipe-test"],
        ["up", "--world", "test;id"],
        ["wipe-test", "--world", "prod-blue"],
    ],
)
def test_cli_rejects_unsafe_selection_before_runner(world_env, args, capsys):
    module = importlib.import_module("robots.adapters.world_compose")

    def runner(*args, **kwargs):
        pytest.fail("invalid CLI reached execution")

    assert module.main(args, inputs=world_env, runner=runner) == 2
    assert "private" not in capsys.readouterr().out


def test_cli_plan_is_validated_json_without_execution(world_env, capsys):
    module = importlib.import_module("robots.adapters.world_compose")

    def runner(*args, **kwargs):
        pytest.fail("plan reached execution")

    assert module.main(["up", "--world", "test", "--plan"], inputs=world_env, runner=runner) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan == module.commands(module.WorldSelection("test"), "up")


def test_cli_config_defaults_debug_and_emits_only_safe_fields(world_env, capsys):
    module = importlib.import_module("robots.adapters.world_compose")
    assert module.main(["config"], inputs=world_env) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["project"] == "ro-bots-debug"
    assert "environment" not in output


def test_cli_failure_output_is_withheld(world_env, capsys):
    module = importlib.import_module("robots.adapters.world_compose")

    def runner(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 7, stdout="sensitive-stdout", stderr="sensitive-stderr"
        )

    assert module.main(["up", "--world", "test"], inputs=world_env, runner=runner) == 2
    output = capsys.readouterr()
    assert "exit 7" in output.err
    assert "sensitive" not in output.err + output.out


def test_selected_database_name_and_prepared_sql_mount(world_env):
    module = importlib.import_module("robots.adapters.world_compose")
    assert module.environment(module.WorldSelection(), world_env)["WORLD_DB_NAME"] == "ragnarok"
    world_env["WORLD_DB_NAME"] = "private_world_db"
    env = module.environment(module.WorldSelection("test"), world_env)
    result = subprocess.run(
        module.commands(module.WorldSelection("test"), "config")[0],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    config = json.loads(result.stdout)
    assert config["services"]["mariadb"]["environment"]["MARIADB_DATABASE"] == "private_world_db"
    assert any(
        mount["target"] == "/docker-entrypoint-initdb.d" and mount["read_only"]
        for mount in config["services"]["mariadb"]["volumes"]
    )
