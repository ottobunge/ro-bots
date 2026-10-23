"""Configuration + secret-file tests: creds are read from files at runtime and
never echoed into errors, reprs or logs."""

from __future__ import annotations

import logging

import pytest

from dashboard_webapp.config import AppConfig, SecretFileError, read_secret


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DASHBOARD_BIND",
        "WORLDFEED_URL",
        "RECEIPTS_GLOB",
        "AGENT_MEMORY_ROOT",
        "DB_HOST",
        "DB_ROOT_SECRET_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = AppConfig.from_env()
    assert cfg.bind == "127.0.0.1:8401"
    assert cfg.worldfeed_url == "http://127.0.0.1:8400"
    assert cfg.receipts_glob == ".work/playing-grind-emission/evidence/receipt-*.json"
    assert cfg.memory_root is None
    assert cfg.db_configured is False
    assert cfg.traces_dir == ".work/runtime/population-live/traces"
    assert cfg.host_manifest == ".work/runtime/population-live/host-manifest.json"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_BIND", "0.0.0.0:8401")
    monkeypatch.setenv("WORLDFEED_URL", "http://worldfeed:8400")
    monkeypatch.setenv("RECEIPTS_GLOB", "/data/receipts/receipt-*.json")
    monkeypatch.setenv("AGENT_MEMORY_ROOT", "/data/memory")
    monkeypatch.setenv("DB_HOST", "mariadb")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_NAME", "ragnarok")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_ROOT_SECRET_FILE", "/run/secrets/db-root")
    monkeypatch.setenv("TRACES_DIR", "/data/runtime/population-live/traces")
    monkeypatch.setenv("HOST_MANIFEST", "/data/runtime/population-live/host-manifest.json")
    cfg = AppConfig.from_env()
    assert cfg.bind == "0.0.0.0:8401"
    assert cfg.worldfeed_url == "http://worldfeed:8400"
    assert cfg.receipts_glob == "/data/receipts/receipt-*.json"
    assert cfg.memory_root == "/data/memory"
    assert cfg.db_host == "mariadb"
    assert cfg.db_port == 3307
    assert cfg.db_name == "ragnarok"
    assert cfg.db_user == "root"
    assert cfg.db_root_secret_file == "/run/secrets/db-root"
    assert cfg.db_configured is True
    assert cfg.traces_dir == "/data/runtime/population-live/traces"
    assert cfg.host_manifest == "/data/runtime/population-live/host-manifest.json"


def test_read_secret_strips_trailing_newline(tmp_path) -> None:
    secret = tmp_path / "db-root"
    secret.write_text("hunter2-not-really\n")
    assert read_secret(secret) == "hunter2-not-really"


def test_missing_secret_error_mentions_path_not_content(tmp_path) -> None:
    secret = tmp_path / "db-root"
    with pytest.raises(SecretFileError) as excinfo:
        read_secret(secret)
    message = str(excinfo.value)
    assert str(secret) in message
    # The failure is a missing file: there is no content to leak, but the
    # contract is that secret-file errors only ever name the path.
    assert "password" not in message.lower()


def test_secret_value_never_reaches_logger(tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    """Secret-file handling must not log file contents at any level."""
    secret = tmp_path / "db-root"
    secret.write_text("super-secret-value\n")
    with caplog.at_level(logging.DEBUG):
        assert read_secret(secret) == "super-secret-value"
        # Simulate the failure path too: unreadable file.
        secret.chmod(0o000)
        try:
            with pytest.raises(SecretFileError):
                read_secret(secret)
        finally:
            secret.chmod(0o600)
    assert "super-secret-value" not in caplog.text
