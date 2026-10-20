"""Offline actual host tracer; no live inference or native sessions."""

import json
import struct
import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from robots import playing
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.agent_runtime import AgentHost
from robots.app.llm_planner import PlanningError
from robots.app.planning_brain import PlannedBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import needs_npc_preparation
from robots.domain.actions import GameAction, Loot, MoveTo, TalkToNpc
from robots.domain.model import BotState
from robots.society.memory import ExperienceNote
from tests.test_llm_planner import frame, plan_arguments
from tests.test_llm_planning_host_construction import host_arguments
from tests.test_native_playing_keepalive import KeepaliveWire
from tests.test_playing_runtime import monster


class BlockedModel:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.payloads: list[dict[str, Any]] = []
        self.failure: BaseException | None = None

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(json.loads(json.dumps(payload)))
        if len(self.payloads) == 1:
            self.entered.set()
            assert self.release.wait(5), "test must release provider"
            if self.failure is not None:
                raise self.failure
            return frame("investigate", {"topic": "map"}, "read-1")
        arguments = plan_arguments()
        arguments.update(
            phases=[{"kind": "idle", "map_name": "prontera"}],
            success="wait complete",
            progress="wait complete",
            duration=300,
            review_after=200,
        )
        return frame("submit_plan", arguments, "plan-2")


class SnapshotModel(BlockedModel):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = super().complete(payload)
        round_number = len(self.payloads)
        if round_number == 1:
            return frame("investigate", {"topic": "inventory"}, "inventory-1")
        if round_number == 2:
            return frame("investigate", {"topic": "memory_search"}, "notes-2")
        return response


class RestModel(BlockedModel):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = super().complete(payload)
        if len(self.payloads) == 2:
            return frame("submit_plan", plan_arguments(), "rest-2")
        return response


def test_runtime_snapshot_and_owner_personas_are_isolated_after_host_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosts: list[AgentHost] = []
    models: list[SnapshotModel] = []
    brains: list[PlannedBrain] = []
    try:
        for index in (1, 2):
            model, now = SnapshotModel(), [0.0]
            owner, character = f"owner-{index}", f"Character{index}"
            host, wire, brain = tracer_host(
                tmp_path / owner,
                monkeypatch,
                model,
                now,
                owner=owner,
                world=f"world-{index}",
                character=character,
            )
            hosts.append(host)
            models.append(model)
            brains.append(brain)
            agent = host.agents[owner]
            inventory = {f"captured-item-{index}": index}
            original_state = agent.build_state

            def with_inventory(
                source: Callable[[], BotState] = original_state, items: dict[str, int] = inventory
            ) -> BotState:
                return replace(source(), inventory=items, inventory_known=True)

            monkeypatch.setattr(agent, "build_state", with_inventory)
            brain.memory.log.append(ExperienceNote(0, "other", f"captured-note-{index}"))
            assert agent.connect()
            assert model.entered.wait(1)
            inventory.clear()
            inventory[f"late-item-{index}"] = 99
            brain.memory.log.append(ExperienceNote(1, "other", f"late-note-{index}"))
            wire.status_params[5] = 80
            model.release.set()
            brain.wait_for_worker(1)
            agent.tick()
            assert brain.active_plan is not None
            assert brain.active_plan.identity.agent == owner
            assert brain.active_plan.identity.world == f"world-{index}"
            assert brain.active_plan.identity.character == character
            assert brain.active_plan.identity.ruleset == "pre-re"
            tool_inventory = json.loads(model.payloads[1]["messages"][-1]["content"])
            assert tool_inventory["data"]["rows"] == [
                {"item": f"captured-item-{index}", "quantity": index}
            ]
            notes = json.loads(model.payloads[2]["messages"][-1]["content"])
            assert any(row["snippet"] == f"captured-note-{index}" for row in notes["data"]["rows"])
            encoded = json.dumps(model.payloads)
            assert f"late-item-{index}" not in encoded
            assert f"late-note-{index}" not in encoded
            assert f"captured-item-{3 - index}" not in encoded
            assert f"captured-note-{3 - index}" not in encoded
            for payload in model.payloads:
                captured = json.loads(payload["messages"][1]["content"])["DATA"]["data"]
                assert (captured["name"], captured["map_name"], captured["hp"]) == (
                    character,
                    "prontera",
                    100,
                )
            assert not wire.sent
            assert not wire.moves
        assert brains[0].identity != brains[1].identity
        assert brains[0].memory.log is not brains[1].memory.log
    finally:
        for model in models:
            model.release.set()
        for host in hosts:
            host.stop()


