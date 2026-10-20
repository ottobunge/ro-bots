"""Offline execution-control tracers through the real host and planner."""

import json
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from robots.app import execution_decisions, planning_brain
from robots.app.agent_runtime import AgentHost
from robots.app.planning_brain import PlannedBrain
from robots.app.planning_job_context import capture_job_context
from robots.domain.events import Heartbeat, ScriptFailed
from robots.domain.model import ActorRef
from robots.society.memory import ExperienceNote
from tests.test_llm_planner import frame
from tests.test_llm_planning_host_tick import tracer_host
from tests.test_llm_planning_rest_execution import MechanicalRestModel, vitals
from tests.test_native_pose_recovery import pose
from tests.test_native_skill_context import row, skill_list


class FreshModel(MechanicalRestModel):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = super().complete(payload)
        if len(self.payloads) == 3:
            return frame("investigate", {"topic": "map"}, "fresh-read")
        return response


@pytest.mark.parametrize(
    ("choice", "confidence", "expected", "replan"),
    [
        ("continue", 0.99, "continue", False),
        ("hold", 0.99, "hold", False),
        ("replan", 0.99, "hold", True),
        ("continue", 0.1, "hold", True),
        ("invent", 0.99, "hold", True),
        ("continue", True, "hold", True),
        ("continue", float("nan"), "hold", True),
        ("continue", float("inf"), "hold", True),
    ],
)
def test_exec2_host_applies_choice_and_bounded_fresh_replan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    choice: str,
    confidence: float,
    expected: str,
    replan: bool,
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    entered = threading.Event()

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        assert set(request) == {"model", "state", "questions"}
        assert set(request["questions"]) == {"plan_execution"}
        entered.set()
        return {"answers": {"plan_execution": {"choice": choice, "confidence": confidence}}}

    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        now[0] = 10.0
        model.replan_release.set()
        agent.deliver_event(agent.build_state(), Heartbeat(7))
        assert entered.wait(1)
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert getattr(brain.execution, "choice", None) == expected
        if replan:
            brain.wait_for_worker(1)
            agent.tick()
            assert len(model.payloads) == 4, "replan must investigate before submission"
        assert brain.runtime.lifecycle.counters["requests"] == (2 if replan else 1)
        assert brain.execution.counters["applied"] == 1
        for _ in range(3):
            agent.tick()
        assert brain.runtime.lifecycle.counters["requests"] == (2 if replan else 1)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize("change", ["version", "epoch", "map", "death"])
