"""Receipt-bound opt-in actual host tracers; all effects are offline wires."""

import json
import struct
import threading
from pathlib import Path
from typing import Any

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import planning_runtime
from robots.app.agent_runtime import ScheduledAgent
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcRespond, TalkToNpc
from robots.domain.events import Heartbeat
from robots.society.memory import ExperienceNote
from tests.test_llm_planner import frame, plan_arguments
from tests.test_llm_planning_host_tick import BlockedModel, tracer_host
from tests.test_native_npc_guidance import dialog
from tests.test_native_playing_keepalive import KeepaliveWire
from tests.test_npc_plan_contract import npc_arguments
from tests.test_playing_runtime import monster, position


def admit_and_issue(agent, brain, model, decision) -> None:
    assert agent.connect()
    assert model.entered.wait(1)
    model.release.set()
    brain.wait_for_worker(1)
    agent.tick()
    assert decision.entered.wait(1)
    decision.release.set()
    brain.execution.wait_for_worker(1)
    agent.tick()


def finish_review(agent, brain, decision) -> None:
    decision.release.set()
    brain.execution.wait_for_worker(1)
    agent.tick()


class NpcModel(BlockedModel):
    def __init__(self) -> None:
        super().__init__()
        self.replan_entered = threading.Event()
        self.replan_release = threading.Event()
        self.review_after = 20

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(json.loads(json.dumps(payload)))
        if len(self.payloads) % 2 == 1:
            self.entered.set()
            assert self.release.wait(5), "test must release planner"
            if len(self.payloads) > 2:
                self.replan_entered.set()
                assert self.replan_release.wait(5), "test must release replanner"
            return frame("investigate", {"topic": "npc"}, "npc-read")
        context = json.loads(payload["messages"][1]["content"])
        receipt = context["caller_capabilities"]["npc_observation"]
        if receipt is None:
            arguments = plan_arguments()
            arguments.update(
                phases=[{"kind": "idle", "map_name": "prontera"}],
                success="wait complete",
                progress="wait complete",
            )
            return frame("submit_plan", arguments, "passive-plan")
        arguments = npc_arguments("next" if receipt["stage"] == "next" else "choose")
        arguments["review_after"] = self.review_after
        intent = arguments["phases"][0]["npc_intent"]
        for field in ("npc_id", "epoch", "map_name", "opened_sequence", "prompt_sequence"):
            intent[field] = receipt[field]
        if receipt["stage"] == "menu":
            intent["option_index"] = receipt["option_indices"][-1]
        return frame("submit_plan", arguments, "npc-plan")


class NpcDecision:
    def __init__(self, choice: str = "continue") -> None:
        self.choice = choice
        self.entered = threading.Event()
        self.release = threading.Event()
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        self.entered.set()
        assert self.release.wait(5), "test must release decision"
        return {"answers": {"plan_execution": {"choice": self.choice, "confidence": 0.99}}}


def npc_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str = "next",
    page: str = "Received guide",
):
    model, now = NpcModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    client = agent.client
    assert isinstance(client, PlayingClient)
    raw = bytearray(monster(kind=6, aid=444))
    raw[59:62] = position(42, 38)
    wire.add(bytes(raw))
    connect = client.connect

    def connect_with_ui(*args: Any, **kwargs: Any) -> Any:
        result = connect(*args, **kwargs)
        client.perform_native(TalkToNpc(444))
        wire.add(dialog(0xB4, page, npc=444))
        wire.add(dialog(0xB5, npc=444) if operation == "next" else dialog(0xB7, "A::C", npc=444))
        return result

    monkeypatch.setattr(client, "connect", connect_with_ui)
    decision = NpcDecision()
    monkeypatch.setattr(brain.decision, "decide", decision.decide)
    return host, wire, brain, model, now, decision


