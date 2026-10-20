"""Actual-client offline receipts; no host dispatch or native/model effects."""

import json
import struct
from dataclasses import replace
from typing import Any

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.llm_planner import LlmPlanner
from robots.app.plan_lifecycle import PlanLifecycle
from robots.app.planning_context import ObservationSnapshot
from robots.app.planning_job_context import capture_job_context
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcClose, NpcNext, NpcSelect, TalkToNpc
from robots.domain.model import Goal
from robots.domain.planning import Capabilities, NpcObservation, PhaseKind, PlanningIdentity
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.society.memory import MemoryLog, StubSummarizer
from tests.test_llm_planner import ScriptedModel, frame
from tests.test_native_gameplay import actor as actor_frame
from tests.test_native_npc_guidance import dialog, npc_wire, opened
from tests.test_npc_plan_contract import npc_arguments
from tests.test_playing_runtime import map_frame, monster, position, walk_ack


def identity_for(client: PlayingClient) -> PlanningIdentity:
    return PlanningIdentity(
        "npc-pilot", "test", client.wire.char_name, client.wire.native_epoch, "pre-re"
    )


def test_current_next_exact_receipt_without_effects() -> None:
    now = [2.0]
    wire, client = opened(now)
    wire.add(dialog(0xB4, "Received guidance"), dialog(0xB5))
    identity = identity_for(client)
    before = (list(wire.sent), list(wire.moves))
    observation = getattr(client, "planning_npc_observation", lambda _: None)(identity)
    assert (
        observation is not None
    ), "current received NPC prompt has no planning observation producer"
    view = client._npc.view
    assert view is not None
    assert observation == NpcObservation(
        identity,
        321,
        wire.native_epoch,
        wire.map_name,
        view.opened_sequence,
        view.sequence,
        "next",
        (),
        True,
        now[0],
        min(client._npc.deadline, client._npc.absolute_deadline),
    )
    assert observation.identity is identity
    assert (wire.sent, wire.moves) == before


def test_current_menu_preserves_empty_label_indices_without_effects() -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "Equipment::Training"))
    before = (list(wire.sent), list(wire.moves))
    observation = getattr(client, "planning_npc_observation", lambda _: None)(identity_for(client))
    assert observation is not None, "current received NPC menu has no planning observation producer"
    assert observation.stage == "menu"
    assert observation.option_indices == (1, 2, 3)
    assert observation.ready is True
    assert (wire.sent, wire.moves) == before


@pytest.mark.parametrize("pid", [None, 0xB4, 0xB6, 0x1D4, 0x142, 0xC4])
def test_no_receipt_for_nonplanning_ui(pid: int | None) -> None:
    wire, client = opened()
    if pid is not None:
        wire.add(dialog(pid, "Guide"))
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert (wire.sent, wire.moves) == before


@pytest.mark.parametrize("action", [NpcNext(321), NpcClose(321), NpcSelect(321, 255)])
def test_consumed_or_cancel_uncertain_prompt_is_not_ready(action) -> None:
    wire, client = opened()
    pid = 0xB5 if isinstance(action, NpcNext) else 0xB6 if isinstance(action, NpcClose) else 0xB7
    wire.add(dialog(pid, "A::C"))
    client.perform_native(action)
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert (wire.sent, wire.moves) == before


