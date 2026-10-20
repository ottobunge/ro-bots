"""Offline scheduled-host transport contracts; never construct a real client."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from robots.app import agent_runtime
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.playing_runtime import PlayingClient
from robots.society.models import SocietyPersona


class ConstructorSpy:
    """Capture constructor arguments without transport, threads, or providers."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.result = SimpleNamespace(char_name="SyntheticCharacter")

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls.append((args, kwargs))
        return self.result


def test_direct_native_entry_forwards_constructor_options(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", spy)
    entry = ManifestEntry(
        "persona",
        "synthetic-account",
        "synthetic-password",
        "SyntheticCharacter",
        login_host="127.0.0.1",
        login_port=16900,
        pincode="0042",
    )
    agent = ScheduledAgent(cast(SocietyPersona, object()), entry, threaded=False)
    constructed = agent._new_client()
    assert isinstance(constructed, PlayingClient)
    assert constructed.wire is spy.result
    assert spy.calls == [
        (
            (entry.account, entry.password),
            {
                "char_name": entry.char_name,
                "verbose": False,
                "login_ip": "127.0.0.1",
                "login_port": 16900,
                "pincode": entry.pincode,
            },
        )
    ]
    assert agent.client is None
    assert agent.thread is None
    assert not agent.online


def write_manifest(tmp_path: Path, **options: object) -> Path:
    path = tmp_path / "synthetic-manifest.json"
    data: dict[str, object] = {
        "accounts": [
            {
                "persona_id": "persona",
                "account": "synthetic-account",
                "password": "synthetic-password",
                "pincode": "0042",
            }
        ],
        **options,
    }
    path.write_text(json.dumps(data))
    return path


def test_manifest_forwards_root_endpoint_and_row_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spy = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", spy)
    path = write_manifest(tmp_path, login_host="127.0.0.1", login_port=16900)
    entry = agent_runtime.load_manifest(path)["persona"]
    agent = ScheduledAgent(cast(SocietyPersona, object()), entry, threaded=False)
    constructed = agent._new_client()
    assert isinstance(constructed, PlayingClient)
    assert constructed.wire is spy.result
    assert spy.calls[0][1]["login_port"] == 16900
    assert spy.calls[0][1]["login_ip"] == "127.0.0.1"
    assert spy.calls[0][1]["pincode"] == "0042"


@pytest.mark.parametrize(
    "options",
    [
        {"login_host": "localhost"},
        {"login_host": "::1"},
        {"login_host": 123},
        {"login_port": True},
        {"login_port": "16900"},
        {"login_port": 0},
        {"login_port": 65536},
        {"pincode": 42},
        {"pincode": "\uff11\uff12\uff13\uff14"},
        {"pincode": "123"},
        {"pincode": "12345"},
        {"pincode": "12 4"},
    ],
)
def test_direct_entry_rejects_invalid_transport(options: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"login|pincode"):
        ManifestEntry("persona", "synthetic-account", "synthetic-password", "Character", **options)


@pytest.mark.parametrize(
    "options",
    [
        {"login_host": "127.0.0.1"},
        {"login_port": 16900},
        {"login_host": "localhost", "login_port": 16900},
        {"login_host": "127.0.0.1", "login_port": True},
        {"login_host": None, "login_port": 16900},
    ],
)
def test_manifest_rejects_endpoint_before_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    options: dict[str, object],
) -> None:
    spy = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", spy)
    path = write_manifest(tmp_path, accounts=[], **options)
    with pytest.raises(ValueError, match="login"):
        agent_runtime.load_manifest(path)
    assert not spy.calls


@pytest.mark.parametrize(
    "pin", [1234, True, "\uff11\uff12\uff13\uff14", "123", "12345", "12 4", None]
)
def test_manifest_rejects_invalid_pin_even_in_skipped_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pin: object,
) -> None:
    spy = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", spy)
    path = write_manifest(
        tmp_path,
        accounts=[
            {"persona_id": "persona", "account": "synthetic-account"},
            {"pincode": pin},
        ],
    )
    with pytest.raises(ValueError, match="pincode") as caught:
        agent_runtime.load_manifest(path)
    assert str(caught.value) == "pincode must be exactly four ASCII digits"
    assert not spy.calls


def test_legacy_entry_keeps_default_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", spy)
    entry = ManifestEntry("persona", "synthetic-account", "synthetic-password", "Character")
    agent = ScheduledAgent(cast(SocietyPersona, object()), entry, threaded=False)
    agent._new_client()
    assert spy.calls[0][1]["login_ip"] == "127.0.0.1"
    assert spy.calls[0][1]["login_port"] == 6900
    assert spy.calls[0][1]["pincode"] is None
    assert entry.password not in repr(entry)


def test_injected_factory_receives_only_original_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    real_constructor = ConstructorSpy()
    factory = ConstructorSpy()
    monkeypatch.setattr(agent_runtime, "_BotClient", real_constructor)
    entry = ManifestEntry(
        "persona",
        "synthetic-account",
        "synthetic-password",
        "Character",
        login_host="127.0.0.2",
        login_port=16900,
        pincode="0042",
    )
    agent = ScheduledAgent(
        cast(SocietyPersona, object()), entry, client_factory=factory, threaded=False
    )
    assert agent._new_client() is factory.result
    assert factory.calls == [((entry,), {})]
    assert not real_constructor.calls
    assert entry.pincode is not None
    assert entry.pincode not in repr(entry)


@pytest.mark.parametrize("port", [1, 65535])
def test_endpoint_port_boundaries(port: int) -> None:
    entry = ManifestEntry(
        "persona",
        "synthetic-account",
        "synthetic-password",
        "Character",
        login_host="192.0.2.1",
        login_port=port,
    )
    assert entry.login_port == port


def test_manifest_preserves_legacy_skip_and_first_duplicate(tmp_path: Path) -> None:
    path = write_manifest(
        tmp_path,
        accounts=[
            None,
            {"account": "missing-persona"},
            {"persona_id": "persona", "account": "first"},
            {"persona_id": "persona", "account": "second"},
        ],
    )
    entries = agent_runtime.load_manifest(path)
    assert list(entries) == ["persona"]
    assert entries["persona"].account == "first"
    assert entries["persona"].char_name == "first"
    assert entries["persona"].login_port == 6900
    assert entries["persona"].pincode is None
