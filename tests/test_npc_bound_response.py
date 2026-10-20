"""Receipt-bound response through actual PlayingClient; offline Wire only."""

import struct
from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from typing import Any

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcClose, NpcRespond, TalkToNpc
from robots.domain.planning import NpcIntent, NpcObservation, NpcOperation, PlanningIdentity
from tests.test_native_gameplay import actor as actor_frame
from tests.test_native_npc_guidance import dialog, npc_wire, opened
from tests.test_npc_planning_observation import _received_gat_prompt, identity_for
from tests.test_playing_runtime import Wire, map_frame, monster, position, walk_ack


@pytest.fixture(autouse=True)
def no_unintended_wire_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("bound reply reached unrelated native/metadata effect")

    for method in (
        "move",
        "sit",
        "stand",
        "say",
        "keepalive",
        "party_reply",
        "party_invite",
        "request_name",
    ):
        monkeypatch.setattr(Wire, method, forbidden, raising=False)


def bound(observation: NpcObservation, index: int | None = None) -> NpcRespond:
    return NpcRespond(
        observation.identity,
        NpcIntent(
            NpcOperation.NEXT if observation.stage == "next" else NpcOperation.CHOOSE,
            observation.npc_id,
            observation.epoch,
            observation.map_name,
            observation.opened_sequence,
            observation.prompt_sequence,
            observation.stage,
            index,
        ),
    )


@pytest.mark.parametrize("index", [1, 2, 3, 254])
def test_choose_exact_received_index_once(index: int) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, ":" * 253))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, index)
    assert isinstance(action.identity, PlanningIdentity)
    client.perform_native(action)
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1), struct.pack("<HIB", 0xB8, 321, index)]
    client.perform_native(action)
    assert len(wire.sent) == 2
    assert not wire.moves
    assert client._npc.requests == 2
    assert client._npc.view is not None
    assert client._npc.view.stage == "waiting"


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_new_prompt_denies_old_action_then_requires_explicit_fresh_action(pid: int) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "Old::Branch"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    old = bound(observation, 3 if pid == 0xB7 else None)
    wire.add(dialog(pid, "New::Branch"))
    client.perform_native(old)
    assert len(wire.sent) == 1
    assert client._npc.requests == 1
    fresh = client.planning_npc_observation(identity_for(client))
    assert fresh is not None
    assert fresh.prompt_sequence > observation.prompt_sequence
    assert client._npc.view is not None
    assert client._npc.view.stage == fresh.stage
    current = bound(fresh, 3 if pid == 0xB7 else None)
    client.perform_native(current)
    assert wire.sent[-1] == (
        struct.pack("<HIB", 0xB8, 321, 3) if pid == 0xB7 else struct.pack("<HI", 0xB9, 321)
    )
    client.perform_native(current)
    wire.add(dialog(pid, "Newest::Branch"))
    client.perform_native(old)
    client.perform_native(current)
    assert len(wire.sent) == 2
    assert not wire.moves


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("epoch", 2),
        ("map_name", "izlude"),
        ("opened_sequence", 3),
        ("prompt_sequence", 6),
        ("expected_stage", "next"),
    ],
)
def test_changed_intent_binding_denies_without_consuming_current_menu(field, value) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    valid = bound(observation, 3)
    stale = replace(valid, intent=replace(valid.intent, **{field: value}))
    client.perform_native(stale)
    assert len(wire.sent) == 1
    assert not client._npc.failed
    assert client._npc.requests == 1
    client.perform_native(valid)
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 3)


