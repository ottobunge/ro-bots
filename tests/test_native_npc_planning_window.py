"""Offline source-shaped ready UI through the real controller and planning path."""

import struct
from dataclasses import replace

import pytest

from robots.app.llm_planner import LlmPlanner
from robots.app.plan_lifecycle import PlanLifecycle
from robots.app.planning_context import ObservationSnapshot
from robots.app.planning_job_context import capture_job_context
from robots.domain.actions import NpcNext, NpcSelect
from robots.domain.model import Goal
from robots.domain.planning import Capabilities, PhaseKind
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.society.memory import MemoryLog, StubSummarizer
from tests.test_llm_planner import ScriptedModel, frame
from tests.test_native_npc_guidance import dialog, opened
from tests.test_npc_bound_response import bound
from tests.test_npc_plan_contract import npc_arguments
from tests.test_npc_planning_observation import forbid_gameplay_effects, identity_for
from tests.test_playing_runtime import map_frame, walk_ack


@pytest.mark.parametrize("operation", ["next", "choose"])
def test_received_ready_ui_survives_bounded_authoring_without_renewing_receipt(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    now = [100.0]
    wire, client = opened(now)
    wire.add(
        dialog(0xB4, "Received guidance"),
        dialog(0xB5 if operation == "next" else 0xB7, "Equipment::Training"),
    )
    identity = identity_for(client)
    forbid_gameplay_effects(monkeypatch, client)
    observation = client.planning_npc_observation(identity)
    assert observation is not None
    state = client.build_native_state(Goal.GRIND)
    capabilities = Capabilities(
        frozenset({PhaseKind.NPC, PhaseKind.IDLE}),
        frozenset({state.map_name}),
        frozenset(),
        observation,
    )
    captured = capture_job_context(
        identity,
        ObservationSnapshot(identity, state, capabilities),
        PublicSkillKnowledge("pre-re", ()),
        MemoryLog(StubSummarizer()),
    )
    assert captured is not None
    arguments = npc_arguments(operation)
    arguments["phases"][0]["npc_intent"].update(
        epoch=observation.epoch,
        map_name=observation.map_name,
        opened_sequence=observation.opened_sequence,
        prompt_sequence=observation.prompt_sequence,
    )
    now[0] = 116.665
    owned = captured.observed_capabilities(identity).npc_observation
    assert owned is not None
    assert owned.eligible(identity, now[0]), "received ready UI expired during bounded authoring"
    assert owned.observed_at == 100.0
    assert owned.expires_at == 130.0
    model = ScriptedModel(
        [frame("investigate", {"topic": "npc"}, "read"), frame("submit_plan", arguments, "plan")]
    )
    lifecycle = PlanLifecycle(identity, lambda: now[0])
    request = lifecycle.request("received guidance")
    assert request is not None
    proposal = LlmPlanner(model, captured, lambda: now[0]).propose(request, captured)
    fresh = client.planning_npc_observation(identity)
    assert fresh is not None
    assert fresh.prompt_sequence == owned.prompt_sequence
    assert fresh.expires_at == owned.expires_at
    assert lifecycle.admit(request, proposal, replace(capabilities, npc_observation=fresh))
    now[0] = 130.0
    assert not owned.eligible(identity, now[0])
    assert client.planning_npc_observation(identity) is None
    assert len(wire.sent) == 1
    assert not wire.moves
    assert client._npc.requests == 1
    assert lifecycle.wait == 5.0
    assert len(model.payloads) == 2


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
@pytest.mark.parametrize("elapsed", [16.665, 29.999, 30.0])
def test_ready_ui_exact_expiry_and_bound_actuation(pid: int, elapsed: float) -> None:

    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(pid, "A::C"))
    identity = identity_for(client)
    observation = client.planning_npc_observation(identity)
    assert observation is not None
    assert observation.expires_at == 30.0
    now[0] = elapsed
    assert observation.eligible(identity, now[0]) is (elapsed < 30.0)
    if elapsed == 30.0:
        wire.add(dialog(pid, "New::Branch"))
    client.perform_native(bound(observation, 3 if pid == 0xB7 else None))
    assert len(wire.sent) == (2 if elapsed < 30.0 else 1)
    assert not wire.moves


@pytest.mark.parametrize("pid", [0xB4, 0xB6, 0xC4, 0x142, 0x1D4])
def test_nonplanning_ui_retains_fifteen_second_budget(pid: int) -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(pid, "Received text"))
    client.build_native_state(Goal.GRIND)
    assert client._npc.deadline == 15.0
    assert client.planning_npc_observation(identity_for(client)) is None
    now[0] = 15.0
    client.build_native_state(Goal.GRIND)
    assert client._npc.failed
    assert len(wire.sent) == 1


