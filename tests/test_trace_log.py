"""Full-trace JSONL logging: chats, decides, LLM calls, events, actions, state.

One append-only JSONL file per persona under --trace-dir; every line is
self-contained (map + position + payload) so a later process can reconstruct
"what happened to this agent" or feed a summarizer. Fails open: logging must
never crash the agent.
"""

from __future__ import annotations

import json
import os
import random
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from robots import playing
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.agent_runtime import IDLE_REVIEW_S, AgentHost, ManifestEntry, ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.app.trace_log import (
    STATE_TICK_INTERVAL_S,
    TracedChatGenerator,
    TracedDecisionModel,
    TraceLog,
)
from robots.domain.actions import MoveTo, PartyChat, Say, WhisperTo
from robots.domain.events import (
    DamageTaken,
    Heartbeat,
    MonsterSpotted,
)
from robots.domain.farm import MobInfo
from robots.domain.model import ActorRef
from robots.society.society import SocietyRoster

# --------------------------------------------------------------------- doubles


class FakeClock:
    """TickClock with a manual monotonic clock (deterministic cadence)."""

    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


class FakeGameClient:
    """BotClient-equivalent double + a settable cached state view."""

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
        self.last_built_state: Any = None

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


class BoomModel:
    """A decision model that always raises (wrapper transparency probe)."""

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        msg = "backend exploded"
        raise RuntimeError(msg)


class BoomChat:
    """A chat generator that always raises."""

    def generate_chat(self, prompt: str) -> str:
        msg = "chat backend exploded"
        raise RuntimeError(msg)


