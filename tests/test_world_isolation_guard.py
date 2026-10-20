"""Unsafe shared-world E2E/seeding must fail before any side effect."""

import importlib.util
from pathlib import Path

import pytest


def load_script(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["e2e_runner", "seed_test_agents"])
def test_unverified_world_cli_cannot_reach_subprocess_or_manifest(name, monkeypatch, capsys):
    script = load_script(name)

    def forbidden(*_args, **_kwargs):
        pytest.fail("unverified world touched a process, database, or manifest", pytrace=False)

    monkeypatch.setattr(script.subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr("sys.argv", [name])
    assert script.main() != 0
    assert "blocked" in capsys.readouterr().err.lower()


def test_unverified_direct_sql_application_is_blocked(monkeypatch):
    script = load_script("seed_test_agents")

    def forbidden(*_args, **_kwargs):
        pytest.fail("unverified seed touched a database subprocess", pytrace=False)

    monkeypatch.setattr(script.subprocess, "run", forbidden)
    with pytest.raises(RuntimeError, match="blocked"):
        script.apply_sql("SELECT 1;", None)
