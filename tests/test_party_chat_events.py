"""The party-chat ChatHeard producer: the reply loop must HEAR party lines.

The premade buff-ask loop needs the brain to receive party chat as ChatHeard
events; before this, only the public 0x008D deque produced them and party
messages were visible in the decide state but never triggered a reaction.
"""

from __future__ import annotations

from collections import deque
from typing import Any, ClassVar

from robots.app.agent_runtime import ScheduledAgent
from robots.domain.events import ChatHeard


def _agent_with(client: Any) -> ScheduledAgent:
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client = client
    agent._chat_seen = 0
    agent._party_chat_seen = 0
    agent.heartbeat_seq = 0
    agent.timers = None
    return agent


def test_party_chat_lines_produce_chat_heard_events() -> None:
    class _Client:
        aid = 2200001
        gid = 300001
        chat: ClassVar[deque] = deque()
        party_chat: ClassVar[deque] = deque([(2200000, "NyxSong", "anyone need buffs?")])
        actors: ClassVar[dict] = {}

    events = _agent_with(_Client())._drain_events()
    party = [e.line for e in events if isinstance(e, ChatHeard) and e.line.channel == "party"]
    assert len(party) == 1
    assert party[0].sender == "NyxSong"
    assert party[0].text == "anyone need buffs?"


def test_public_chat_still_produces_events() -> None:
    class _Client:
        aid = 2200001
        gid = 300001
        chat: ClassVar[deque] = deque([(2200002, "hello world")])
        party_chat: ClassVar[deque] = deque()
        actors: ClassVar[dict] = {2200002: {"name": "zeny_wing"}}

    events = _agent_with(_Client())._drain_events()
    heard = [e for e in events if isinstance(e, ChatHeard)]
    assert len(heard) == 1
    assert heard[0].line.channel == "public"
    assert heard[0].line.sender == "zeny_wing"


def test_own_party_lines_are_skipped() -> None:
    class _Client:
        aid = 2200001
        gid = 300001
        chat: ClassVar[deque] = deque()
        party_chat: ClassVar[deque] = deque([(2200001, "RinceNyan", "my own line")])
        actors: ClassVar[dict] = {}

    events = _agent_with(_Client())._drain_events()
    assert events == ()