@pytest.mark.parametrize("payload", [None, True, {}, "choose", object()])
@pytest.mark.parametrize("field", ["identity", "intent"])
def test_opaque_payload_denied_before_observation_without_poisoning(
    monkeypatch: pytest.MonkeyPatch, field: str, payload: Any
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3)

    def forbidden() -> Any:
        pytest.fail("invalid action payload reached clock/snapshot callback")

    with monkeypatch.context() as patch:
        patch.setattr(client, "_now", forbidden)
        patch.setattr(wire, "native_frame_snapshot", forbidden)
        client.perform_native(replace(action, **{field: payload}))
    assert len(wire.sent) == 1
    assert client._npc.requests == 1
    assert not client._npc.failed
    client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 3)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("npc_id", True),
        ("npc_id", 0),
        ("npc_id", 2**32),
        ("epoch", False),
        ("map_name", None),
        ("map_name", "prontera.gat"),
        ("opened_sequence", -1),
        ("prompt_sequence", "5"),
        ("operation", "choose"),
        ("operation", "close"),
        ("operation", "submit_name"),
        ("operation", object()),
        ("expected_stage", "string_input"),
        ("option_index", None),
        ("option_index", True),
        ("option_index", 0),
        ("option_index", 255),
        ("option_index", 3.0),
        ("option_index", "3"),
    ],
)
def test_malformed_direct_intent_denied_before_observation(
    monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3)
    invalid = replace(action, intent=replace(action.intent, **{field: value}))

    def forbidden() -> float:
        pytest.fail("malformed direct intent reached observation clock")

    with monkeypatch.context() as patch:
        patch.setattr(client, "_now", forbidden)
        client.perform_native(invalid)
    assert not client._npc.failed
    assert client._npc.requests == 1
    client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 3)


def test_invalid_identity_record_reuses_domain_identity_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation)
    identity = replace(action.identity)
    object.__setattr__(identity, "agent", "")

    def forbidden() -> float:
        pytest.fail("invalid identity reached observation clock")

    with monkeypatch.context() as patch:
        patch.setattr(client, "_now", forbidden)
        client.perform_native(replace(action, identity=identity))
    assert not client._npc.failed
    client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HI", 0xB9, 321)


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_qualified_one_clock_one_snapshot_direct_controller_request(
    monkeypatch: pytest.MonkeyPatch, pid: int
) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3 if pid == 0xB7 else None)
    order = []
    snapshot: Callable[[], Any] = wire.native_frame_snapshot
    request = client._npc.request
    send: Callable[[bytes], None] = wire._send

    def clock() -> float:
        order.append("clock")
        assert order == ["clock"]
        return 2.0

    def receive():
        order.append("snapshot")
        return snapshot()

    def controller_request(primitive, now, selected_name=None):
        order.append("request")
        assert now == 2.0
        assert order == ["clock", "snapshot", "request"]
        return request(primitive, now, selected_name)

    def emit(raw):
        order.append("send")
        send(raw)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("bound action reentered state publication or legacy dispatcher")

    monkeypatch.setattr(client, "_now", clock)
    monkeypatch.setattr(wire, "native_frame_snapshot", receive)
    monkeypatch.setattr(client._npc, "request", controller_request)
    monkeypatch.setattr(wire, "_send", emit)
    monkeypatch.setattr(client, "build_native_state", forbidden)
    monkeypatch.setattr(client, "_npc_action", forbidden)
    client.perform_native(action)
    assert order == ["clock", "snapshot", "request", "send"]
    assert client._npc.deadline == 7.0
    assert len(wire.sent) == 2


@pytest.mark.parametrize("fault", ["transport", "vitals", "class", "gap", "closed"])
def test_readiness_loss_denies_without_request_or_exception(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation)
    if fault == "transport":
        wire.running = False
    elif fault == "vitals":
        wire.status_params.pop(8)
    elif fault == "class":
        wire.class_fresh = False
    elif fault == "gap":
        wire.frames.append((99, 99.0, 0xB5, dialog(0xB5)))
    else:
        client._closed = True

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("unavailable observation reached controller request")

    monkeypatch.setattr(client._npc, "request", forbidden)
    client.perform_native(action)
    assert len(wire.sent) == 1
    assert not wire.moves