@pytest.mark.parametrize("mode", ["query", "foreign", "duplicate", "keepalive"])
def test_without_new_matching_ui_no_deadline_renewal(mode: str) -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    original = client.planning_npc_observation(identity)
    assert original is not None
    now[0] = 20.0
    if mode == "foreign":
        wire.add(dialog(0xB5, npc=999))
    elif mode == "duplicate":
        client._npc.consume(((original.prompt_sequence, 20.0, 0xB5, dialog(0xB5)),), now[0])
    elif mode == "keepalive":
        wire.add(struct.pack("<HI", 0x7F, 123))
    current = client.planning_npc_observation(identity)
    assert current is not None
    assert current.prompt_sequence == original.prompt_sequence
    assert current.expires_at == original.expires_at == 30.0
    assert original.observed_at == 0.0
    assert len(wire.sent) == 1
    now[0] = 30.0
    assert client.planning_npc_observation(identity) is None


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_only_new_prompt_refreshes_deadline_without_reviving_captured_receipt(pid: int) -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(pid, "A::C"))
    identity = identity_for(client)
    old = client.planning_npc_observation(identity)
    assert old is not None
    now[0] = 20.0
    wire.add(dialog(pid, "New::Branch"))
    fresh = client.planning_npc_observation(identity)
    assert fresh is not None
    assert fresh.prompt_sequence > old.prompt_sequence
    assert fresh.expires_at == 50.0
    now[0] = 30.0
    assert not old.eligible(identity, now[0])
    assert fresh.eligible(identity, now[0])
    historical = replace(old, expires_at=15.0)
    assert not historical.eligible(identity, 16.665)
    assert old.expires_at == 30.0
    assert len(wire.sent) == 1


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_malformed_ready_packet_blocks_without_extending_deadline(pid: int) -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    assert client.planning_npc_observation(identity) is not None
    now[0] = 20.0
    malformed = dialog(pid, "A::C") + b"extra" if pid == 0xB5 else dialog(pid, "A::C")[:-1]
    wire.add(malformed)
    assert client.planning_npc_observation(identity) is None
    assert client._npc.failed
    assert client._npc.deadline == 30.0
    assert len(wire.sent) == 1


@pytest.mark.parametrize("operation", ["next", "choose", "cancel"])
def test_sent_response_retains_five_second_timeout(operation: str) -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5 if operation == "next" else 0xB7, "A::C"))
    client.build_native_state(Goal.GRIND)
    now[0] = 2.0
    action = (
        NpcNext(321) if operation == "next" else NpcSelect(321, 255 if operation == "cancel" else 3)
    )
    client.perform_native(action)
    assert client._npc.deadline == 7.0
    assert client._npc.absolute_deadline == 120.0
    now[0] = 7.0
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == ("cancel_abandoned" if operation == "cancel" else "blocked")
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 2


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_opening_exact_five_second_expiry_cannot_be_rescued_by_ready_ui(pid: int) -> None:
    now = [0.0]
    wire, client = opened(now)
    assert client._npc.deadline == 5.0
    now[0] = 5.0
    wire.add(dialog(pid, "A::C"))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert client._npc.failed
    assert client._npc.deadline == 5.0
    assert len(wire.sent) == 1


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_repeated_new_ready_ui_is_capped_by_original_absolute_deadline(pid: int) -> None:
    now = [0.0]
    wire, client = opened(now)
    identity = identity_for(client)
    for received_at in (0.0, 25.0, 50.0, 75.0, 100.0, 119.0):
        now[0] = received_at
        wire.add(dialog(pid, "A::C"))
        observation = client.planning_npc_observation(identity)
        assert observation is not None
        assert observation.expires_at == min(received_at + 30.0, 120.0)
        assert client._npc.absolute_deadline == 120.0
    now[0] = 120.0
    wire.add(dialog(pid, "A::C"))
    assert client.planning_npc_observation(identity) is None
    assert client._npc.deadline == 120.0
    assert client._npc.failed
    assert len(wire.sent) == 1


@pytest.mark.parametrize("boundary", ["warp", "vanish", "epoch", "death", "motion"])
def test_extended_window_does_not_waive_received_invalidation_before_actuation(
    boundary: str,
) -> None:

    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    now[0] = 16.665
    if boundary == "warp":
        wire.add(map_frame())
    elif boundary == "vanish":
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "death":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    else:
        wire.add(walk_ack((42, 37), (43, 37)))
    client.perform_native(bound(observation))
    assert struct.pack("<HI", 0xB9, 321) not in wire.sent
    assert not wire.moves