class RecordingChat:
    """Chat generator that records its prompt and returns a fixed reply."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_chat(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "hello there"


class FakeMobDB:
    def __init__(self, mobs: dict[str, MobInfo]) -> None:
        self._mobs = mobs

    def mobs_on_map(self, map_name: str) -> tuple[MobInfo, ...]:
        return tuple(sorted(self._mobs.values(), key=lambda m: m.level))

    def by_name(self, name: str) -> MobInfo | None:
        return self._mobs.get(name)


# -------------------------------------------------------------------- helpers

LOW_CONFIDENCE_ANSWERS: dict[str, Any] = {
    "next_action": {"type": "choice", "choice": "travel", "confidence": 0.3},
    "target_choice": {"type": "choice", "choice": "closest", "confidence": 0.9},
    "should_reply": {"type": "noul", "noul": 0.0},
    "hp_critical": {"type": "noul", "noul": 0.0},
    "threat_near": {"type": "noul", "noul": 0.0},
    "accept_invite": {"type": "noul", "noul": 0.0},
    "use_premade": {"type": "noul", "noul": 0.0},
    "premade_pick": {"type": "choice", "choice": "none", "confidence": 0.9},
    "chat_urgency": {"type": "score", "score": 0.0},
    "goal_review": {"type": "score", "score": 1.0},
    "change_goal": {"type": "choice", "choice": "keep", "confidence": 0.9},
    "farm_duration": {"type": "score", "score": 1.0},
    "farm_target": {"type": "choice", "choice": "Poring", "confidence": 0.9},
    "react_monster": {"type": "choice", "choice": "ignore", "confidence": 0.9},
    "react_damage": {"type": "choice", "choice": "keep", "confidence": 0.9},
}


def make_roster() -> SocietyRoster:
    """The seed-42 / 3-groups roster: deterministic personas + schedules."""
    return SocietyRoster.build(random.Random(42), n_groups=3)


def make_entry(persona_id: str) -> ManifestEntry:
    return ManifestEntry(persona_id, f"e2e_{persona_id.replace('-', '')}", "pw", persona_id)


def write_host_manifest(tmp_path: Path, roster: SocietyRoster) -> str:
    data = {
        "accounts": [
            {
                "persona_id": pid,
                "account": f"e2e_{pid.replace('-', '')}",
                "password": "pw",
                "char_name": pid,
            }
            for pid in sorted(roster.personas)
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return str(path)


def make_agent(
    trace: TraceLog | None,
    tmp_path: Path,
    *,
    answers: dict[str, Any] | None = None,
    chat: Any | None = None,
) -> tuple[ScheduledAgent, FakeGameClient, FakeClock]:
    """A scheduled agent wired for offline ticks, with or without a trace."""
    roster = make_roster()
    persona_id = "Doramir-01"
    client = FakeGameClient(make_entry(persona_id))
    clock = FakeClock()
    model: Any = ScriptedDecisionModel(answers=dict(answers or LOW_CONFIDENCE_ANSWERS))
    chat_gen: Any = chat if chat is not None else StaticChatGenerator(["gg"])
    if trace is not None:  # mirror the host's transparent-proxy wiring
        model = TracedDecisionModel(model, trace)
        chat_gen = TracedChatGenerator(chat_gen, trace)
    brain = EventDrivenBrain(model, chat_gen, trace=trace)
    agent = ScheduledAgent(
        roster.personas[persona_id],
        make_entry(persona_id),
        brain=brain,
        client=client,
        tick_clock=clock,
        heartbeat_min_s=2.0,
        heartbeat_max_s=3.0,
        rng=random.Random(7),
        threaded=False,
        trace=trace,
    )
    return agent, client, clock


def read_lines(trace_dir: Path, persona_id: str) -> list[dict[str, Any]]:
    path = trace_dir / f"{persona_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def kinds(lines: list[dict[str, Any]]) -> list[str]:
    return [line["kind"] for line in lines]


def test_trace_log_writes_jsonl_lines_with_context(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path / "traces", "Doramir-01")
    trace.log("chat_heard", speaker="Trader", message="hi", channel="public")
    trace.log("chat_sent", channel="party", message="hello")
    trace.close()
    lines = read_lines(tmp_path / "traces", "Doramir-01")
    assert kinds(lines) == ["chat_heard", "chat_sent"], "append order is replay order"
    heard = lines[0]
    assert heard["persona"] == "Doramir-01"
    assert heard["speaker"] == "Trader"
    assert heard["message"] == "hi"
    assert heard["channel"] == "public"
    assert isinstance(heard["t"], str), "wall-clock ISO timestamp"
    assert "T" in heard["t"]
    assert lines[1]["channel"] == "party"


def test_trace_log_files_are_owner_private(tmp_path: Path) -> None:
    root = tmp_path / "traces"
    trace = TraceLog(root, "Doramir-01")
    trace.log("state_tick")
    trace.close()
    assert stat.S_IMODE(root.stat().st_mode) & 0o077 == 0, "trace dir owner-only"
    info = (root / "Doramir-01.jsonl").stat()
    assert stat.S_IMODE(info.st_mode) & 0o077 == 0, "trace file owner-only"


def test_trace_log_fails_open_after_close(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    trace.close()
    trace.log("chat_sent", channel="public", message="lost")
    assert trace.dropped == 1, "post-close writes are counted, never raised"
    trace.close()  # double close is safe


def test_trace_log_swallows_unserializable_payloads(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    trace.log("world_event", payload=object())
    trace.close()
    lines = read_lines(tmp_path, "p")
    assert len(lines) == 1, "non-serializable values degrade, never raise"


def test_trace_log_constructor_is_strict_on_blocked_root(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")
    with pytest.raises(NotADirectoryError):
        TraceLog(blocker / "traces", "p")


def test_traced_decision_model_is_transparent(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    inner = ScriptedDecisionModel(answers={"change_goal": {"choice": "keep"}})
    model = TracedDecisionModel(inner, trace)
    request = {"state": {"map": "prontera"}, "questions": {}}
    response = model.decide(request)
    trace.close()
    assert response["answers"]["change_goal"]["choice"] == "keep"
    lines = read_lines(tmp_path, "p")
    assert kinds(lines) == ["decide_request", "decide_response"], "request precedes response"
    assert lines[0]["request"] == request, "the exact request dict is captured"
    assert lines[1]["answers"]["change_goal"]["choice"] == "keep"
    assert isinstance(lines[1]["duration_s"], float)
    assert lines[1]["duration_s"] >= 0.0


def test_traced_decision_model_logs_errors_and_reraises(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    model = TracedDecisionModel(BoomModel(), trace)
    with pytest.raises(RuntimeError, match="backend exploded"):
        model.decide({"state": {}})
    trace.close()
    lines = read_lines(tmp_path, "p")
    assert kinds(lines) == ["decide_request", "decide_response"]
    assert "error" in lines[1], "the failure is part of the agent's history"
    assert lines[1]["duration_s"] >= 0.0


def test_traced_chat_generator_logs_request_and_response(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    chat = RecordingChat()
    gen = TracedChatGenerator(chat, trace)
    reply = gen.generate_chat("A player named Trader said: hi")
    trace.close()
    assert reply == "hello there"
    assert chat.prompts == ["A player named Trader said: hi"], "prompt passes through"
    lines = read_lines(tmp_path, "p")
    assert kinds(lines) == ["llm_request", "llm_response"]
    messages = lines[0]["messages"]
    assert messages[0]["role"] == "user"
    assert "Trader" in messages[0]["content"]
    assert lines[1]["reply"] == "hello there"
    assert isinstance(lines[1]["duration_s"], float)
    assert lines[1]["duration_s"] >= 0.0


def test_traced_chat_generator_logs_errors_and_reraises(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    gen = TracedChatGenerator(BoomChat(), trace)
    with pytest.raises(RuntimeError, match="chat backend exploded"):
        gen.generate_chat("prompt")
    trace.close()
    lines = read_lines(tmp_path, "p")
    assert kinds(lines) == ["llm_request", "llm_response"]
    assert "error" in lines[1]


def test_full_sequence_produces_ordered_trace_lines(tmp_path: Path) -> None:
    """chat heard -> decide -> llm escalation -> chat sent, exactly once each,
    in causal order, in one persona file."""
    trace = TraceLog(tmp_path / "traces", "Doramir-01")
    agent, client, _clock = make_agent(trace, tmp_path)
    client.chat = [(9001, "hi bot")]
    agent.tick()
    trace.close()
    lines = read_lines(tmp_path / "traces", "Doramir-01")
    # The causal chain must appear exactly, in order; after the reply the
    # goal script may add its own mechanical action lines (never sampled).
    assert kinds(lines)[:9] == [
        "state_tick",
        "world_event",
        "chat_heard",
        "decide_request",
        "decide_response",
        "llm_request",
        "llm_response",
        "action_executed",
        "chat_sent",
    ]
    heard = lines[2]
    assert heard["speaker"] == "Trader"
    assert heard["message"] == "hi bot"
    assert heard["channel"] == "public"
    assert heard["map"] == "prontera", "every line carries its own context"
    request = lines[3]["request"]
    assert request["state"]["event"], "the decide request captures the trigger context"
    assert lines[6]["reply"] == "gg"
    sent = lines[8]
    assert sent["channel"] == "public"
    assert sent["message"] == "gg"
    assert sent["action"] == "Say"
    assert client.said == ["gg"], "the real send still happened"


def test_world_event_lines_carry_payload_and_context(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    agent, _client, _clock = make_agent(trace, tmp_path)
    state = agent.build_state()
    agent.deliver_event(
        state,
        MonsterSpotted(actor=ActorRef(id=7, name="Poring", kind="monster", distance=3.0)),
    )
    agent.deliver_event(state, DamageTaken(amount=12, from_id=7))
    trace.close()
    lines = read_lines(tmp_path, "p")
    events = [line for line in lines if line["kind"] == "world_event"]
    assert len(events) == 2
    monster = events[0]
    assert monster["event"] == "MonsterSpotted"
    assert monster["monster"] == "Poring"
    assert monster["monster_id"] == 7
    assert monster["map"] == "prontera"
    assert monster["x"] == 120
    assert monster["y"] == 74
    assert monster["adjacent_monsters"] >= 0
    damage = events[1]
    assert damage["event"] == "DamageTaken"
    assert damage["amount"] == 12
    assert damage["from_id"] == 7


def test_action_lines_cover_moves_and_chat_alias(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    agent, client, _clock = make_agent(trace, tmp_path)
    state = agent.build_state()
    client.last_built_state = state  # the cached view a real tick maintains
    agent.execute_actions(
        (MoveTo(121, 75), Say("public line"), PartyChat("party line"), WhisperTo("Trader", "psst"))
    )
    trace.close()
    lines = read_lines(tmp_path, "p")
    actions = [line for line in lines if line["kind"] == "action_executed"]
    assert [line["action"] for line in actions] == ["MoveTo", "Say", "PartyChat", "WhisperTo"]
    assert actions[0]["params"] == {"x": 121, "y": 75}
    assert actions[0]["map"] == "prontera"
    chats = [line for line in lines if line["kind"] == "chat_sent"]
    assert [(c["channel"], c["message"]) for c in chats] == [
        ("public", "public line"),
        ("party", "party line"),
        ("whisper", "psst"),
    ], "chat stays greppable through the chat_sent alias"


def test_state_tick_is_bounded_to_once_per_interval(tmp_path: Path) -> None:
    trace = TraceLog(tmp_path, "p")
    agent, _client, clock = make_agent(trace, tmp_path)
    agent.tick()
    clock.now += 1.0
    agent.tick()
    clock.now += STATE_TICK_INTERVAL_S
    agent.tick()
    trace.close()
    lines = read_lines(tmp_path, "p")
    ticks = [line for line in lines if line["kind"] == "state_tick"]
    assert len(ticks) == 2, "one anchor snapshot + one per interval, never per tick"
    snapshot = ticks[0]
    assert snapshot["map"] == "prontera"
    assert snapshot["x"] == 120
    assert snapshot["hp_max"] > 0
    assert snapshot["base_level"] >= 1
    assert snapshot["inventory_counts"] == {}
    assert snapshot["online"] is False


def test_no_trace_dir_means_no_files_and_same_behavior(tmp_path: Path) -> None:
    agent, client, _clock = make_agent(None, tmp_path)
    client.chat = [(9001, "hi bot")]
    agent.tick()
    assert client.said == ["gg"], "behavior is identical without tracing"
    produced = [p.name for p in tmp_path.rglob("*.jsonl")]
    assert produced == [], "no trace dir, no files"


def test_host_wires_per_persona_trace_files(tmp_path: Path) -> None:
    roster = make_roster()
    manifest = write_host_manifest(tmp_path, roster)
    trace_dir = tmp_path / "traces"
    host = AgentHost(
        roster,
        str(manifest),
        client_factory=FakeGameClient,
        world_state=None,
        run_worldfeed=False,
        trace_dir=trace_dir,
    )
    try:
        assert set(host.agents) == set(roster.personas)
        files = {p.name for p in trace_dir.glob("*.jsonl")}
        assert files == {f"{pid}.jsonl" for pid in host.agents}
        for agent in host.agents.values():
            brain = agent.brain
            assert isinstance(brain, EventDrivenBrain)
            assert agent._trace is not None
            assert brain._trace is agent._trace
            assert isinstance(brain._model, TracedDecisionModel)
    finally:
        host.stop()


def test_host_without_trace_dir_stays_untraced(tmp_path: Path) -> None:
    roster = make_roster()
    manifest = write_host_manifest(tmp_path, roster)
    host = AgentHost(
        roster,
        str(manifest),
        client_factory=FakeGameClient,
        world_state=None,
        run_worldfeed=False,
    )
    try:
        for agent in host.agents.values():
            assert agent._trace is None
            brain = agent.brain
            assert isinstance(brain, EventDrivenBrain)
            assert not isinstance(brain._model, TracedDecisionModel)
    finally:
        host.stop()


def test_host_fails_open_on_unwritable_trace_dir(tmp_path: Path) -> None:
    roster = make_roster()
    manifest = write_host_manifest(tmp_path, roster)
    blocker = tmp_path / "blocked"
    blocker.write_text("a file where the trace dir should be")
    host = AgentHost(
        roster,
        manifest,
        client_factory=FakeGameClient,
        world_state=None,
        run_worldfeed=False,
        trace_dir=blocker,
    )
    try:
        assert host.agents, "the host constructs despite the blocked trace dir"
        host.step()  # schedule pass must not raise on tracing failure
        assert all(agent._trace is None for agent in host.agents.values())
    finally:
        host.stop()


def test_brain_logs_goal_review_and_plan_authoring(tmp_path: Path, state: Any) -> None:
    trace = TraceLog(tmp_path, "p")
    answers = dict(LOW_CONFIDENCE_ANSWERS)
    answers["change_goal"] = {"type": "choice", "choice": "farm", "confidence": 0.9}
    brain = EventDrivenBrain(
        ScriptedDecisionModel(answers=answers),
        StaticChatGenerator(["gg"]),
        mob_db=FakeMobDB({"Poring": MobInfo(id=1002, name="Poring", level=3)}),
        trace=trace,
    )
    brain.handle_event(state, Heartbeat(seq=1))
    brain.handle_event(state, Heartbeat(seq=2), trigger="idle_review")
    trace.close()
    lines = read_lines(tmp_path, "p")
    reviews = [line for line in lines if line["kind"] == "goal_review"]
    assert [r["trigger"] for r in reviews] == ["heartbeat", "idle_review"], "provenance kept"
    assert reviews[0]["goal"] == "farm_item"
    assert reviews[0]["previous_goal"] == "grind", "the reviewed-from goal is kept"
    plans = [line for line in lines if line["kind"] == "plan_authored"]
    assert len(plans) == 2, "every re-authoring is recorded"
    plan = plans[0]
    assert plan["targets"] == ["Poring"]
    assert plan["map"] == "prt_fild08"
    assert isinstance(plan["duration_s"], (int, float))
    assert plan["goal"] == "farm_item"
    assert plan["trigger"] == "heartbeat"


def test_idle_watch_labels_its_review_trigger(tmp_path: Path, state: Any) -> None:
    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _client, clock = make_agent(trace, tmp_path)
    agent._last_action_monotonic = clock.monotonic() - IDLE_REVIEW_S - 1.0
    agent._idle_watch(state)
    trace.close()
    lines = read_lines(tmp_path, "Doramir-01")
    reviews = [line for line in lines if line["kind"] == "goal_review"]
    assert len(reviews) == 1
    assert reviews[0]["trigger"] == "idle_review"


def test_playing_parse_args_accepts_trace_dir() -> None:
    args = playing.parse_args(
        ["--manifest", "m", "--runtime-root", "r", "--memory-root", "mem", "--decision-url", "d"]
    )
    assert args.trace_dir is None, "default: no tracing"
    args = playing.parse_args(
        [
            "--manifest",
            "m",
            "--runtime-root",
            "r",
            "--memory-root",
            "mem",
            "--decision-url",
            "d",
            "--trace-dir",
            "run/traces",
        ]
    )
    assert args.trace_dir == Path("run/traces")


@pytest.mark.parametrize(
    "runner",
    ["scripts/population_host_runner.py", "scripts/plain_host_runner.py"],
)
def test_runners_expose_trace_dir_flag(runner: str) -> None:
    repo = Path(__file__).parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    proc = subprocess.run(
        [sys.executable, str(repo / runner), "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--trace-dir" in proc.stdout
