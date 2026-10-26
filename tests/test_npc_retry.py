"""The NPC retry cadence: the barrier holds, but the runtime schedules the
fresh begin so the bot never freezes for whole windows (leg 23: 598 ticks)."""

from __future__ import annotations

from robots.adapters.native_npc_dialogue import NativeNpcDialogue
from robots.app.playing_runtime import PlayingClient


class _RecordingWire:
    char_name = "probe"
    native_epoch = 1

    def __init__(self) -> None:
        self.sent: list[bytes] = []

    def _send(self, frame: bytes) -> None:
        self.sent.append(frame)


def _runtime(now: list[float], budget: int = 3) -> PlayingClient:
    client = PlayingClient.__new__(PlayingClient)
    client.wire = _RecordingWire()
    client._npc = NativeNpcDialogue()
    client._metadata_cursor = 50
    client._now = lambda: now[0]
    client._npc_retries = budget
    client._npc_retry_at = 0.0
    return client


def _deny(client: PlayingClient) -> None:
    client._npc.begin(110001762, 1, "prontera", 10, 100.0)
    client._npc._expire(200.0)


def test_retry_re_begins_the_denied_dialogue() -> None:
    now = [300.0]
    client = _runtime(now)
    _deny(client)
    assert client._retry_blocked_dialogue()
    assert client.wire.sent, "the fresh click must go out"
    assert not client._npc.failed


def test_retry_re_fires_on_each_new_deny_within_budget() -> None:
    now = [300.0]
    client = _runtime(now)
    _deny(client)
    assert client._retry_blocked_dialogue()
    first = len(client.wire.sent)
    # the fresh begin cleared the failed flag; the normal flow proceeds until
    # the new dialogue denies again - then the retry fires within the budget
    client._npc._expire(now[0] + 10.0)
    now[0] = 311.0
    assert client._retry_blocked_dialogue()
    assert len(client.wire.sent) > first
    assert client._npc_retries == 1


def test_retry_budget_caps_the_attempts() -> None:
    now = [300.0]
    client = _runtime(now, budget=0)
    _deny(client)
    # the barrier holds with the spent budget: the caller returns, no send
    assert client._retry_blocked_dialogue()
    assert client.wire.sent == []
