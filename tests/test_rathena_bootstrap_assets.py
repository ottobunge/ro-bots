"""Offline artifact tests; never send SQL to a server."""

import hashlib
import importlib
import importlib.util
import json
import re
import socket
import subprocess
from collections import Counter
from pathlib import Path
from types import ModuleType

import pytest

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
MODULE = "robots.adapters.rathena_bootstrap_assets"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def adapter() -> ModuleType:
    assert importlib.util.find_spec(MODULE) is not None, "public bootstrap derivation is missing"
    return importlib.import_module(MODULE)


def test_unique_default_suppression_preserves_every_other_public_byte():
    assets = adapter().derive()
    original = (SOURCE / "sql-files/main.sql").read_bytes()
    expected = original[:29900] + original[30138:]
    assert digest(assets["main.sql"]) == digest(expected)
    assert b"INSERT INTO `login`" not in assets["main.sql"]
    assert assets["main.sql"].count(b"INSERT INTO `clan`") == 4
    assert assets["main.sql"].count(b"INSERT INTO `clan_alliance`") == 8
    for name in ("logs.sql", "web.sql", "roulette_default_data.sql"):
        assert digest(assets[name]) == digest((SOURCE / "sql-files" / name).read_bytes())
    assert set(assets) == {"main.sql", "logs.sql", "web.sql", "roulette_default_data.sql"}


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "cross_target", "changed_shape", "changed_ddl"]
)
def test_changed_or_ambiguous_main_is_rejected_without_reporting_statement(mutation):
    module = adapter()
    assert hasattr(module, "suppress_default"), "hash-guarded suppression proof is missing"
    raw = (SOURCE / "sql-files/main.sql").read_bytes()
    target = raw.splitlines(keepends=True)[798]
    variants = {
        "missing": raw.replace(target, b""),
        "extra": raw + target,
        "cross_target": raw.replace(b"INSERT INTO `login`", b"INSERT INTO `other`"),
        "changed_shape": raw.replace(target, b"INSERT INTO `login` VALUES (999);\n"),
        "changed_ddl": raw + b"CREATE TABLE `unexpected` (`id` int);\n",
    }
    with pytest.raises(ValueError, match="pinned public SQL file drift"):
        module.suppress_default(variants[mutation])


def test_actual_reference_artifact_manifest_readback_and_complete_source_projection(tmp_path):
    module = adapter()
    assert hasattr(module, "reference_bundle"), "provenance/schema bundle is missing"
    assets, manifest = module.reference_bundle()
    for name, raw in assets.items():
        with (tmp_path / name).open("xb") as stream:
            stream.write(raw)
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    with (tmp_path / "manifest.json").open("xb") as stream:
        stream.write(manifest_bytes)
    observed = json.loads((tmp_path / "manifest.json").read_bytes())
    assert observed == manifest
    assert manifest["source_nar"] == "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI="
    assert manifest["revision"] == "e985006171d2eb320ee512a653f4c83aea3d81b6"
    assert manifest["scope"] == "public-reference-derivation-only"
    assert manifest["sql_executed"] is False
    assert manifest["mutation_authorized"] is False
    expected_engines = {
        "main.sql": {"MyISAM": 53, "InnoDB": 3},
        "logs.sql": {"MyISAM": 10},
        "web.sql": {"MyISAM": 4},
        "roulette_default_data.sql": {},
    }
    expected_inserts = {
        "main.sql": 12,
        "logs.sql": 0,
        "web.sql": 0,
        "roulette_default_data.sql": 42,
    }
    for name in assets:
        entry = manifest["files"][name]
        assert entry["sha256"] == digest((tmp_path / name).read_bytes())
        assert entry["size"] == (tmp_path / name).stat().st_size
        source = (SOURCE / "sql-files" / name).read_bytes()
        assert entry["source_sha256"] == digest(source)
        independent = []
        for block in source.split(b"CREATE TABLE IF NOT EXISTS ")[1:]:
            table = block.split(b"`", 2)[1].decode()
            body = block.split(b";", 1)[0]
            engine_match = re.search(rb"ENGINE\s*=\s*(\w+)", body)
            assert engine_match is not None
            engine = engine_match[1].decode()
            columns = re.findall(rb"^\s+`([^`]+)`\s+", body, re.MULTILINE)
            independent.append(
                {
                    "name": table,
                    "engine": engine,
                    "columns": [column.decode() for column in columns],
                    "field_count": len(columns),
                }
            )
        assert entry["tables"] == independent
        assert entry["table_count"] == len(independent)
        assert dict(Counter(t["engine"] for t in independent)) == expected_engines[name]
        assert entry["engines"] == expected_engines[name]
        assert entry["insert_count"] == expected_inserts[name]
    login = next(t for t in manifest["files"]["main.sql"]["tables"] if t["name"] == "login")
    assert login["field_count"] == 20
    assert "online" not in login["columns"]
    assert manifest["suppression"]["source_byte_span"] == [29900, 30138]
    assert manifest["suppression"]["statement_count"] == 1
    assert manifest["suppression"]["adjacent_comment_lines"] == [796, 797]


@pytest.mark.parametrize("failure", ["drift", "exit", "timeout", "missing_nix"])
def test_attestation_refuses_before_any_sql_asset_read(monkeypatch, failure):
    module = adapter()
    seen = []

    def runner(args, **kwargs):
        seen.append((args, kwargs))
        if failure == "timeout":
            command = "fixed-public-attestation"
            raise subprocess.TimeoutExpired(command, 60)
        if failure == "missing_nix":
            message = "synthetic tool unavailable"
            raise OSError(message)
        return subprocess.CompletedProcess(args, int(failure == "exit"), b"drift", b"unused")

    def forbidden_read(*args, **kwargs):
        pytest.fail("source SQL read happened before failed attestation")

    monkeypatch.setattr(module.subprocess, "run", runner)
    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    with pytest.raises(ValueError, match="pinned public source attestation failed"):
        module.reference_bundle()
    assert seen == [
        (
            ["nix", "hash", "path", "--sri", str(SOURCE)],
            {"check": False, "capture_output": True, "timeout": 60},
        )
    ]


def test_real_derivation_has_only_fixed_nix_child_no_network_or_sql_process(monkeypatch):
    module = adapter()
    real_popen = subprocess.Popen
    seen = []

    def allow_fixed_nix(args, **kwargs):
        assert args == ["nix", "hash", "path", "--sri", str(SOURCE)]
        assert kwargs.get("shell", False) is False
        seen.append(args)
        return real_popen(args, **kwargs)

    def forbidden_network(*args, **kwargs):
        pytest.fail("network operation attempted during public derivation")

    monkeypatch.setattr(subprocess, "Popen", allow_fixed_nix)
    monkeypatch.setattr(socket, "socket", forbidden_network)
    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    assets, manifest = module.reference_bundle()
    assert len(assets) == 4
    assert manifest["sql_executed"] is False
    assert len(seen) == 1