def test_exec3_detached_owner_context_and_stale_reply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    entered, release = threading.Event(), threading.Event()
    requests: list[dict[str, Any]] = []

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        requests.append(request)
        entered.set()
        assert release.wait(5)
        return {"answers": {"plan_execution": {"choice": "continue", "confidence": 0.99}}}

    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        brain.memory.log.append(ExperienceNote(0, "other", "owner-only-note"))
        state = replace(agent.build_state(), inventory={"captured": 1}, inventory_known=True)
        brain.handle_event(state, Heartbeat(7))
        assert entered.wait(1)
        frozen = json.dumps(requests[0])
        state.inventory.clear()
        brain.memory.log.append(ExperienceNote(1, "other", "late-note"))
        assert json.dumps(requests[0]) == frozen
        assert "owner-only-note" in frozen
        assert "late-note" not in frozen
        assert requests[0]["state"]["plan"]["identity"] == {
            "agent": "one",
            "world": "offline-test",
            "character": "WireNovice",
            "session_epoch": brain.identity.session_epoch,
            "ruleset": "pre-re",
        }
        if change == "version":
            brain.runtime.lifecycle.version += 1
        changes: dict[str, dict[str, Any]] = {
            "epoch": {"native_epoch": 999},
            "map": {"map_name": "izlude"},
            "death": {"alive": False},
        }
        state = replace(agent.build_state(), **changes.get(change, {}))
        release.set()
        brain.execution.wait_for_worker(1)
        brain.sync_context(state)
        assert (
            brain.execution.counters["applied"] == 0
        ), "late replies cannot authorize current state"
        assert brain.execution.counters["stale"] == 1
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_exec4_timeout_retains_worker_and_event_dedup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    entered, release = threading.Event(), threading.Event()

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        entered.set()
        assert release.wait(5)
        return {"answers": {"plan_execution": {"choice": "continue", "confidence": 0.99}}}

    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        brain.handle_event(agent.build_state(), Heartbeat(7))
        assert entered.wait(1)
        job = brain.execution.job
        now[0] = 31.0
        vitals(wire, 21, 3)
        agent.tick()
        assert brain.execution.counters["timeouts"] == 1
        assert brain.execution.job is job
        assert not brain.reconnect_ready
        brain.handle_event(agent.build_state(), Heartbeat(8))
        assert brain.execution.counters["decisions"] == 1
        with pytest.raises(RuntimeError, match="release unconfirmed"):
            brain.bind_session(lambda: 31.0)
        release.set()
        brain.execution.wait_for_worker(1)
        agent.tick()
        assert brain.execution.counters["applied"] == 0
        brain.handle_event(agent.build_state(), Heartbeat(7))
        assert brain.execution.counters["decisions"] == 1
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize("change", ["current", "map", "death", "none", "identity", "version"])
def test_timeout_escalation_requires_current_host_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    entered, release = threading.Event(), threading.Event()

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        entered.set()
        assert release.wait(5)
        return {"answers": {"plan_execution": {"choice": "continue", "confidence": 0.99}}}

    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        agent.deliver_event(agent.build_state(), Heartbeat(7))
        assert entered.wait(1)
        job = brain.execution.job
        state = agent.build_state()
        if change == "none":
            brain.runtime.lifecycle.active = None
        elif change == "identity":
            brain.identity = replace(brain.identity, world="other-world")
        elif change == "version":
            brain.runtime.lifecycle.version += 1
        elif change == "map":
            state = replace(state, map_name="izlude")
        elif change == "death":
            state = replace(state, alive=False)
        now[0] = 31.0
        brain.sync_context(state)
        assert brain.execution.counters["timeouts"] == 1
        assert brain.execution.counters["replans"] == (1 if change == "current" else 0)
        assert brain.runtime.lifecycle.counters["requests"] == (2 if change == "current" else 1)
        assert brain.execution.job is job
        assert not brain.reconnect_ready
        brain.sync_context(state)
        assert brain.execution.counters["replans"] == (1 if change == "current" else 0)
        if change == "current":
            assert brain.execution.pauses_request(brain.runtime.lifecycle.version)
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize(
    "failure",
    [
        "none",
        "value",
        "surrogate",
        "budget",
        "nonfinite",
        "source_unicode",
        "source_nonfinite",
        "source_budget",
        "control",
    ],
)
def test_request_failure_holds_without_provider_or_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:

    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    calls: list[dict[str, Any]] = []

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        calls.append(request)
        return {}

    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        attempts: list[str] = []
        origin = KeyboardInterrupt("capture origin")

        capture = _failure_capture(monkeypatch, failure, attempts, origin)
        monkeypatch.setattr(planning_brain, "capture_job_context", capture)
        version = brain.runtime.lifecycle.version
        state = agent.build_state()
        event: Heartbeat | ScriptFailed = Heartbeat(7)
        if failure == "source_unicode":
            state = replace(state, inventory={"bad-\ud800": 1})
        elif failure == "source_nonfinite":
            state = replace(state, nearby=(ActorRef(42, "bad", "player", float("nan")),))
        elif failure == "source_budget":
            event = ScriptFailed("x" * 32768)
        if failure == "control":
            with pytest.raises(KeyboardInterrupt) as caught:
                agent.deliver_event(state, event)
            assert caught.value is origin
        else:
            agent.deliver_event(state, event)
        assert brain.execution.pauses_request(version)
        agent.deliver_event(state, event)
        for _ in range(3):
            agent.tick()
        assert attempts == ([] if failure == "source_budget" else [failure])
        assert all(len(str(key).encode("utf-8")) <= 4096 for key in brain.execution.events)
        assert not calls
        assert brain.execution.job is None
        assert brain.runtime.lifecycle.counters["requests"] == 1
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize("boundary", ["poll", "close"])
@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_completed_control_flow_preserves_origin_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    error_type: type[BaseException],
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    origin = error_type("decision origin")
    cleanup: list[str] = []

    def failed_decision(request: dict[str, Any]) -> dict[str, Any]:
        raise origin

    def failed_close() -> None:
        cleanup.append("planning")
        message = "secondary planning cleanup"
        raise RuntimeError(message)

    monkeypatch.setattr(brain.decision, "decide", failed_decision)
    agent = host.agents["one"]
    try:
        _admit_execution_agent(host, brain, model)
        agent.deliver_event(agent.build_state(), Heartbeat(7))
        brain.execution.wait_for_worker(1)
        if boundary == "close":
            monkeypatch.setattr(brain.runtime, "close", failed_close)
        operation = host.stop if boundary == "close" else agent.tick
        with pytest.raises(error_type) as caught:
            operation()
        assert caught.value is origin
        traceback = caught.value.__traceback__
        assert traceback is not None
        while traceback.tb_next is not None:
            traceback = traceback.tb_next
        assert traceback.tb_frame.f_code.co_name == "failed_decision"
        assert brain.execution.job is None
        if boundary == "close":
            assert cleanup == ["planning"]
            assert not wire.running
    finally:
        model.release.set()
        model.replan_release.set()
        monkeypatch.undo()
        host.stop()