def _received_boundary(wire: Any, client: PlayingClient, boundary: str, pid: int) -> None:
    if boundary in ("vanish", "reuse"):
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
        if boundary == "reuse":
            raw = bytearray(monster(kind=6, aid=321))
            raw[59:62] = position(42, 38)
            wire.add(bytes(raw), dialog(pid, "A::C"))
    elif boundary == "map":
        wire.add(map_frame(), dialog(pid, "A::C"))
    elif boundary in ("far", "kind"):
        raw = bytearray(monster(kind=0 if boundary == "kind" else 6, aid=321))
        raw[59:62] = position(70, 70) if boundary == "far" else position(42, 38)
        wire.add(bytes(raw), dialog(pid, "A::C"))
    elif boundary == "death":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1), dialog(pid, "A::C"))
    elif boundary == "motion":
        wire.add(walk_ack((42, 37), (43, 37)))
    elif boundary == "walking":
        wire.add(actor_frame(0x09FD, 321, 6), actor_frame(0x09FE, 321, 6), dialog(pid, "A::C"))
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "replacement":
        client.wire = npc_wire()
        client.wire.add(dialog(pid, "A::C"))
    else:
        wire.char_name = "AnotherCharacter"


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
@pytest.mark.parametrize(
    "boundary",
    [
        "vanish",
        "reuse",
        "map",
        "far",
        "kind",
        "death",
        "motion",
        "walking",
        "epoch",
        "replacement",
        "character",
    ],
)
def test_fresh_received_boundary_denies_old_action(boundary: str, pid: int) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3 if pid == 0xB7 else None)
    _received_boundary(wire, client, boundary, pid)
    client.perform_native(action)
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1)]
    assert not wire.moves
    if client.wire is not wire:
        assert not client.wire.sent
        assert not client.wire.moves


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_reopened_dialogue_does_not_reuse_prior_intent(pid: int) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3 if pid == 0xB7 else None)
    wire.add(dialog(0xB6))
    client.perform_native(NpcClose(321))
    client.perform_native(TalkToNpc(321))
    wire.add(dialog(pid, "New::C"))
    before = list(wire.sent)
    client.perform_native(action)
    assert wire.sent == before
    current = client.planning_npc_observation(identity_for(client))
    assert current is not None
    assert current.opened_sequence > observation.opened_sequence
    client.perform_native(bound(current, 3 if pid == 0xB7 else None))
    assert len(wire.sent) == len(before) + 1


@pytest.mark.parametrize(
    "fault",
    [
        "sitting",
        "standing-unknown",
        "stand-pending",
        "rest",
        "pending",
        "unknown-life",
        "failed",
        "uncertain",
        "requests",
        "options",
    ],
)
def test_existing_local_gates_deny_before_controller_request(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB7, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3)
    if fault in ("sitting", "standing-unknown"):
        client._standing = False if fault == "sitting" else None
    elif fault == "stand-pending":
        client._stand_pending = (client._metadata_cursor, 0.0, 0.0, 1)
    elif fault == "rest":
        client._rest_seq = client._metadata_cursor
    elif fault == "pending":
        client._pending = ((42, 37), client._metadata_cursor, 0.0, 0)
    elif fault == "unknown-life":
        client._authenticated_baseline = False
    elif fault == "failed":
        client._npc.failed = True
    elif fault == "uncertain":
        client._npc.cancel_uncertain = True
    elif fault == "requests":
        client._npc.requests = 32
    else:
        view = client._npc.view
        assert view is not None
        client._npc.view = replace(view, options=((1, "A"), (2, "")))

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("existing readiness gate reached controller request")

    monkeypatch.setattr(client._npc, "request", forbidden)
    client.perform_native(action)
    assert len(wire.sent) == 1
    assert not wire.moves


@pytest.mark.parametrize(
    "clock", [True, None, "2", float("nan"), float("inf"), 10**400, -(10**400)]
)
def test_invalid_clock_denies_without_unsafe_math(clock: Any) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    client._now = lambda: clock
    client.perform_native(bound(observation))
    assert len(wire.sent) == 1


@pytest.mark.parametrize("which", ["deadline", "absolute_deadline"])
@pytest.mark.parametrize("deadline", [0.0, True, float("nan"), float("inf"), 10**400])
def test_invalid_or_expired_deadline_denies(which: str, deadline: Any) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    setattr(client._npc, which, deadline)
    client.perform_native(bound(observation))
    assert len(wire.sent) == 1


def test_exact_expiry_and_backward_clock_deny() -> None:
    now = [2.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    now[0] = observation.expires_at
    client.perform_native(bound(observation))
    now[0] = 1.0
    client.perform_native(bound(observation))
    assert len(wire.sent) == 1


def _assert_origin(caught: BaseException, origin: BaseException) -> None:
    assert caught is origin
    trace = caught.__traceback__
    assert trace is not None
    while trace.tb_next is not None:
        trace = trace.tb_next
    assert trace.tb_frame.f_code.co_name == "fail"


@pytest.mark.parametrize(
    "origin",
    [
        OSError("send"),
        RuntimeError("send"),
        KeyboardInterrupt(),
        SystemExit(),
        BaseException("send"),
    ],
)
@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_send_failure_preserves_origin_failed_state_and_never_resends(
    monkeypatch: pytest.MonkeyPatch, origin: BaseException, pid: int
) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation, 3 if pid == 0xB7 else None)
    attempts = []

    def fail(raw):
        attempts.append(raw)
        raise origin

    monkeypatch.setattr(wire, "_send", fail)
    with pytest.raises(type(origin)) as caught:
        client.perform_native(action)
    _assert_origin(caught.value, origin)
    assert attempts == [
        struct.pack("<HI", 0xB9, 321) if pid == 0xB5 else struct.pack("<HIB", 0xB8, 321, 3)
    ]
    assert client._npc.failed
    assert client._npc.requests == 2
    assert client._npc.view is not None
    assert client._npc.view.stage == "waiting"
    client.perform_native(action)
    wire.add(dialog(pid, "New::C"))
    client.perform_native(action)
    assert client.planning_npc_observation(identity_for(client)) is None
    assert len(attempts) == 1
    assert len(wire.sent) == 1
    assert not wire.moves


