"""Synthetic real-host startup ownership regressions; no native I/O."""

import argparse
import json
import traceback
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from robots import playing
from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.agent_runtime import AgentHost, ManifestEntry
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import script_for
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire


class OwnedWire(Wire):
    def __init__(self, cleanup_error: BaseException | None = None) -> None:
        super().__init__()
        self.connects = 0
        self.closed = 0
        self.cleanup_error = cleanup_error

    def connect(self):
        self.connects += 1

    def close(self):
        self.closed += 1
        if self.cleanup_error is not None:
            raise self.cleanup_error
        self.running = self.connected_map = False
        self.sock = None


class InterruptedModel:
    def __init__(self, origin: BaseException) -> None:
        self.origin = origin

    def decide(self, request: Any) -> NoReturn:
        raise self.origin


def host_for(tmp_path: Path, wire: OwnedWire, origin: BaseException) -> AgentHost:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "persona_id": "one",
                        "account": "synthetic",
                        "password": "synthetic",
                        "char_name": wire.char_name,
                    }
                ]
            }
        )
    )
    entries = {"one": ManifestEntry("one", "synthetic", "synthetic", wire.char_name)}
    args = argparse.Namespace(seed=0, solo=True, playground=True, duration=120, schedule_file=None)
    host = AgentHost(
        playing.build_roster(entries, args),
        path,
        run_worldfeed=False,
        decision_factory=lambda: InterruptedModel(origin),
        chat_generator=StaticChatGenerator(),
        client_factory=lambda _: PlayingClient(wire),
    )
    host.agents["one"]._threaded = False
    return host


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_initial_inference_control_releases_owned_client(tmp_path, error_type):
    origin = error_type("initial inference cancelled")
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    with pytest.raises(error_type) as caught:
        playing.run_host(host, 0.01)
    assert caught.value is origin
    assert traceback.extract_tb(origin.__traceback__)[-1].name == "decide"
    assert wire.connects == wire.closed == 1
    assert wire.sock is None
    assert not host.agents["one"]._client_cleanup_pending
    host.stop()
    assert wire.closed == 1


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, RuntimeError])
@pytest.mark.parametrize("cleanup_type", [OSError, SystemExit])
def test_failed_startup_close_preserves_origin_without_unsafe_retry(
    tmp_path, error_type, cleanup_type
):
    origin = error_type("initial inference cancelled")
    wire = OwnedWire(cleanup_type("private cleanup detail"))
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    if isinstance(origin, Exception):
        assert agent.connect() is False
    else:
        with pytest.raises(error_type) as caught:
            playing.run_host(host, 0.01)
        assert caught.value is origin
        assert traceback.extract_tb(origin.__traceback__)[-1].name == "decide"
    assert wire.closed == 1
    assert agent._client_cleanup_pending
    assert not agent.online
    host.stop()
    assert wire.closed == 1
    assert agent.connect() is False
    assert wire.connects == 1


def test_invalid_goal_still_raises_assertion():
    state = PlayingClient(Wire()).build_native_state(Goal.GRIND)
    with pytest.raises(AssertionError):
        script_for(cast(Goal, "invalid"), state)