@pytest.mark.parametrize("claimed", [False, True])
def test_cleanup_cancels_only_unclaimed_work_and_retains_physical_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, claimed: bool
) -> None:

    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    entered, release = threading.Event(), threading.Event()
    calls: list[dict[str, Any]] = []
    original = execution_decisions._decide

    def delayed(job: execution_decisions.ExecutionJob, decide: Any) -> None:
        entered.set()
        assert release.wait(5)
        original(job, decide)

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        calls.append(request)
        entered.set()
        assert release.wait(5)
        return {}

    if not claimed:
        monkeypatch.setattr(execution_decisions, "_decide", delayed)
    monkeypatch.setattr(brain.decision, "decide", decide)
    agent = host.agents["one"]
    try:
        _admit_execution_agent(host, brain, model)
        agent.deliver_event(agent.build_state(), Heartbeat(7))
        assert entered.wait(1)
        job = brain.execution.job
        assert job is not None
        with pytest.raises(RuntimeError, match="execution worker release unconfirmed"):
            host.stop()
        assert brain.execution.job is job
        assert job.cancelled is not claimed
        assert not wire.running
        assert not bool(brain.reconnect_ready)
        with pytest.raises(RuntimeError, match="release unconfirmed"):
            brain.bind_session(lambda: 31.0)
        release.set()
        brain.execution.wait_for_worker(1)
        brain.close()
        assert brain.reconnect_ready
        assert len(calls) == int(claimed)
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        brain.execution.wait_for_worker(1)
        brain.close()
        host.stop()


@pytest.mark.parametrize("started", [False, True])
@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_thread_start_failure_preserves_origin_and_known_worker_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    started: bool,
    error_type: type[BaseException],
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    release = threading.Event()
    origin = error_type("start origin")
    original = threading.Thread.start

    def start(thread: threading.Thread) -> None:
        if started:
            original(thread)
        raise origin

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        assert release.wait(5)
        return {}

    agent = host.agents["one"]
    try:
        _admit_execution_agent(host, brain, model)
        monkeypatch.setattr(brain.decision, "decide", decide)
        with monkeypatch.context() as scoped:
            scoped.setattr(threading.Thread, "start", start)
            if error_type is KeyboardInterrupt:
                with pytest.raises(KeyboardInterrupt) as caught:
                    agent.deliver_event(agent.build_state(), Heartbeat(7))
                assert caught.value is origin
            else:
                agent.deliver_event(agent.build_state(), Heartbeat(7))
                assert brain.execution.pauses_request(brain.runtime.lifecycle.version)
        if started:
            job = brain.execution.job
            assert job is not None
            with pytest.raises(RuntimeError, match="execution worker release unconfirmed"):
                host.stop()
            assert brain.execution.job is job
            assert not wire.running
        else:
            assert brain.execution.job is None, "known-unstarted thread cannot own a join"
            host.stop()
        release.set()
        brain.execution.wait_for_worker(1)
        brain.close()
        assert brain.reconnect_ready
    finally:
        release.set()
        model.release.set()
        model.replan_release.set()
        brain.execution.wait_for_worker(1)
        brain.close()
        host.stop()