@pytest.mark.parametrize("flag", ["failed", "cancel_uncertain"])
def test_failed_or_uncertain_controller_never_publishes_ready(flag: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    setattr(client._npc, flag, True)
    assert client.planning_npc_observation(identity_for(client)) is None


def test_unsolicited_prompt_is_not_a_dialogue() -> None:
    wire = npc_wire()
    client = PlayingClient(wire, monotonic=lambda: 0.0)
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert not wire.sent


@pytest.mark.parametrize("field", ["character", "session_epoch"])
def test_identity_must_match_exact_current_received_self(field: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    wrong = (
        replace(identity, character=identity.character.lower())
        if field == "character"
        else replace(identity, session_epoch=2)
    )
    assert client.planning_npc_observation(wrong) is None
    assert client.planning_npc_observation(identity) is not None
    assert len(wire.sent) == 1


def test_host_metadata_is_preserved_not_inferred_from_public_rules() -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    identity = replace(
        identity_for(client), agent="other-agent", world="other-world", ruleset="opaque-rule"
    )
    observation = client.planning_npc_observation(identity)
    assert observation is not None
    assert observation.identity is identity


@pytest.mark.parametrize(
    "fault",
    [
        "standing-unknown",
        "sitting",
        "stand-pending",
        "rest-pending",
        "movement-pending",
        "unknown-life",
    ],
)
def test_pure_pose_and_pending_guards_never_send_recovery(fault: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    if fault == "standing-unknown":
        client._standing = None
    elif fault == "sitting":
        client._standing = False
    elif fault == "stand-pending":
        client._stand_pending = (client._metadata_cursor, 0.0, 0.0, 1)
    elif fault == "rest-pending":
        client._rest_seq = client._metadata_cursor
    elif fault == "movement-pending":
        client._pending = ((42, 37), client._metadata_cursor, 0.0, 0)
    else:
        client._authenticated_baseline = False
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert (wire.sent, wire.moves) == before


@pytest.mark.parametrize(
    "fault",
    [
        "running",
        "connected_map",
        "sock",
        "rx_thread",
        "rx_error",
        "closed",
        "keepalive",
        "gap",
        "class_fresh",
        "vitals",
        "selection_epoch",
        "name",
    ],
)
def test_fresh_transport_and_selected_state_denies_unavailable(fault: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    assert client.planning_npc_observation(identity) is not None
    if fault in ("running", "connected_map", "class_fresh"):
        setattr(wire, fault, False)
    elif fault in ("sock", "rx_thread"):
        setattr(wire, fault, None)
    elif fault == "rx_error":
        setattr(wire, fault, "received error")
    elif fault == "closed":
        client._closed = True
    elif fault == "keepalive":
        client._keepalive_failed = True
    elif fault == "gap":
        wire.frames.append((99, 99.0, 0xB5, dialog(0xB5)))
    elif fault == "vitals":
        wire.status_params.pop(8)
    elif fault == "selection_epoch":
        wire.selection_epoch = 2
    else:
        wire.char_name = "Renamed"
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity) is None
    assert (wire.sent, wire.moves) == before
    if fault in (
        "running",
        "connected_map",
        "sock",
        "rx_thread",
        "rx_error",
        "dispatch_errors",
        "closed",
        "keepalive",
        "gap",
    ):
        assert client._npc.view is None
        assert client._encounters is None


@pytest.mark.parametrize(
    "boundary", ["vanish", "reuse", "map", "far", "kind", "death", "motion", "epoch", "replacement"]
)
def test_fresh_received_actor_session_boundaries_deny_stale_prompt(boundary: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    assert client.planning_npc_observation(identity) is not None
    if boundary in ("vanish", "reuse"):
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
        if boundary == "reuse":
            raw = bytearray(monster(kind=6, aid=321))
            raw[59:62] = position(42, 38)
            wire.add(bytes(raw), dialog(0xB5))
    elif boundary == "map":
        wire.add(map_frame(), dialog(0xB5))
    elif boundary in ("far", "kind"):
        raw = bytearray(monster(kind=0 if boundary == "kind" else 6, aid=321))
        raw[59:62] = position(70, 70) if boundary == "far" else position(42, 38)
        wire.add(bytes(raw), dialog(0xB5))
    elif boundary == "death":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1), dialog(0xB5))
    elif boundary == "motion":
        wire.add(walk_ack((42, 37), (43, 37)))
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    else:
        client.wire = npc_wire()
        client.wire.add(dialog(0xB5))
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity) is None
    assert (wire.sent, wire.moves) == before
    assert not client.wire.moves


@pytest.mark.parametrize("kind", [6, 12])
def test_continuous_received_actor_and_matching_arrival_remain_usable(kind: int) -> None:
    wire, client = opened()
    raw = bytearray(monster(kind=kind, aid=321))
    raw[59:62] = position(42, 38)
    wire.add(bytes(raw), walk_ack((42, 37), (42, 37)), dialog(0xB7, "::"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    assert observation.option_indices == (1, 2, 3)
    assert len(wire.sent) == 1


@pytest.mark.parametrize(
    "invalid",
    [True, False, float("nan"), float("inf"), float("-inf"), 10**400, -(10**400), "0", None],
)
def test_invalid_clock_never_reaches_unsafe_controller_math(invalid) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    client._now = lambda: invalid
    before = (list(wire.sent), list(wire.moves))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert (wire.sent, wire.moves) == before


@pytest.mark.parametrize("which", ["deadline", "absolute_deadline"])
@pytest.mark.parametrize("invalid", [0.0, True, float("nan"), float("inf"), 10**400])
def test_existing_expiry_must_be_valid_and_strictly_future(which: str, invalid) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    setattr(client._npc, which, invalid)
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


def test_clock_sample_is_once_and_used_by_consumption_and_receipt() -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    readings = []

    def sample() -> float:
        readings.append(2.0)
        return 2.0

    client._now = sample
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    assert readings == [2.0]
    assert observation.observed_at == 2.0
    assert observation.expires_at == min(client._npc.deadline, client._npc.absolute_deadline)


@pytest.mark.parametrize(
    "origin",
    [
        OSError("clock-origin"),
        KeyboardInterrupt(),
        SystemExit(),
        RuntimeError("unexpected-callback"),
    ],
)
@pytest.mark.parametrize("callback", ["clock", "snapshot", "reader"])
def test_supported_callback_errors_and_controlflow_preserve_origin(
    monkeypatch, origin: BaseException, callback: str
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None

    def fail():
        raise origin

    target = client if callback == "clock" else wire if callback == "snapshot" else wire.rx_thread
    name = (
        "_now"
        if callback == "clock"
        else "native_frame_snapshot" if callback == "snapshot" else "is_alive"
    )
    monkeypatch.setattr(target, name, fail)
    with pytest.raises(type(origin)) as caught:
        client.planning_npc_observation(identity_for(client))
    assert caught.value is origin
    assert caught.value.__traceback__ is not None
    trace = caught.value.__traceback__
    while trace.tb_next is not None:
        trace = trace.tb_next
    assert trace.tb_frame.f_code.co_name == "fail"
    assert len(wire.sent) == 1


@pytest.mark.parametrize("fault", ["requests", "map-name", "indices", "open-sequence"])
def test_ready_receipt_needs_remaining_request_budget_and_exact_valid_binding(fault: str) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "A::C"))
    assert client.planning_npc_observation(identity_for(client)) is not None
    view = client._npc.view
    assert view is not None
    if fault == "requests":
        client._npc.requests = 32
    elif fault == "map-name":
        wire.map_name = "different"
    elif fault == "indices":
        client._npc.view = replace(view, options=((255, "not received"),))
    else:
        client._npc.view = replace(view, opened_sequence=view.sequence)
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


def test_valid_large_clock_and_received_maximum_menu_do_not_get_arbitrary_caps() -> None:
    now = [1e15]
    wire, client = opened(now)
    wire.add(dialog(0xB7, ":" * 253))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    assert observation.option_indices == tuple(range(1, 255))
    assert observation.observed_at == now[0]
    assert observation.expires_at == client._npc.deadline
    now[0] = observation.expires_at
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


def test_selected_name_change_cannot_rebind_old_prompt_to_new_identity() -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    wire.char_name = "AnotherSelectedName"
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


@pytest.mark.parametrize("kind", [6, 12])
def test_walking_npc_denies_even_if_stationary_presentation_follows(kind: int) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    wire.add(actor_frame(0x09FD, 321, kind), actor_frame(0x09FE, 321, kind), dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


@pytest.mark.parametrize("epoch", [True, 0, -1, 1.0, 10**400])
def test_invalid_current_epoch_never_publishes_receipt(epoch: Any) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    identity = identity_for(client)
    assert client.planning_npc_observation(identity) is not None
    wire.native_epoch = epoch
    assert client.planning_npc_observation(identity) is None
    assert len(wire.sent) == 1


def forbid_gameplay_effects(monkeypatch: pytest.MonkeyPatch, client: PlayingClient) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("read-only observation/context/planner/admission reached gameplay effect")

    for method in (
        "_send",
        "move",
        "sit",
        "stand",
        "say",
        "keepalive",
        "party_reply",
        "party_invite",
    ):
        monkeypatch.setattr(client.wire, method, forbidden, raising=False)
    monkeypatch.setattr(client, "_keepalive", forbidden)


@pytest.mark.parametrize("operation", ["next", "choose"])
@pytest.mark.parametrize("drift", ["none", "new-prompt", "close", "vanish", "expiry"])
def test_produced_receipt_enters_unchanged_capture_planner_and_fresh_admission(
    monkeypatch: pytest.MonkeyPatch, operation: str, drift: str
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
    memory = MemoryLog(StubSummarizer())
    snapshot = ObservationSnapshot(identity, state, capabilities)
    captured = capture_job_context(identity, snapshot, PublicSkillKnowledge("pre-re", ()), memory)
    assert captured is not None
    owned = captured.observed_capabilities(identity).npc_observation
    assert owned == observation
    assert owned is not observation
    assert owned.identity is not observation.identity
    response = captured.read(identity, "npc")
    assert response["data"]["dialogue"]["pages"] == ("Received guidance",)
    response["data"]["dialogue"]["pages"] = ("Not received",)
    assert captured.read(identity, "npc")["data"]["dialogue"]["pages"] == ("Received guidance",)
    arguments = npc_arguments(operation)
    arguments["phases"][0]["npc_intent"].update(
        epoch=observation.epoch,
        map_name=observation.map_name,
        opened_sequence=observation.opened_sequence,
        prompt_sequence=observation.prompt_sequence,
    )
    model = ScriptedModel(
        [frame("investigate", {"topic": "npc"}, "read"), frame("submit_plan", arguments, "plan")]
    )
    lifecycle = PlanLifecycle(identity, lambda: now[0])
    request = lifecycle.request("received guidance")
    assert request is not None
    planner = LlmPlanner(model, captured, lambda: now[0])
    proposal = planner.propose(request, captured)
    assert planner.counters == {"model_calls": 2, "investigations": 1}
    assert len(model.payloads) == 2
    advisory = json.loads(model.payloads[0]["messages"][1]["content"])["caller_capabilities"]
    assert advisory["native_action_authorization"] == "UNKNOWN"
    assert advisory["npc_observation"]["prompt_sequence"] == observation.prompt_sequence
    assert advisory["npc_observation"]["available_operation"] == operation
    if drift == "new-prompt":
        wire.add(dialog(0xB5 if operation == "next" else 0xB7, "Equipment::Training"))
    elif drift == "close":
        wire.add(dialog(0xB6))
    elif drift == "vanish":
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
    elif drift == "expiry":
        now[0] = observation.expires_at
    current = replace(capabilities, npc_observation=client.planning_npc_observation(identity))
    assert lifecycle.admit(request, proposal, current) is (drift == "none")
    assert (lifecycle.active is not None) is (drift == "none")
    assert captured.observed_capabilities(identity).npc_observation == observation
    assert memory.notes() == ()
    assert len(wire.sent) == 1
    assert not wire.moves


def test_verified_cached_map_identity_keeps_literal_received_spelling() -> None:
    wire = npc_wire()
    wire.map_name = "prontera.gat"
    raw = bytearray(monster(kind=6, aid=321))
    raw[59:62] = position(42, 38)
    wire.add(struct.pack("<H16sHH", 0x91, b"prontera.gat", 42, 37), bytes(raw))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = PlayingClient(wire, cache=cache, monotonic=lambda: 0.0)
    client.perform_native(TalkToNpc(321))
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    assert observation.map_name == "prontera"
    assert wire.map_name == "prontera.gat"
    assert client._tracker is not None
    assert client._tracker.view.map_name == "prontera.gat"
    view = client._npc.view
    assert view is not None
    assert view.stage == "next"
    assert view.map_name == "prontera"
    assert len(wire.sent) == 1


def _received_gat_prompt(cache: MapCache | None) -> tuple[Any, PlayingClient]:
    wire = npc_wire()
    wire.map_name = "prontera.gat"
    raw = bytearray(monster(kind=6, aid=321))
    raw[59:62] = position(42, 38)
    wire.add(struct.pack("<H16sHH", 0x91, b"prontera.gat", 42, 37), bytes(raw))
    client = PlayingClient(wire, cache=cache, monotonic=lambda: 0.0)
    client.perform_native(TalkToNpc(321))
    wire.add(dialog(0xB5))
    return wire, client


def test_gat_spelling_without_verified_cache_is_not_planning_permission() -> None:
    wire, client = _received_gat_prompt(None)
    assert client.planning_npc_observation(identity_for(client)) is None
    assert wire.map_name == "prontera.gat"
    assert len(wire.sent) == 1


@pytest.mark.parametrize("wire_map", ["unknown.gat", "izlude.gat"])
def test_cached_wire_map_must_match_the_received_view_identity(wire_map: str) -> None:
    cache = MapCache(
        (WalkMap("prontera", 100, 100, bytes(10000)), WalkMap("izlude", 100, 100, bytes(10000)))
    )
    wire, client = _received_gat_prompt(cache)
    assert client.planning_npc_observation(identity_for(client)) is not None
    wire.map_name = wire_map
    assert client.planning_npc_observation(identity_for(client)) is None
    assert client._tracker is not None
    assert client._tracker.view.map_name == "prontera.gat"
    assert len(wire.sent) == 1


def test_backward_clock_is_not_a_ready_receipt() -> None:
    now = [2.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is not None
    now[0] = 1.0
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(wire.sent) == 1


def test_cancel_abandoned_is_not_permission_and_never_recontacts() -> None:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB7, "A::C"))
    client.perform_native(NpcSelect(321, 255))
    now[0] = 6.0
    for _ in range(3):
        assert client.planning_npc_observation(identity_for(client)) is None
    view = client._npc.view
    assert view is not None
    assert view.stage == "cancel_abandoned"
    assert len(wire.sent) == 2


def test_same_epoch_wire_replacement_forgets_old_prompt_and_reopens_fresh() -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    old = client.planning_npc_observation(identity_for(client))
    assert old is not None
    replacement = npc_wire()
    client.wire = replacement
    replacement.add(dialog(0xB5))
    assert client.planning_npc_observation(identity_for(client)) is None
    client.perform_native(TalkToNpc(321))
    replacement.add(dialog(0xB7, "A::C"))
    current = client.planning_npc_observation(identity_for(client))
    assert current is not None
    assert current.stage == "menu"
    assert current.opened_sequence > old.opened_sequence
    assert replacement.sent == [struct.pack("<HIB", 0x90, 321, 1)]
    assert len(wire.sent) == 1


# Revision (criterion-9 live chain): the "dispatch_errors" fault case left the
# deny parametrization — a parse failure no longer denies transport health
# (see tests/test_playing_runtime.py::test_health_survives_historical_dispatch_errors).
