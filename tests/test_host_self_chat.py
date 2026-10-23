"""Offline host chat identity contracts; synthetic inputs, not native receipt."""

from types import SimpleNamespace
from typing import cast

import pytest

from robots.app.agent_runtime import ScheduledAgent
from robots.domain.events import ChatHeard
from robots.domain.model import ChatLine


def test_account_id_self_chat_is_suppressed() -> None:
    client = SimpleNamespace(aid=11, gid=21, chat=[(11, "synthetic self")], actors={})
    host = SimpleNamespace(client=client, _chat_seen=0, _party_chat_seen=0)

    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()
    assert host._chat_seen == 1
    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()
    assert host._chat_seen == 1


def test_peer_delivery_preserves_name_event_channel_and_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("robots.app.agent_runtime.time.time", lambda: 123.5)
    client = SimpleNamespace(
        aid=11, gid=21, chat=[(31, "synthetic peer")], actors={31: {"name": "Peer"}}
    )
    host = SimpleNamespace(client=client, _chat_seen=0, _party_chat_seen=0)

    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == (
        ChatHeard(line=ChatLine(channel="public", sender="Peer", text="synthetic peer", at=123.5)),
    )
    assert host._chat_seen == 1
    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()


def test_interleaved_self_peer_and_broadcast_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("robots.app.agent_runtime.time.time", lambda: 123.5)
    chat: list[tuple[int, str]] = []
    client = SimpleNamespace(aid=11, gid=21, chat=chat, actors={31: {"name": "Peer"}})
    host = SimpleNamespace(client=client, _chat_seen=0, _party_chat_seen=0)
    inputs = [(11, "self account"), (31, "peer"), (21, "legacy echo"), (0, "broadcast")]
    for cursor, (sender, text) in enumerate(inputs, start=1):
        chat.append((sender, text))
        events = ScheduledAgent._drain_events(cast(ScheduledAgent, host))
        if sender in (11, 21):
            assert events == ()
        else:
            name = "Peer" if sender == 31 else "0"
            assert events == (
                ChatHeard(line=ChatLine(channel="public", sender=name, text=text, at=123.5)),
            )
        assert host._chat_seen == cursor
        assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()
        assert host._chat_seen == cursor

    chat.extend(inputs)
    events = ScheduledAgent._drain_events(cast(ScheduledAgent, host))
    assert tuple(event.line.text for event in events if isinstance(event, ChatHeard)) == (
        "peer",
        "broadcast",
    )
    assert host._chat_seen == len(chat)
    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()


@pytest.mark.parametrize(
    ("identity", "sender", "suppressed"),
    [
        ({"gid": 21}, 21, True),
        ({"gid": 21}, 11, False),
        ({"aid": 11}, 11, True),
        ({"aid": 11}, 21, False),
        ({}, 0, False),
        ({}, 31, False),
        ({"aid": None, "gid": None}, 0, False),
        ({"aid": 0, "gid": 21}, 0, True),
    ],
)
def test_missing_identity_attributes_keep_existing_policy(
    identity: dict[str, int | None], sender: int, suppressed: bool
) -> None:
    client = SimpleNamespace(**identity, chat=[(sender, "synthetic")], actors={})
    host = SimpleNamespace(client=client, _chat_seen=0, _party_chat_seen=0)

    events = ScheduledAgent._drain_events(cast(ScheduledAgent, host))
    assert len(events) == (0 if suppressed else 1)
    if events:
        assert isinstance(events[0], ChatHeard)
        assert events[0].line.sender == str(sender)
    assert host._chat_seen == 1
    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()


def test_absent_client_is_noop() -> None:
    host = SimpleNamespace(client=None, _chat_seen=0, _party_chat_seen=0)
    assert ScheduledAgent._drain_events(cast(ScheduledAgent, host)) == ()
    assert host._chat_seen == 0