@pytest.mark.parametrize("operation", ["next", "choose"])
def test_actual_npc_investigation_admission_clef_before_exact_bound_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    host, wire, brain, model, _, decision = npc_host(tmp_path, monkeypatch, operation)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        captured = json.loads(model.payloads[0]["messages"][1]["content"])
        assert (
            "npc" in captured["caller_capabilities"]["supported"]
        ), "actual host NPC capability missing"
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.active_plan is not None, "actual planner must decode and freshly admit NPC"
        assert brain.active_plan.phases[0].npc_intent is not None
        assert decision.entered.wait(1), "admission must trigger event-only physical CLEF review"
        assert len(wire.sent) == 1, "pending first CLEF review must not issue NPC response"
        tool = json.loads(model.payloads[1]["messages"][-1]["content"])
        assert tool["data"]["dialogue"]["npc_id"] == 444
        assert tool["data"]["dialogue"]["pages"] == ["Received guide"]
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        expected = (
            struct.pack("<HI", 0xB9, 444)
            if operation == "next"
            else struct.pack("<HIB", 0xB8, 444, 3)
        )
        assert wire.sent == [struct.pack("<HIB", 0x90, 444, 1), expected]
        assert brain.execution.counters["applied"] == 1
        for _ in range(4):
            agent.tick()
        assert wire.sent[-1] == expected
        assert len(wire.sent) == 2
        assert len(decision.requests) == 1
    finally:
        model.release.set()
        decision.release.set()
        host.stop()


def test_actual_host_npc_uses_verified_cache_identity_and_retains_raw_gat_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, _, decision = npc_host(tmp_path, monkeypatch, "choose")
    agent = host.agents["one"]
    client = agent.client
    assert isinstance(client, PlayingClient)
    client.cache = MapCache([WalkMap("prontera", 100, 100, bytes(10000))])
    seq, at, pid, _ = wire.frames[1]
    wire.frames[1] = (seq, at, pid, struct.pack("<H16sHH", 0x91, b"prontera.gat", 42, 37))
    wire.map_name = "prontera.gat"
    try:
        admit_and_issue(agent, brain, model, decision)
        assert brain.active_plan is not None
        assert brain.active_plan.phases[0].map_name == "prontera"
        assert wire.map_name == "prontera.gat"
        assert client._tracker is not None
        assert client._tracker.view.map_name == "prontera.gat"
        assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 444, 3)
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize("failure", ["timeout", "denied", "send", "missing"])
def test_failed_dispatch_or_expired_wait_requests_one_bounded_fresh_plan_not_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch, "choose")
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)
        now[0] = 10.0
        if failure == "missing":
            client = agent.client
            assert isinstance(client, PlayingClient)
            monkeypatch.setattr(client, "perform_native", lambda _action: None)
        if failure == "send":

            def failed_send(raw: bytes) -> None:
                msg = "offline source send failure"
                raise OSError(msg)

            monkeypatch.setattr(wire, "_send", failed_send)
        elif failure == "denied":
            perform = agent._perform

            def drift_before_perform(action) -> None:
                wire.add(dialog(0xB7, "New::menu", npc=444))
                perform(action)

            monkeypatch.setattr(agent, "_perform", drift_before_perform)
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        phase = brain._npc_phase
        assert phase is not None
        if failure == "timeout":
            now[0] = 15.0
        elif failure == "denied":
            wire.add(dialog(0xB4, "Later unrelated to denied request", npc=444))
        agent.tick()
        assert phase.status == "failed"
        assert phase.progress_sequence is None
        assert (
            brain.runtime.lifecycle.counters["requests"] == 2
        ), "phase failure did not request bounded fresh planning"
        assert model.replan_entered.wait(1)
        for _ in range(6):
            agent.tick()
        assert brain.runtime.lifecycle.counters["requests"] == 2
        assert len(wire.sent) == (2 if failure == "timeout" else 1)
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_clef_receives_detached_complete_permitted_ui_and_current_typed_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = "Received " + "x" * 3500
    host, wire, brain, model, _, decision = npc_host(tmp_path, monkeypatch, "choose", page)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)
        request = decision.requests[0]
        assert (
            request["state"].get("caller_capabilities", {}).get("npc_observation") is not None
        ), "CLEF capture omits current typed NPC receipt"
        assert request["state"]["received_npc_ui"]["pages"] == [page]
        frozen = json.dumps(request)
        wire.add(dialog(0xB4, "Later UI", npc=444))
        brain.memory.log.append(ExperienceNote(1, "other", "late note"))
        assert json.dumps(request) == frozen
        assert len(frozen.encode()) <= 32768
        assert "not" in request["questions"]["plan_execution"]["instructions"]
    finally:
        model.release.set()
        decision.release.set()
        host.stop()