def test_two_execution_hosts_detach_owner_private_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    hosts: list[AgentHost] = []
    brains: list[PlannedBrain] = []
    models: list[FreshModel] = []
    release = threading.Event()
    requests: list[dict[str, Any]] = []

    def decide(request: dict[str, Any]) -> dict[str, Any]:
        requests.append(request)
        assert release.wait(5)
        return {}

    try:
        for index in (1, 2):
            model, now = FreshModel(), [0.0]
            owner = f"owner-{index}"
            host, wire, brain = tracer_host(
                tmp_path / owner,
                monkeypatch,
                model,
                now,
                owner=owner,
                world=f"world-{index}",
                character=f"Character{index}",
            )
            hosts.append(host)
            brains.append(brain)
            models.append(model)
            wire.add(skill_list(row(level=3)))
            vitals(wire, 20, 2)
            agent = host.agents[owner]
            _admit_execution_agent(host, brain, model, owner)
            brain.memory.log.append(ExperienceNote(0, "other", f"private-note-{index}"))
            items = {f"private-item-{index}": index}
            state = replace(agent.build_state(), inventory=items, inventory_known=True)
            monkeypatch.setattr(brain.decision, "decide", decide)
            agent.deliver_event(state, Heartbeat(7))
            job = brain.execution.job
            assert job is not None
            frozen = json.dumps(job.request, ensure_ascii=False, allow_nan=False)
            assert len(frozen.encode("utf-8")) <= 32768
            assert f"private-note-{index}" in frozen
            assert f"private-item-{index}" in frozen
            assert f"private-note-{3 - index}" not in frozen
            assert f"private-item-{3 - index}" not in frozen
            assert job.request["state"]["plan"]["identity"]["agent"] == owner
            assert job.request["state"]["plan"]["identity"]["world"] == f"world-{index}"
            assert job.request["state"]["plan"]["identity"]["character"] == f"Character{index}"
            items.clear()
            brain.memory.log.append(ExperienceNote(1, "other", "late-private-note"))
            assert json.dumps(job.request, ensure_ascii=False, allow_nan=False) == frozen
            monkeypatch.setattr(brain.decision, "decide", lambda _request: {})
        release.set()
        for brain in brains:
            brain.execution.wait_for_worker(1)
        assert len(requests) == 2
        assert brains[0].memory.log is not brains[1].memory.log
    finally:
        release.set()
        for model in models:
            model.release.set()
            model.replan_release.set()
        for host in hosts:
            host.stop()


def _admit_execution_agent(
    host: AgentHost, brain: PlannedBrain, model: FreshModel, owner: str = "one"
) -> None:
    assert host.agents[owner].connect()
    model.release.set()
    brain.wait_for_worker(1)
    host.agents[owner].tick()


def _failure_capture(
    monkeypatch: pytest.MonkeyPatch, failure: str, attempts: list[str], origin: BaseException
) -> Any:
    def capture(*args: Any, **kwargs: Any) -> Any:
        attempts.append(failure)
        if failure == "control":
            raise origin
        if failure.startswith("source_"):
            return capture_job_context(*args, **kwargs)
        if failure == "none":
            return None
        if failure == "value":
            message = "unavailable capture"
            raise ValueError(message)
        reader = capture_job_context(*args, **kwargs)
        assert reader is not None
        original_read = reader.read

        def read(*read_args: Any, **read_kwargs: Any) -> dict[str, Any]:
            data = original_read(*read_args, **read_kwargs)
            data["data"] = {
                "bad": {
                    "surrogate": "\ud800",
                    "budget": "x" * 32768,
                    "nonfinite": float("nan"),
                }[failure]
            }
            return data

        monkeypatch.setattr(reader, "read", read)
        return reader

    return capture
