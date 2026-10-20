"""Actual offline host REST tracer; packets are synthetic, never live evidence."""

import struct
import threading
from pathlib import Path
from typing import Any

import pytest

from robots.app.playing_runtime import PlayingClient
from robots.domain.planning import PhaseKind
from tests.test_llm_planner import frame, plan_arguments
from tests.test_llm_planning_host_tick import BlockedModel, tracer_host
from tests.test_native_pose_recovery import pose
from tests.test_native_skill_context import row, skill_list
from tests.test_playing_runtime import walk_ack


class MechanicalRestModel(BlockedModel):
    def __init__(self) -> None:
        super().__init__()
        self.replan_entered = threading.Event()
        self.replan_release = threading.Event()
        self.success = "recovered"

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        if len(self.payloads) == 2:
            self.replan_entered.set()
            assert self.replan_release.wait(5), "test must release replanner"
        response = super().complete(payload)
        if len(self.payloads) == 2:
            args = plan_arguments()
            args.update(duration=300, review_after=200, success=self.success)
            return frame("submit_plan", args, "rest-2")
        return response


def vitals(wire: Any, hp: int, sp: int) -> None:
    # Effect-boundary double mirrors BotClient's received B0 retention.
    for parameter, value in ((5, hp), (6, 100), (7, sp), (8, 20)):
        wire.add(struct.pack("<HHi", 0x00B0, parameter, value))
        wire.status_params[parameter] = value


@pytest.mark.parametrize("invalid", ["condition", "map"])
def test_rest_install_denies_unimplemented_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    if invalid == "condition":
        model.success = "wait complete"
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        if invalid == "map":
            wire.add(struct.pack("<H16sHH", 0x0091, b"izlude", 42, 37))
        agent.tick()
        assert wire.sent == [], "REST must not reinterpret unsupported semantics"
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize("ack", [False, True])
def test_rest4_finite_failure_requests_one_replan_with_keepalive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ack: bool
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        if ack:
            wire.add(pose())
            agent.tick()
        for second in (1, 2, 3, 10, 20, 30):
            now[0] = float(second)
            vitals(wire, 20, 2)  # New cursors with identical values are not progress.
            agent.tick()
        assert model.replan_entered.wait(1), "bounded mechanical failure must replan"
        assert wire.sent == (["sit", "stand"] if ack else ["sit"] * 3)
        for second in (40, 60, 80):
            now[0] = float(second)
            agent.tick()
        assert brain.runtime.lifecycle.counters["requests"] == 2
        assert wire.keepalives == [20.0, 40.0, 60.0, 80.0]
        assert bool(brain.is_recovering)
        assert not wire.moves
        assert len(model.payloads) == 2  # Replanner is at the controlled effect boundary.
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_stand_budget_exhaustion_requests_one_replan_without_resit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        vitals(wire, 80, 16)
        agent.tick()
        for second in (1, 2, 3, 10):
            now[0] = float(second)
            agent.tick()
        assert model.replan_entered.wait(1), "exhausted stand budget must replan"
        assert wire.sent == ["sit", "stand", "stand", "stand"]
        assert bool(brain.is_recovering)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_rest3_received_skill_loss_stops_pending_sit_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(skill_list(row(level=0)))
        now[0] = 1.0
        agent.tick()
        assert wire.sent == ["sit"], "lost received sit gate must stop new requests"
        assert bool(brain.is_recovering)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_rest2_fresh_sp_progress_still_requires_own_stand_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        vitals(wire, 80, 2)
        agent.tick()
        assert wire.sent == ["sit"]  # HP alone cannot meet the recovered policy.
        vitals(wire, 80, 16)
        agent.tick()
        assert wire.sent == ["sit", "stand"], "fresh HP/SP success must request stand"
        for second in (0.1, 0.5, 1.0):
            now[0] = second
            wire.add(pose(123, 3))
            agent.tick()
            assert bool(brain.is_recovering)
        assert wire.sent == ["sit", "stand", "stand"]
        wire.add(pose(kind=3))
        agent.tick()
        assert not bool(brain.is_recovering)
        agent.tick()
        assert wire.sent == ["sit", "stand", "stand"]
        assert not wire.moves
        assert len(model.payloads) == 2
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_rest1_actual_host_persistent_received_sit_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.active_plan is not None, "source-qualified REST must be admitted"

        def forbidden_decision(*_args: Any, **_kwargs: Any) -> Any:
            message = "REST mechanics must not call CLEF"
            raise AssertionError(message)

        monkeypatch.setattr(brain.decision, "decide", forbidden_decision)
        assert wire.sent == ["sit"]
        wire.add(pose())
        agent.tick()
        for second in (1, 2, 20):
            now[0] = float(second)
            agent.tick()
        assert bool(brain.is_recovering)
        assert wire.sent == ["sit"]
        assert not wire.moves
        assert wire.keepalives == [20.0]
        assert len(model.payloads) == 2
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


