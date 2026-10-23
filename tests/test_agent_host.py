"""AgentHost / ScheduledAgent: schedule-driven lifecycle + real state feeds.

No live server: the game client is a FakeGameClient double implementing the
same surface the spike-003 BotClient exposes (connect/close/move/say/sit +
world-model attrs), and the schedule/clock are injected so windows can be
forced open and closed.
"""

from __future__ import annotations

import json
import random
from typing import Any

import pytest

from robots.__main__ import build_host, parse_args
from robots.app.agent_runtime import (
    AgentHost,
    ManifestEntry,
    PersonaClock,
    ScheduledAgent,
    load_manifest,
)
from robots.app.brain import EventDrivenBrain
from robots.app.world_state import WorldState
from robots.domain.actions import MoveTo, Rest, Say
from robots.domain.model import Goal
from robots.society.models import FriendGroup, Schedule
from robots.society.society import SocietyRoster

# --------------------------------------------------------------------- doubles


class FakeClock:
    """TickClock with a manual monotonic clock (deterministic timers)."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


class FakeSocietyClock:
    """SocietyClock pinned to a (weekday, hour) the test moves by hand."""

    def __init__(self, now: tuple[int, float] = (0, 10.0)) -> None:
        self.now = now

    def local_now(self) -> tuple[int, float]:
        return self.now


class FakeGameClient:
    """BotClient-equivalent double: same limb surface + world model."""

    def __init__(self, entry: ManifestEntry) -> None:
        self.entry = entry
        self.char_name = entry.char_name
        self.status_params: dict[int, int] = {5: 1, 6: 1, 7: 1, 8: 1}
        self.gid = 150000
        self.connected = False
        self.x = 120
        self.y = 74
        self.sitting = False
        self.map_name = "prontera"
        self.actors: dict[int, dict] = {9001: {"name": "Trader", "x": 118, "y": 75}}
        self.chat: list[tuple[int, str]] = []
        self.party_id = 0
        self.party_invite_pid = 0
        self.party_invite_from = ""
        self.moves: list[tuple[int, int]] = []
        self.said: list[str] = []
        self.sits = 0

    def connect(self) -> FakeGameClient:
        self.connected = True
        return self

    def close(self) -> None:
        self.connected = False

    def move(self, x: int, y: int) -> None:
        self.moves.append((x, y))
        self.x, self.y = x, y

    def say(self, text: str) -> None:
        self.said.append(text)

    def sit(self) -> None:
        self.sits += 1
        self.sitting = True

    def stand(self) -> None:
        self.sitting = False

    def party_reply(self, party_id: int, accept: bool = True) -> None:
        if accept:
            self.party_id = party_id

    def party_invite(self, name: str) -> None:
        pass


class ScriptedDecisionModel:
    """The same canned-answer shape the e2e stub uses."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self._answers = answers
        self.calls = 0

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {"answers": dict(self._answers)}


# ------------------------------------------------------------------ fixtures

STUB_ANSWERS: dict[str, Any] = {
    "next_action": {"choice": "travel", "confidence": 0.9},
    "target_choice": {"choice": "closest"},
    "should_reply": {"noul": True},
    "hp_critical": {"noul": False},
    "threat_near": {"noul": False},
    "accept_invite": {"noul": True},
    "use_premade": {"noul": True},
    "premade_pick": {"choice": "greet"},
    "chat_urgency": {"score": 2.0},
    "change_goal": {"choice": "keep"},
    "goal_review": {"score": 1.0},
    "farm_duration": {"score": 1.0},
    "farm_target": {"choice": "Poring"},
    "react_monster": {"choice": "ignore"},
    "react_damage": {"choice": "rest"},
}


def make_roster() -> SocietyRoster:
    """The seed-42 / 3-groups roster: deterministic personas + schedules."""
    return SocietyRoster.build(random.Random(42), n_groups=3)


def make_entry(persona_id: str) -> ManifestEntry:
    return ManifestEntry(persona_id, f"e2e_{persona_id.replace('-', '')}", "pw", persona_id)


def make_agent(
    persona_id: str = "Doramir-01",
    roster: SocietyRoster | None = None,
    world_state: WorldState | None = None,
    chat: list[tuple[int, str]] | None = None,
) -> tuple[ScheduledAgent, FakeGameClient, FakeClock]:
    rng = random.Random(7)
    roster = roster or make_roster()
    client = FakeGameClient(make_entry(persona_id))
    clock = FakeClock()
    if chat is not None:
        client.chat = chat
    agent = ScheduledAgent(
        roster.personas[persona_id],
        make_entry(persona_id),
        brain=EventDrivenBrain(
            ScriptedDecisionModel(dict(STUB_ANSWERS)),
            _StaticChat(),
        ),
        client=client,
        tick_clock=clock,
        world_state=world_state,
        heartbeat_min_s=2.0,
        heartbeat_max_s=3.0,
        rng=rng,
        threaded=False,
    )
    return agent, client, clock