def replace_host_binding(agent, wire, now: list[float], replacement: str):
    if replacement == "session":
        return reconnect_identical_ui(agent, wire)
    new_wire = KeepaliveWire(now)
    new_wire.frames = list(wire.frames[:-2])
    new_wire.native_epoch = new_wire.selection_epoch = new_wire.map_epoch = wire.native_epoch
    new_wire.char_name = wire.char_name
    if replacement == "client":
        new_client = PlayingClient(new_wire, monotonic=lambda: now[0])
        agent.client = new_client
    else:
        new_client = agent.client
        assert isinstance(new_client, PlayingClient)
        new_client.wire = new_wire
    new_client.build_native_state(agent.goal)
    new_client.perform_native(TalkToNpc(444))
    new_wire.add(*(f[3] for f in wire.frames[-2:]))
    return new_wire, new_client


def reconnect_identical_ui(
    agent: ScheduledAgent, wire: KeepaliveWire
) -> tuple[KeepaliveWire, PlayingClient]:
    epoch, frames = wire.native_epoch, list(wire.frames)
    client = agent.client
    assert isinstance(client, PlayingClient)
    client.connect()
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = epoch
    wire.frames = frames[:-2]
    client.perform_native(TalkToNpc(444))
    wire.add(*(f[3] for f in frames[-2:]))
    return wire, client


@pytest.mark.parametrize("replacement", ["client", "wire", "session"])
@pytest.mark.parametrize("stage", ["planning", "decision", "queued", "waiting"])
def test_binding_replacement_with_identical_metadata_invalidates_all_old_npc_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str, stage: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch, "choose")
    agent = host.agents["one"]
    old_client = agent.client
    assert isinstance(old_client, PlayingClient)
    queued: list[NpcRespond] = []
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        original_receipt = old_client.planning_npc_observation(brain.identity)
        assert original_receipt is not None
        if stage != "planning":
            model.release.set()
            brain.wait_for_worker(1)
            agent.tick()
            assert decision.entered.wait(1)
        if stage in ("queued", "waiting"):
            decision.release.set()
            brain.execution.wait_for_worker(1)
            if stage == "queued":
                original = agent.execute_actions

                def retain(actions) -> None:
                    queued.extend(action for action in actions if isinstance(action, NpcRespond))

                monkeypatch.setattr(agent, "execute_actions", retain)
                agent.tick()
                monkeypatch.setattr(agent, "execute_actions", original)
                assert len(queued) == 1
            else:
                agent.tick()
                assert len(wire.sent) == 2
        new_wire, new_client = replace_host_binding(agent, wire, now, replacement)
        assert new_client.planning_npc_observation(brain.identity) == original_receipt
        before = list(new_wire.sent)
        if stage == "queued":
            agent._perform(queued[0])
        else:
            agent.tick()
        assert brain.active_plan is None, "host kept a plan across a changed client/wire binding"
        assert brain._npc_phase is None, "host kept phase/issued barrier across replacement"
        model.release.set()
        decision.release.set()
        brain.wait_for_worker(1)
        brain.execution.wait_for_worker(1)
        agent.tick()
        agent.deliver_event(agent.build_state(), Heartbeat(9))
        assert new_wire.sent == before, f"old {stage} work dispatched against replacement"
    finally:
        model.release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize("operation", ["next", "choose"])
