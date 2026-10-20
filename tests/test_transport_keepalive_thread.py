"""Reader/transport stability: keepalive must not ride host cognition (RED).

Window 14 (run/reviews/playing-grind-operator-live-window14.json, fixture_1):
the rx thread did not exit from a swallowed exception - it recorded
``rx_error: "EOF from map-server"`` and died. The server side closes client
sessions it has received no data from for ``stall_time`` seconds (pinned
rAthena src/common/socket.cpp:1016 "Session #N timed out" -> set_eof; the
deployed world pins ``stall_time: 60`` in packet_athena.conf:22). The only
client-side countermeasure is the CZ_REQUEST_TIME keepalive pumped from
``PlayingClient._keepalive`` (KEEPALIVE_INTERVAL_S = 20), which rides
``drain_native_events`` -> ``agent.tick`` -> successful ``build_state``:
window 14 sent only FOUR keepalives in ~500 s while the pacer recorded
build_state failures from step 144 onward, and the source comment at
playing_runtime.py:1171 already concedes ">60s blocked ticks".

The fix: an independent daemon pump thread in PlayingClient that shares the
same guarded schedule (same lock, same interval, same poison flag) and sends
even when ticks starve. It starts only after the first successful strict
post-readiness pump (the existing contract is unchanged), stops on close,
and failures poison health fail-closed exactly like the tick path.
"""

import time as _time
from typing import Any

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from tests.test_native_playing_keepalive import KeepaliveWire


def _client(now: list[float], interval: float) -> tuple[KeepaliveWire, PlayingClient]:
    wire = KeepaliveWire(now)
    client = PlayingClient(wire, monotonic=lambda: now[0], keepalive_interval_s=interval)
    client.connect()
    return wire, client


def test_thread_pumps_keepalive_while_the_tick_clock_is_frozen() -> None:
    now = [100.0]
    wire, client = _client(now, interval=0.05)
    client._keepalive()  # the same guarded pump the strict-ready tick path calls
    assert wire.keepalives == []  # first pump only schedules (existing contract)
    assert client._keepalive_at == 100.0
    assert client._keepalive_thread is not None  # started after the successful pump
    _time.sleep(0.4)  # real wall time advances; the fake host clock does not
    thread_sends = len(wire.keepalives)
    assert thread_sends >= 2, "background pump must send without any tick"
    client.close()
    after_close = len(wire.keepalives)
    _time.sleep(0.2)
    assert len(wire.keepalives) == after_close
    assert client._keepalive_thread is None


def test_thread_is_started_only_after_a_successful_pump() -> None:
    now = [0.0]
    wire, client = _client(now, interval=0.05)
    assert client._keepalive_thread is None
    _time.sleep(0.1)
    assert wire.keepalives == []  # no sends before strict readiness


def test_thread_send_failure_poisons_health_fail_closed() -> None:
    now = [5.0]
    wire, client = _client(now, interval=0.05)
    client._keepalive()  # first successful pump starts the daemon pump thread
    assert client._keepalive_thread is not None

    def broken() -> None:
        msg = "wire gone"
        raise OSError(msg)

    wire.keepalive = broken  # type: ignore[method-assign]

    # The flag flips on the daemon thread, so poll it via an Any-typed alias:
    # a direct member read would let mypy narrow it (whole-source gate), and
    # getattr with a constant name trips ruff B009.
    pump_state: Any = client
    deadline = _time.monotonic() + 2.0
    failed_seen = False
    while _time.monotonic() < deadline:
        if pump_state._keepalive_failed:
            failed_seen = True
            break
        _time.sleep(0.02)
    assert failed_seen
    assert pump_state._keepalive_thread is None  # stopped, no spin
    with pytest.raises(NativeTelemetryUnavailable, match="keepalive send failed"):
        client._health()


def test_close_joins_a_waiting_thread_without_sends_after_close() -> None:
    now = [7.0]
    _wire, client = _client(now, interval=0.05)
    client._keepalive()
    pump_thread = client._keepalive_thread
    assert pump_thread is not None
    client.close()
    assert client._keepalive_thread is None
    # assert on THIS client's pump thread only: other suites may legitimately
    # keep their own daemon pumps waiting (no process-wide scan).
    assert not pump_thread.is_alive()
    assert now == [7.0]  # the fake clock never advanced: no tick-side pump ran