class _StaticChat:
    def generate_chat(self, prompt: str, *, system: str = "") -> str:
        return "hello there"


def write_manifest(tmp_path: Any) -> str:
    data = {
        "accounts": [
            {
                "persona_id": pid,
                "account": f"e2e_{pid.replace('-', '')}",
                "password": "pw",
                "char_name": pid,
            }
            for pid in sorted(make_roster().personas)
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return str(path)


# -------------------------------------------------------------------- tests


def test_manifest_loading_maps_personas_to_accounts(tmp_path: Any) -> None:
    path = write_manifest(tmp_path)
    entries = load_manifest(path)
    assert set(entries) == set(make_roster().personas)
    entry = entries["Doramir-01"]
    assert entry.account == "e2e_Doramir01"
    assert entry.char_name == "Doramir-01"
    assert entry.password == "pw"


def test_manifest_loading_skips_malformed_rows(tmp_path: Any) -> None:
    data = {
        "accounts": [
            {"account": "no_persona", "password": "x"},
            {"persona_id": "A", "account": "acct_a", "char_name": "A"},
            {"persona_id": "A", "account": "dupe", "char_name": "dupe"},
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    entries = load_manifest(path)
    assert set(entries) == {"A"}
    assert entries["A"].account == "acct_a"


def test_manifest_empty_raises(tmp_path: Any) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"accounts": []}))
    with pytest.raises(ValueError, match="maps no personas"):
        load_manifest(path)


def test_agent_connects_when_window_opens_and_publishes_online() -> None:
    roster = make_roster()
    ws = WorldState(roster)
    agent, client, _clock = make_agent(world_state=ws)
    assert agent.online is False

    connected = agent.connect()
    assert connected is True
    assert client.connected is True
    assert client.said, "brain.start heartbeat should emit the premade greet"

    state = ws.agent_state(agent.persona.persona_id)
    assert state is not None
    assert state.online is True
    assert state.current_script != ""


def test_agent_disconnect_closes_session_with_memory_note() -> None:
    roster = make_roster()
    ws = WorldState(roster)
    agent, client, _clock = make_agent(world_state=ws)
    agent.connect()
    agent.tick()
    ticks = agent._session_ticks

    agent.disconnect()

    assert not agent.online
    assert not client.connected
    assert agent.online is False
    notes = agent.memory.log.notes()
    assert any(n.kind == "session" for n in notes), "ADR-004: sessions are memories"
    session = [n for n in notes if n.kind == "session"][-1]
    assert str(ticks) in session.text
    state = ws.agent_state(agent.persona.persona_id)
    assert state is not None
    assert state.online is False
    # disconnect is idempotent
    agent.disconnect()
    assert len([n for n in agent.memory.log.notes() if n.kind == "session"]) == 1


def test_chat_event_flows_to_brain_and_produces_say_back() -> None:
    chat = [(9001, "hi Doramir-01, need a party?")]
    agent, client, _clock = make_agent(chat=chat)
    agent.connect()
    before = len(client.said)

    agent.tick()

    assert agent.brain is not None
    assert isinstance(agent.brain, EventDrivenBrain)
    assert agent.brain.decision_count >= 1, "ChatHeard must reach the decision model"
    assert len(client.said) > before, "brain should push a Say back through the limb"
    # the heard line was consumed (not re-delivered on the next tick)
    agent.tick()
    count_after_first = agent.brain.decision_count
    agent.tick()
    assert agent.brain.decision_count == count_after_first


def test_tick_maps_world_and_executes_script_actions() -> None:
    agent, client, clock = make_agent()
    agent.connect()  # brain.start heartbeat: goal review (grind -> farm plan)
    assert agent.brain is not None
    assert isinstance(agent.brain, EventDrivenBrain)
    # Drive a goal review to 'town': IdleTownScript then walks one step/tick.
    model = agent.brain._model
    assert model is not None
    model._answers["change_goal"] = {"choice": "town"}  # type: ignore[attr-defined]
    clock.now += 10.0  # heartbeat due -> review picks idle_town
    agent.tick()
    agent.goal = Goal.IDLE_TOWN

    agent.tick()

    assert client.moves, "idle-town script should emit MoveTo through the limb"
    assert agent.tick_count == 2


def test_heartbeat_fires_via_injected_timers() -> None:
    agent, _client, clock = make_agent()
    agent.connect()
    assert agent.timers is not None
    # jump past the random heartbeat window (2-3s in this fixture)
    clock.now += 10.0
    assert isinstance(agent.brain, EventDrivenBrain)
    decision_before = agent.brain.decision_count if agent.brain else 0

    agent.tick()

    assert agent.heartbeat_seq == 1, "TimerFired(idle_review) must become a Heartbeat"
    assert agent.brain is not None
    assert agent.brain.decision_count == decision_before + 1


def test_own_chat_echo_is_not_reacted_to() -> None:
    agent, client, _clock = make_agent()
    agent.connect()
    client.gid = 150000
    client.chat = [(150000, "my own line")]
    assert isinstance(agent.brain, EventDrivenBrain)
    decision_before = agent.brain.decision_count if agent.brain else 0

    agent.tick()

    assert agent.brain is not None
    assert agent.brain.decision_count == decision_before


def test_say_action_reaches_client_and_memory() -> None:
    agent, client, _clock = make_agent()
    agent.connect()

    agent.execute_actions((Say("hello world"),))

    assert "hello world" in client.said
    notes = agent.memory.log.notes()
    assert any(n.kind == "chat" and "hello world" in n.text for n in notes)


def test_rest_action_sits() -> None:
    agent, client, _clock = make_agent()
    agent.connect()

    agent.execute_actions((Rest(),))

    assert client.sits == 1
    assert client.sitting is True


def test_move_action_through_limb() -> None:
    agent, client, _clock = make_agent()
    agent.connect()

    agent.execute_actions((MoveTo(x=130, y=80),))

    assert client.moves == [(130, 80)]


def test_run_loop_ticks_until_stop_flag() -> None:
    agent, _client, _clock = make_agent()
    agent.connect()
    agent.stop_flag = True
    agent._run_loop()  # must return immediately, not spin forever
    assert agent.online


def test_host_step_connects_and_disconnects_by_schedule(tmp_path: Any) -> None:
    roster = make_roster()
    ws = WorldState(roster)
    manifest = write_manifest(tmp_path)
    created: list[FakeGameClient] = []

    def factory(entry: ManifestEntry) -> FakeGameClient:
        client = FakeGameClient(entry)
        created.append(client)
        return client

    # Force one friend group permanently online; everyone else off.
    group = next(g for g in roster.groups if len(g.member_ids) >= 2)
    all_day: list[tuple[int, float, float]] = [(day, 0.0, 24.0) for day in range(7)]
    always = Schedule(all_day)
    never = Schedule(((0, 1.0, 1.5),))
    groups = [
        FriendGroup(
            g.group_id,
            g.member_ids,
            g.attitude,
            always if g is group else never,
        )
        for g in roster.groups
    ]
    forced = SocietyRoster(groups, roster.personas, roster.graph, roster.reputation)
    clock = FakeSocietyClock((0, 10.0))
    host = AgentHost(
        forced,
        manifest,
        client_factory=factory,
        clock=clock,
        world_state=ws,
        run_worldfeed=False,
    )
    assert set(host.agents) == set(forced.personas)

    # window open -> agent connects, WorldState shows online + character
    host.step()
    online_ids = {pid for pid, a in host.agents.items() if a.online}
    assert online_ids == set(group.member_ids)
    for pid in online_ids:
        agent = host.agents[pid]
        assert agent.client is not None
        assert agent.client.connected
        state = ws.agent_state(pid)
        assert state is not None
        assert state.online is True
        assert state.current_goal != ""

    # window closes -> graceful disconnect + session memory note
    clock.now = (0, 23.0)
    host.roster = SocietyRoster(
        [FriendGroup(g.group_id, g.member_ids, g.attitude, never) for g in groups],
        host.roster.personas,
        host.roster.graph,
        host.roster.reputation,
    )
    host.step()
    assert all(not a.online for a in host.agents.values())
    for pid in online_ids:
        notes = host.agents[pid].memory.log.notes()
        assert any(n.kind == "session" for n in notes)
        state = ws.agent_state(pid)
        assert state is not None
        assert state.online is False


def test_host_max_agents_via_cli_builder(tmp_path: Any) -> None:
    manifest = write_manifest(tmp_path)
    args = parse_args(["--manifest", manifest, "--tick-seconds", "1", "--max-agents", "2"])
    host = build_host(args)
    assert len(host.agents) == 2
    assert args.tick_seconds == 1.0
    assert args.clef_url is None


def test_persona_clock_is_society_clock() -> None:
    clock = PersonaClock()
    weekday, hour = clock.local_now()
    assert 0 <= weekday <= 6
    assert 0.0 <= hour < 24.0


def test_worldfeed_defaults_to_a_live_state(tmp_path: Any) -> None:
    roster = make_roster()
    manifest = write_manifest(tmp_path)
    host = AgentHost(
        roster,
        manifest,
        client_factory=FakeGameClient,
        world_state=None,
        run_worldfeed=False,
    )
    # ADR-010: the host owns a real WorldState unless one is injected.
    assert host.world_state is not None
    assert set(host.world_state.roster.personas) == set(roster.personas)
    host.start_worldfeed()  # disabled via run_worldfeed=False: must be a no-op
    host.stop()
    assert all(not a.online for a in host.agents.values())