def test_expected_waiting_survives_until_new_same_open_received_ui_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch, operation)
    agent = host.agents["one"]
    try:
        admit_and_issue(agent, brain, model, decision)
        admitted = brain.active_plan
        assert admitted is not None
        client = agent.client
        assert isinstance(client, PlayingClient)
        assert client.planning_npc_observation(brain.identity) is None
        for second in (0.5, 1.0, 2.0):
            now[0] = second
            agent.tick()
        assert (
            brain.active_plan is admitted
        ), "expected post-request waiting must not invalidate admitted NPC"
        phase = brain._npc_phase
        assert phase is not None
        assert getattr(phase, "progress_sequence", None) is None
        wire.add(dialog(0xB4, "New received page", npc=444), dialog(0xB5, npc=444))
        agent.tick()
        received = agent.build_state().npc_dialogue
        assert received is not None
        assert phase.progress_sequence == received.sequence
        assert phase.status == "completed"
        for _ in range(4):
            agent.tick()
        assert len(wire.sent) == 2, "one completed phase cannot automatically answer follow-up UI"
        assert len(decision.requests) == 1
    finally:
        model.release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize("choice", ["hold", "replan"])
def test_npc_clef_control_does_not_author_menu_or_use_legacy_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, choice: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch, "choose")
    decision.choice = choice
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)
        now[0] = 10.0
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert brain.execution.choice == "hold"
        assert len(wire.sent) == 1
        assert brain.runtime.lifecycle.counters["requests"] == (2 if choice == "replan" else 1)
        if choice == "replan":
            assert model.replan_entered.wait(1)
            assert brain.runtime.job is not None
            decision.choice = "hold"
            model.replan_release.set()
            brain.wait_for_worker(1)
            agent.tick()
            brain.execution.wait_for_worker(1)
            agent.tick()
            assert brain.runtime.lifecycle.counters["admitted"] == 2
            assert len(model.payloads) == 4
        for _ in range(5):
            agent.tick()
        assert len(wire.sent) == 1
        assert brain.mechanical_fallback_allowed is False
        assert brain.runtime.lifecycle.counters["requests"] == (2 if choice == "replan" else 1)
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def drift_ui(wire, now: list[float], change: str) -> None:
    if change == "deadline":
        # Newly received actionable UI expires at 30s, not the historical 15s.
        now[0] = 30.0
    elif change == "actor":
        wire.add(struct.pack("<HIB", 0x80, 444, 0))
    elif change == "reuse":
        wire.add(struct.pack("<HIB", 0x80, 444, 0))
        raw = bytearray(monster(kind=6, aid=444))
        raw[59:62] = position(42, 38)
        wire.add(bytes(raw), dialog(0xB7, "A::C", npc=444))
    elif change == "map":
        wire.map_name = "izlude"
        wire.add(struct.pack("<H16sHH", 0x91, b"izlude", 42, 37))
    elif change == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 3
    elif change == "index":
        wire.add(dialog(0xB7, "A", npc=444))
    else:
        wire.add(dialog(0xB7, "New::same-index", npc=444))