def test_npc_preparation_and_patrol_never_enter_opt_in_mechanical_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for mode in ("npc", "preparation", "patrol"):
        model, now = BlockedModel(), [0.0]
        host, wire, brain = tracer_host(tmp_path / mode, monkeypatch, model, now)
        agent = host.agents["one"]
        client = agent.client
        assert isinstance(client, PlayingClient)
        client.cache = MapCache([WalkMap("prontera", 100, 100, bytes(10000))])
        wire.frames = wire.frames[:2]
        if mode != "patrol":
            wire.add(struct.pack("<HHi", 0x00B0, 24, 0))
        if mode == "npc":
            wire.add(monster(kind=6, aid=345))
        elif mode == "patrol":
            wire.add(struct.pack("<HIHHBhhBBh", 0x0ADD, 321, 501, 0, 1, 42, 37, 0, 0, 3) + bytes(3))
        called: list[str] = []

        def forbidden_fallback(
            state: BotState,
            actions: tuple[GameAction, ...],
            calls: list[str] = called,
            variant: str = mode,
        ) -> tuple[GameAction, ...]:
            calls.append(variant)
            return (MoveTo(43, 37), TalkToNpc(345), Loot())

        monkeypatch.setattr(client, "mechanical_actions", forbidden_fallback)
        try:
            assert agent.connect()
            assert model.entered.wait(1)
            state = agent.build_state()
            assert needs_npc_preparation(state) == (mode != "patrol")
            assert bool([actor for actor in state.nearby if actor.kind == "npc"]) == (mode == "npc")
            for second in (0, 20, 40, 60, 80, 121):
                now[0] = float(second)
                agent.tick()
            assert brain.runtime.lifecycle.pending is None
            brain.runtime.invalidate()
            agent.tick()
            model.release.set()
            brain.wait_for_worker(1)
            agent.tick()
            assert brain.runtime.lifecycle.active is None
            model.payloads.clear()
            brain.request_replan(agent.build_state(), "fresh passive idle")
            brain.wait_for_worker(1)
            agent.tick()
            assert brain.active_plan is not None
            assert wire.keepalives[:4] == [20.0, 40.0, 60.0, 80.0]
            assert called == []
            assert not wire.sent
            assert not wire.moves
        finally:
            model.release.set()
            host.stop()


def test_actual_host_denies_unsupported_rest_under_advertised_idle_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = RestModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(struct.pack("<hh", 0x010F, 4))  # Received partial list grants no sit gate.
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        job = brain.runtime.job
        assert job is not None
        model.release.set()
        brain.wait_for_worker(1)
        assert isinstance(job.error, PlanningError)
        assert job.result is None
        agent.tick()
        assert brain.active_plan is None
        assert brain.planning_status == "planning denied"
        for payload in model.payloads:
            context = json.loads(payload["messages"][1]["content"])
            assert context["caller_capabilities"]["supported"] == ["idle"]
            phase = payload["tools"][1]["function"]["parameters"]["properties"]["phases"]
            assert phase["items"]["properties"]["kind"]["enum"] == ["idle"]
        assert len(model.payloads) == 2
        assert not wire.sent
        assert not wire.moves
    finally:
        model.release.set()
        host.stop()


def tracer_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model: BlockedModel,
    now: list[float],
    *,
    owner: str = "one",
    world: str = "offline-test",
    character: str = "WireNovice",
) -> tuple[AgentHost, KeepaliveWire, PlannedBrain]:
    monkeypatch.setattr(playing, "LocalPlanningModel", lambda *_args, **_kwargs: model)
    argv = host_arguments(tmp_path)
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text())
    data["accounts"][0].update(persona_id=owner, char_name=character)
    manifest.write_text(json.dumps(data))
    host = playing.build_host(
        playing.parse_args(
            [
                *argv,
                "--llm-planning",
                "--planning-world",
                world,
            ]
        )
    )
    agent = host.agents[owner]
    monkeypatch.setattr(agent, "_threaded", False)
    monkeypatch.setattr(agent._tick_clock, "monotonic", lambda: now[0])
    wire = KeepaliveWire(now)
    wire.char_name = character
    wire.add(struct.pack("<HIHHBhhBBh", 0x0ADD, 321, 501, 0, 1, 42, 37, 0, 0, 3) + bytes(3))
    agent.client = PlayingClient(wire, monotonic=lambda: now[0])
    brain = agent.brain
    assert isinstance(brain, PlannedBrain)
    return host, wire, brain


def test_actual_host_pending_provider_keeps_native_ticks_passive_then_admits_idle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = BlockedModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        assert brain.planning_status == "pending"
        for second in (0, 20, 40, 60, 80):
            now[0] = float(second)
            wire.add(monster(aid=123 + second))
            agent.tick()
        assert wire.keepalives == [20.0, 40.0, 60.0, 80.0]
        assert not wire.sent
        assert not wire.moves
        assert brain.current_plan is None
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.active_plan is not None
        assert brain.active_plan.identity.session_epoch == wire.native_epoch
        assert brain.planning_status == "admitted"
        assert len(model.payloads) == 2
        assert model.payloads[1]["messages"][-1]["role"] == "tool"
        assert not wire.sent
        assert not wire.moves
    finally:
        model.release.set()
        host.stop()


@pytest.mark.parametrize("change", ["map", "health", "epoch"])
def test_fresh_host_context_denies_captured_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    model, now = BlockedModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        if change == "map":
            wire.add(struct.pack("<H16sHH", 0x0091, b"izlude", 42, 37))
        elif change == "health":
            wire.status_params.clear()
        else:
            wire.native_epoch = wire.selection_epoch = wire.map_epoch = 3
        agent.tick()
        assert brain.active_plan is None
        assert not wire.sent
        assert not wire.moves
    finally:
        model.release.set()
        host.stop()


def test_logical_timeout_and_epoch_change_retain_same_physical_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = BlockedModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        job = brain.runtime.job
        assert job is not None
        now[0] = 121.0
        agent.tick()
        assert brain.runtime.lifecycle.pending is None
        for reason in range(20):
            brain.request_replan(agent.build_state(), f"reason-{reason}")
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 3
        agent.tick()
        brain.request_replan(agent.build_state(), "epoch changed")
        assert brain.runtime.job is job
        assert len(brain.runtime.lifecycle.reasons) <= 8
        assert len(model.payloads) == 1
        assert not wire.sent
        assert not wire.moves
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        assert brain.reconnect_ready
        assert brain.active_plan is None
    finally:
        model.release.set()
        host.stop()