@pytest.mark.parametrize("callback", ["clock", "snapshot", "reader"])
@pytest.mark.parametrize(
    "origin",
    [
        OSError("callback"),
        RuntimeError("callback"),
        KeyboardInterrupt(),
        SystemExit(),
        BaseException("callback"),
    ],
)
def test_unexpected_callback_exception_keeps_exact_controlflow_origin(
    monkeypatch: pytest.MonkeyPatch, callback: str, origin: BaseException
) -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None

    def fail():
        raise origin

    target = client if callback == "clock" else wire if callback == "snapshot" else wire.rx_thread
    method = (
        "_now"
        if callback == "clock"
        else "native_frame_snapshot" if callback == "snapshot" else "is_alive"
    )
    monkeypatch.setattr(target, method, fail)
    with pytest.raises(type(origin)) as caught:
        client.perform_native(bound(observation))
    _assert_origin(caught.value, origin)
    assert len(wire.sent) == 1
    assert client._npc.requests == 1


def test_response_record_is_frozen_slotted_and_has_no_operation_or_text_fields() -> None:
    wire, client = opened()
    wire.add(dialog(0xB5))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    action = bound(observation)
    assert [field.name for field in fields(action)] == ["identity", "intent"]
    assert not hasattr(action, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(action, fields(action)[0].name, identity_for(client))


def test_verified_cached_gat_map_responds_without_rewriting_received_names() -> None:
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    wire, client = _received_gat_prompt(cache)
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    client.perform_native(bound(observation))
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1), struct.pack("<HI", 0xB9, 321)]
    assert wire.map_name == "prontera.gat"
    assert client._tracker is not None
    assert client._tracker.view.map_name == "prontera.gat"


@pytest.mark.parametrize("change", ["removed-cache", "unknown-map", "no-cache"])
def test_map_cache_qualification_loss_denies_response(change: str) -> None:
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    wire, client = _received_gat_prompt(cache)
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    if change == "removed-cache":
        client.cache = MapCache(())
    elif change == "unknown-map":
        wire.map_name = "unknown.gat"
    else:
        client.cache = None
    client.perform_native(bound(observation))
    assert len(wire.sent) == 1


@pytest.mark.parametrize("pid", [0xB5, 0xB7])
def test_boundary_reopen_requires_fresh_explicit_action_after_epoch_or_wire_reset(pid: int) -> None:
    wire, client = opened()
    wire.add(dialog(pid, "A::C"))
    observation = client.planning_npc_observation(identity_for(client))
    assert observation is not None
    old = bound(observation, 3 if pid == 0xB7 else None)
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    client.perform_native(old)
    client.perform_native(TalkToNpc(321))
    wire.add(dialog(pid, "Epoch::C"))
    client.perform_native(old)
    assert len(wire.sent) == 2
    fresh = client.planning_npc_observation(identity_for(client))
    assert fresh is not None
    client.perform_native(bound(fresh, 3 if pid == 0xB7 else None))
    replacement = npc_wire()
    replacement.add(dialog(pid, "Unsolicited"))
    client.wire = replacement
    client.perform_native(old)
    client.perform_native(TalkToNpc(321))
    replacement.add(dialog(pid, "Replacement::C"))
    client.perform_native(old)
    assert len(replacement.sent) == 1
    fresh = client.planning_npc_observation(identity_for(client))
    assert fresh is not None
    client.perform_native(bound(fresh, 3 if pid == 0xB7 else None))
    assert len(replacement.sent) == 2