@pytest.mark.parametrize("checkpoint", ["admission", "decision"])
@pytest.mark.parametrize(
    "change", ["deadline", "actor", "reuse", "map", "epoch", "index", "sequence"]
)
def test_actual_received_drift_denies_old_proposal_or_pending_clef_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str, change: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch, "choose")
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        if checkpoint == "decision":
            agent.tick()
            assert decision.entered.wait(1)
        drift_ui(wire, now, change)
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        for _ in range(5):
            agent.tick()
        assert brain.active_plan is None
        assert len(wire.sent) == 1
        assert brain.execution.counters["applied"] == 0
        assert brain.runtime.lifecycle.counters["requests"] == 1
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize(
    "change",
    [
        "same",
        "peer",
        "cutin",
        "map",
        "actor",
        "reuse",
        "epoch",
        "new-open",
        "close",
        "numeric",
        "string",
    ],
)
def test_waiting_requires_new_matching_same_open_ui_not_unrelated_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    try:
        admit_and_issue(agent, brain, model, decision)
        phase = brain._npc_phase
        assert phase is not None
        client = agent.client
        assert isinstance(client, PlayingClient)
        if change in ("map", "actor", "reuse", "epoch"):
            drift_ui(wire, now, change)
        elif change == "peer":
            wire.add(dialog(0xB4, "Peer text", npc=777), dialog(0xB5, npc=777))
        elif change == "cutin":
            wire.add(struct.pack("<H64sB", 0x1B3, b"illustration", 0))
        elif change == "new-open":
            client._npc.invalidate()
            client.perform_native(TalkToNpc(444))
            wire.add(dialog(0xB4, "Different opening", npc=444), dialog(0xB5, npc=444))
        elif change in ("close", "numeric", "string"):
            wire.add(dialog({"close": 0xB6, "numeric": 0x142, "string": 0x1D4}[change], npc=444))
        before = list(wire.sent)
        for _ in range(4):
            agent.tick()
        assert phase.progress_sequence is None
        assert wire.sent == before
        assert len(decision.requests) == 1
        assert phase.status == ("waiting" if change in ("same", "peer", "cutin") else "failed")
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_actual_host_npc_send_control_flow_keeps_exact_origin_and_failed_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    host, wire, brain, model, _, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    origin = error_type("offline NPC send origin")
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)

        def failed_send(raw: bytes) -> None:
            raise origin

        monkeypatch.setattr(wire, "_send", failed_send)
        decision.release.set()
        brain.execution.wait_for_worker(1)
        with pytest.raises(error_type) as caught:
            agent.tick()
        assert caught.value is origin
        tb = caught.value.__traceback__
        assert tb is not None
        while tb.tb_next is not None:
            tb = tb.tb_next
        assert tb.tb_frame.f_code.co_name == "failed_send"
        phase = brain._npc_phase
        assert phase is not None
        assert phase.status == "failed"
        assert phase.progress_sequence is None
        agent.tick()
        assert len(wire.sent) == 1
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_new_admitted_version_cannot_inherit_issued_barrier_or_old_queued_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    try:
        admit_and_issue(agent, brain, model, decision)
        old_phase = brain._npc_phase
        assert old_phase is not None
        assert old_phase.action is not None
        wire.add(dialog(0xB4, "New guide", npc=444), dialog(0xB5, npc=444))
        agent.tick()
        assert old_phase.status == "completed"
        now[0] = 10.0
        decision.release.clear()
        decision.entered.clear()
        brain.request_replan(agent.build_state(), "fresh received follow-up")
        assert model.replan_entered.wait(1)
        model.replan_release.set()
        brain.wait_for_worker(1)
        agent.tick()
        fresh = brain._npc_phase
        assert fresh is not None
        assert fresh is not old_phase
        assert fresh.status == "review"
        assert fresh.action is None
        assert decision.entered.wait(1)
        agent._perform(old_phase.action)
        assert len(wire.sent) == 2
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert fresh.status == "waiting"
        assert len(wire.sent) == 3
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_disconnect_invalidates_npc_phase_and_queued_action_before_client_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, _, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    try:
        admit_and_issue(agent, brain, model, decision)
        assert brain._npc_phase is not None
        original_close = wire.close
        observed: list[bool] = []

        def close(*args: Any, **kwargs: Any) -> None:
            observed.append(brain._npc_phase is None and brain.active_plan is None)
            original_close(*args, **kwargs)

        monkeypatch.setattr(wire, "close", close)
        agent.disconnect()
        assert observed == [True], "NPC plan and phase must be invalidated before native close"
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_queued_npc_reply_is_denied_when_admitted_plan_review_deadline_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    model.review_after = 1
    agent = host.agents["one"]
    queued: list[NpcRespond] = []
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)

        def retain(actions) -> None:
            queued.extend(a for a in actions if isinstance(a, NpcRespond))

        monkeypatch.setattr(agent, "execute_actions", retain)
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert len(queued) == 1
        now[0] = 1.0
        client = agent.client
        assert isinstance(client, PlayingClient)
        assert client.planning_npc_observation(brain.identity) is not None
        agent._perform(queued[0])
        assert len(wire.sent) == 1, "queued action ignored admitted plan review deadline"
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_received_progress_after_plan_review_deadline_cannot_complete_expired_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    model.review_after = 1
    agent = host.agents["one"]
    try:
        admit_and_issue(agent, brain, model, decision)
        phase = brain._npc_phase
        assert phase is not None
        now[0] = 1.0
        wire.add(dialog(0xB4, "Late received page", npc=444), dialog(0xB5, npc=444))
        agent.tick()
        assert phase.status == "failed", "received UI completed an expired admitted phase"
        assert phase.progress_sequence is None
        assert len(wire.sent) == 2
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_full_permitted_ui_does_not_become_an_oversized_execution_event_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = "x" * 4096
    host, _, brain, model, _, decision = npc_host(tmp_path, monkeypatch, "next", page)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.active_plan is not None
        assert decision.entered.wait(
            1
        ), "received UI was duplicated into the bounded event key and prevented review"
        assert decision.requests[0]["state"]["received_npc_ui"]["pages"] == [page]
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_host_reconnect_invalidates_old_npc_state_before_wire_connect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    observed: list[bool] = []
    connect = wire.connect
    try:
        admit_and_issue(agent, brain, model, decision)
        assert brain._npc_phase is not None

        def reconnect(*args: Any, **kwargs: Any) -> None:
            observed.append(brain.active_plan is None and brain._npc_phase is None)
            connect(*args, **kwargs)

        monkeypatch.setattr(wire, "connect", reconnect)
        agent.online = False
        now[0] = 10.0
        model.replan_release.set()
        assert agent.connect()
        assert observed == [
            True
        ], "host invalidated prior NPC only after replacement session allocation"
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_npc_planner_timeout_retains_physical_owner_and_passive_keepalive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        job = brain.runtime.job
        assert job is not None
        agent.tick()
        for second in (20, 40, 60, 80, 121):
            now[0] = float(second)
            agent.tick()
        assert brain.runtime.lifecycle.pending is None
        assert brain.runtime.job is job
        assert not brain.reconnect_ready
        assert wire.keepalives == [20.0, 40.0, 60.0, 80.0, 121.0]
        assert len(wire.sent) == 1
        assert len(model.payloads) == 1
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.active_plan is None
        assert brain.reconnect_ready
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


