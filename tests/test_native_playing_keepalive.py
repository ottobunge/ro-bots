"""Synthetic offline lifecycle contracts, not native-session observations."""

from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, Rest
from robots.domain.model import Goal
from robots.society.models import Attitude, Playstyle, SocietyPersona
from tests.test_playing_runtime import Wire, walk_ack


class KeepaliveWire(Wire):
    def __init__(self, now: list[float]) -> None:
        super().__init__()
        self.now = now
        self.keepalives: list[float] = []

    def keepalive(self) -> None:
        self.keepalives.append(self.now[0])

    def close(self, *args: Any, **kwargs: Any) -> None:
        self.running = self.connected_map = False

    def connect(self, *args: Any, **kwargs: Any) -> None:
        self.running = self.connected_map = True
        self.native_epoch += 1
        self.selection_epoch = self.map_epoch = self.native_epoch


def test_idle_host_ticks_keep_transport_alive_across_server_stall_window() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    wire.frames = wire.frames[:2]  # No observed monster: a genuinely idle host tick.
    client = PlayingClient(wire, monotonic=lambda: now[0])
    persona = SocietyPersona("idle", "idle", Playstyle.MELEE, Attitude.GRINDER, 0.5, (1, 10))
    agent = ScheduledAgent(
        persona,
        ManifestEntry("idle", "unused", "unused", wire.char_name),
        client=client,
        threaded=False,
    )
    agent.brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    for second in range(91):
        now[0] = float(second)
        agent.tick()
    assert wire.keepalives == [20.0, 40.0, 60.0, 80.0]
    assert wire.moves == []
    assert wire.sent == []


def test_epoch_change_and_close_reconnect_restart_pacing() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 19.0
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    client.drain_native_events()
    now[0] = 20.0
    client.drain_native_events()
    assert wire.keepalives == []
    now[0] = 39.0
    client.drain_native_events()
    assert wire.keepalives == [39.0]
    client.close()
    now[0] = 100.0
    client.connect()
    client.drain_native_events()
    assert wire.keepalives == [39.0]
    now[0] = 120.0
    client.drain_native_events()
    assert wire.keepalives == [39.0, 120.0]
    client.close()
    now[0] = 140.0
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == [39.0, 120.0]


@pytest.mark.parametrize("clock", [float("nan"), float("inf"), -1.0])
def test_invalid_or_reversed_clock_cannot_send(clock: float) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = clock
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == []


def test_unknown_reader_liveness_cannot_send() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 20.0
    wire.rx_thread = SimpleNamespace(is_alive=object)
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == []


def test_failed_send_propagates_exact_origin_without_automatic_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    origin = ConnectionError("synthetic send failed")
    attempts: list[float] = []

    def fail() -> None:
        attempts.append(now[0])
        raise origin

    monkeypatch.setattr(wire, "keepalive", fail)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 20.0
    with pytest.raises(ConnectionError) as caught:
        client.drain_native_events()
    assert caught.value is origin
    now[0] = 40.0
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert attempts == [20.0]


@pytest.mark.parametrize("flag", ["running", "connected_map", "class_fresh"])
def test_unhealthy_due_tick_never_sends(flag: str) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 20.0
    setattr(wire, flag, False)
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == []


def test_pre_auth_does_not_send() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    wire.frames = []
    client = PlayingClient(wire, monotonic=lambda: now[0])
    for second in (0.0, 20.0, 80.0):
        now[0] = second
        with pytest.raises(NativeTelemetryUnavailable):
            client.drain_native_events()
    assert wire.keepalives == []


def test_movement_rest_and_repeated_getters_do_not_change_pacing() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.drain_native_events()
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]
    now[0] = 20.0
    for _ in range(10):
        client.build_native_state(Goal.GRIND)
    assert wire.keepalives == []  # Public state projection remains read-only.
    client.drain_native_events()
    client.drain_native_events()
    wire.add(walk_ack((43, 37), (43, 37)))
    client.perform_native(MoveTo(44, 37))
    assert wire.moves[-1] == (44, 37)
    client.perform_native(Rest())
    now[0] = 40.0
    client.drain_native_events()
    now[0] = 200.0
    client.drain_native_events()  # One send, not a missed-interval burst.
    assert wire.keepalives == [20.0, 40.0, 200.0]
    assert "sit" in wire.sent


@pytest.mark.parametrize("reader_alive", [False, None])
def test_stopped_or_unknown_reader_never_sends(reader_alive: bool | None) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 20.0
    wire.rx_thread = SimpleNamespace(is_alive=lambda: reader_alive)
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == []


def test_frame_gap_never_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()
    now[0] = 20.0
    monkeypatch.setattr(wire, "native_frame_snapshot", lambda: (1, 10, ()))
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.keepalives == []


def test_clients_have_independent_transport_timers() -> None:
    now = [0.0]
    first_wire, second_wire = KeepaliveWire(now), KeepaliveWire(now)
    first = PlayingClient(first_wire, monotonic=lambda: now[0])
    second = PlayingClient(second_wire, monotonic=lambda: now[0])
    first.drain_native_events()
    now[0] = 10.0
    second.drain_native_events()
    now[0] = 20.0
    first.drain_native_events()
    second.drain_native_events()
    assert first_wire.keepalives == [20.0]
    assert second_wire.keepalives == []
    now[0] = 30.0
    second.drain_native_events()
    assert second_wire.keepalives == [30.0]


def test_moving_session_ticks_across_server_stall_window() -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    cache = MapCache((WalkMap("prontera", 200, 100, bytes(20000)),))
    client = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    for second in range(91):
        now[0] = float(second)
        wire.add(walk_ack((42 + second, 37), (42 + second, 37)))
        client.drain_native_events()
        client.perform_native(MoveTo(43 + second, 37))
    assert len(wire.moves) == 91
    assert wire.keepalives == [20.0, 40.0, 60.0, 80.0]


def test_failed_close_does_not_clear_failed_send_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.drain_native_events()

    def fail() -> None:
        message = "synthetic failure"
        raise ConnectionError(message)

    monkeypatch.setattr(wire, "keepalive", fail)
    now[0] = 20.0
    with pytest.raises(ConnectionError):
        client.drain_native_events()
    monkeypatch.setattr(wire, "close", fail)
    with pytest.raises(ConnectionError):
        client.close()
    with pytest.raises(NativeTelemetryUnavailable):
        client.build_native_state(Goal.GRIND)