@pytest.mark.parametrize(
    "change", ["skill", "unreceived", "transport", "death", "epoch", "hp_only"]
)
def test_rest_received_boundary_denials_remain_passive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    if change != "unreceived":
        wire.add(skill_list(row(level=2 if change == "skill" else 3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        if change == "transport":
            wire.running = False
        elif change == "death":
            wire.add(struct.pack("<HIB", 0x0080, wire.aid, 1))
        elif change == "epoch":
            wire.native_epoch = wire.selection_epoch = wire.map_epoch = 3
        elif change == "hp_only":
            wire.status_params[5] = 80  # No raw receipt: cannot count as progress or authority.
        agent.tick()
        assert not wire.sent
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_health_improves_requires_fresh_changed_sp_not_new_same_value_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    model.success = "health improves"
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(5018, 1)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        vitals(wire, 20, 2)
        agent.tick()
        assert wire.sent == ["sit"]
        vitals(wire, 20, 3)
        agent.tick()
        assert wire.sent == ["sit", "stand"]
        wire.add(pose((-wire.aid) & 0xFFFFFFFF, 3))
        agent.tick()
        assert not bool(brain.is_recovering)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


class HandoffModel(MechanicalRestModel):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = super().complete(payload)
        if len(self.payloads) == 3:
            return frame("investigate", {"topic": "map"}, "replan-map")
        return response


def test_failed_rest_releases_after_new_idle_and_later_own_stand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = HandoffModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        version = brain.runtime.lifecycle.version
        for second in (1.0, 2.0, 3.0, 10.0):
            now[0] = second
            agent.tick()
        assert model.replan_entered.wait(1)
        assert bool(brain.is_recovering)
        assert wire.sent == ["sit"] * 3
        model.replan_release.set()
        brain.wait_for_worker(1)
        now[0] = 11.0
        agent.tick()
        assert brain.runtime.lifecycle.version > version, (
            brain.runtime.lifecycle.outcome,
            brain.runtime.lifecycle.counters,
            brain.runtime.lifecycle.pending,
            brain.runtime.job,
        )
        assert brain.active_plan is not None
        assert brain.active_plan.phases[0].kind == PhaseKind.IDLE
        assert bool(
            brain.is_recovering
        ), "metadata admission alone cannot release failed pose ownership"
        wire.add(pose(123, 3))
        agent.tick()
        assert bool(brain.is_recovering), "peer standing cannot release ownership"
        wire.add(pose(kind=3))
        agent.tick()
        assert not bool(
            brain.is_recovering
        ), "later own stand must reconcile failure and hand off new IDLE"
        assert not wire.moves
        assert brain.runtime.lifecycle.counters["requests"] == 2
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


class ReplacementRestModel(HandoffModel):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = super().complete(payload)
        if len(self.payloads) == 4:
            args = plan_arguments()
            args.update(duration=300, review_after=200)
            return frame("submit_plan", args, "replacement-rest")
        return response


def test_replacement_rest_requires_old_pose_release_then_fresh_sit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = ReplacementRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        old = brain.runtime.lifecycle.version
        for second in (1.0, 2.0, 3.0, 10.0):
            now[0] = second
            agent.tick()
        assert model.replan_entered.wait(1)
        model.replan_release.set()
        brain.wait_for_worker(1)
        now[0] = 11.0
        agent.tick()
        assert brain.active_plan is not None
        assert brain.active_plan.phases[0].kind == PhaseKind.REST
        assert brain.runtime.lifecycle.version > old
        assert wire.sent == ["sit"] * 3
        wire.add(pose(123, 3))
        agent.tick()
        assert wire.sent == ["sit"] * 3
        wire.add(pose(kind=3))
        agent.tick()
        assert not bool(brain.is_recovering)
        agent.tick()
        assert wire.sent == ["sit"] * 4
        assert brain._rest_hold is not None
        assert brain._rest_hold.version == brain.runtime.lifecycle.version
        assert brain._rest_hold.identity == brain.active_plan.identity
        assert bool(brain.is_recovering)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_no_progress_known_sit_stands_bounded_even_after_basic_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = HandoffModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        now[0] = 30.0
        agent.tick()
        assert wire.sent == ["sit", "stand"]
        assert model.replan_entered.wait(1)
        wire.add(skill_list(row(level=0)))
        for second in (31.0, 32.0, 33.0, 40.0):
            now[0] = second
            agent.tick()
        assert wire.sent == ["sit", "stand", "stand", "stand"]
        assert bool(brain.is_recovering)
        wire.add(pose(kind=3))
        agent.tick()
        assert not bool(brain.is_recovering)
        assert brain.runtime.lifecycle.counters["requests"] == 2
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_stale_pose_and_pending_arrival_cannot_release_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    agent = host.agents["one"]
    client = agent.client
    assert isinstance(client, PlayingClient)
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        wire.add(pose())
        agent.tick()
        vitals(wire, 80, 16)
        agent.tick()
        barrier = brain.stand_barrier
        assert barrier is not None
        # The effect-boundary wire replays an already consumed own standing
        # record; metadata sequence, not the repeated payload, is authority.
        original = wire.frames[-1]
        wire.frames[-1] = (barrier, float(barrier), 0x08C8, pose(kind=3))
        agent.tick()
        assert bool(brain.is_recovering)
        wire.frames[-1] = original
        wire.add(pose(123, 3))
        agent.tick()
        assert bool(brain.is_recovering), (client.planning_rest_observation(), brain._rest_hold)
        client._pending = ((43, 37), client._metadata_cursor, now[0], 1)
        wire.add(pose(kind=3))
        agent.tick()
        assert bool(brain.is_recovering), "standing does not acknowledge pending arrival"
        wire.add(walk_ack((43, 37), (43, 37)))
        agent.tick()
        assert not bool(brain.is_recovering)
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()


def test_zero_max_sp_received_quartet_recovers_without_invented_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = MechanicalRestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 0)
    wire.add(struct.pack("<HHi", 0x00B0, 8, 0))
    wire.status_params[8] = 0
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert wire.sent == ["sit"]
        wire.add(pose())
        wire.add(struct.pack("<HHi", 0x00B0, 5, 80))
        wire.status_params[5] = 80
        agent.tick()
        assert wire.sent == ["sit", "stand"]
        wire.add(pose(kind=3))
        agent.tick()
        assert not bool(brain.is_recovering)
        assert agent.build_state().max_sp == 0
        assert not wire.moves
    finally:
        model.release.set()
        model.replan_release.set()
        host.stop()