@pytest.mark.parametrize("claimed", [False, True])
def test_changed_binding_retains_physical_planner_until_join_and_requires_fresh_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, claimed: bool
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    entered, release = threading.Event(), threading.Event()
    original_propose = planning_runtime._propose_job

    def before_claim(job, factory, clock) -> None:
        entered.set()
        assert release.wait(5)
        original_propose(job, factory, clock)

    if not claimed:
        monkeypatch.setattr(planning_runtime, "_propose_job", before_claim)
    try:
        assert agent.connect()
        assert (model.entered if claimed else entered).wait(1)
        job = brain.runtime.job
        assert job is not None
        new_wire, _ = replace_host_binding(agent, wire, now, "client")
        agent.tick()
        assert brain.runtime.job is job
        assert job.cancelled is not claimed
        assert not brain.reconnect_ready
        with pytest.raises(RuntimeError, match="release unconfirmed"):
            agent._start_brain()
        assert brain.runtime.job is job
        assert not agent.connect()  # Even online connect cannot return physical ownership.
        model.release.set()
        release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.reconnect_ready
        assert brain.active_plan is None
        assert brain.runtime.lifecycle.counters["admitted"] == 0
        assert len(model.payloads) == (2 if claimed else 0)
        monkeypatch.setattr(planning_runtime, "_propose_job", original_propose)
        now[0] = 10.0
        model.replan_release.set()
        agent._start_brain()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)
        finish_review(agent, brain, decision)
        assert brain.runtime.lifecycle.counters["admitted"] == 1
        assert len(new_wire.sent) == 2
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()


def test_pending_npc_clef_timeout_retains_worker_and_blocks_fresh_binding_until_join(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, wire, brain, model, now, decision = npc_host(tmp_path, monkeypatch)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert decision.entered.wait(1)
        job = brain.execution.job
        assert job is not None
        for second in (16, 31, 32):
            now[0] = float(second)
            agent.tick()
        assert brain.execution.counters["timeouts"] == 1
        assert brain.execution.job is job
        assert not brain.reconnect_ready
        assert len(wire.sent) == 1
        with pytest.raises(RuntimeError, match="release unconfirmed"):
            agent._start_brain()
        assert brain._npc_phase is None
        assert brain.execution.job is job
        decision.release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert brain.reconnect_ready
        assert brain.execution.counters["applied"] == 0
        assert brain.runtime.lifecycle.counters["requests"] == 1
    finally:
        model.release.set()
        model.replan_release.set()
        decision.release.set()
        host.stop()
