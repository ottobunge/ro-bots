"""Selected-name input through actual PlayingClient and offline received Wire."""

import struct
from dataclasses import fields
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcClose, NpcSelect, NpcSubmitName, TalkToNpc
from robots.domain.model import Goal
from tests.test_native_npc_guidance import dialog, npc_wire, opened
from tests.test_playing_runtime import map_frame, monster, position, walk_ack


def current_prompt(client: PlayingClient) -> NpcSubmitName:
    prompt = client.build_native_state(Goal.GRIND).npc_dialogue
    assert prompt is not None
    return NpcSubmitName(prompt.npc_id, prompt.epoch, prompt.sequence)


def test_explicit_current_prompt_sends_exact_selected_name_once():
    wire, client = opened()
    wire.char_name = " MiXeD 雪 "
    wire.add(dialog(0x01D4))
    action = current_prompt(client)
    assert len(wire.sent) == 1
    client.perform_native(action)
    value = wire.char_name.encode("utf-8")
    assert wire.sent == [
        struct.pack("<HIB", 0x90, 321, 1),
        struct.pack("<HHI", 0x1D5, 8 + len(value), 321) + value,
    ]
    client.perform_native(action)
    assert len(wire.sent) == 2
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "waiting"
    assert not state.inventory
    assert state.base_level == 10


def test_name_action_cannot_carry_arbitrary_text():
    assert [field.name for field in fields(NpcSubmitName)] == ["npc_id", "epoch", "prompt_sequence"]
    constructor: Any = NpcSubmitName
    with pytest.raises(TypeError):
        constructor(321, 1, 5, "arbitrary")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("npc_id", 999),
        ("npc_id", True),
        ("npc_id", 321.0),
        ("epoch", 0),
        ("epoch", True),
        ("epoch", 1.0),
        ("prompt_sequence", 4),
        ("prompt_sequence", True),
        ("prompt_sequence", 5.0),
    ],
)
def test_action_is_bound_to_plain_current_prompt_identifiers(field, value):
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    args = {item.name: getattr(action, item.name) for item in fields(action)}
    args[field] = value
    client.perform_native(NpcSubmitName(**args))
    assert len(wire.sent) == 1
    client.perform_native(action)
    assert len(wire.sent) == 2


def test_new_prompt_rejects_old_action_and_requires_new_explicit_intent():
    wire, client = opened()
    wire.add(dialog(0x1D4))
    old = current_prompt(client)
    wire.add(dialog(0x1D4))
    client.perform_native(old)
    assert len(wire.sent) == 1
    current = current_prompt(client)
    client.perform_native(current)
    client.perform_native(current)
    assert len(wire.sent) == 2
    wire.add(dialog(0x1D4))
    client.perform_native(current)
    assert len(wire.sent) == 2
    client.perform_native(current_prompt(client))
    assert len(wire.sent) == 3


@pytest.mark.parametrize("name", ["", "\ud800", "a" * 24, "雪" * 8, "x\0y", b"bytes", None])
def test_invalid_current_selected_name_is_denied_without_send(name):
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    target: Any = wire
    target.char_name = name
    client.perform_native(action)
    assert len(wire.sent) == 1
    wire.char_name = "Valid"
    client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HHI", 0x1D5, 13, 321) + b"Valid"


@pytest.mark.parametrize("name", ["a" * 23, "雪" * 7 + "Ab", " Space CASE 雪 "])
def test_current_name_valid_bytes_are_never_truncated_or_normalized(name):
    wire, client = opened()
    wire.char_name = "Previous"
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    wire.char_name = name
    client.perform_native(action)
    value = name.encode("utf-8")
    assert wire.sent[-1] == struct.pack("<HHI", 0x1D5, 8 + len(value), 321) + value


@pytest.mark.parametrize("request_now", [float("nan"), float("inf"), -1.0, True, 15.0, 10**1000])
def test_fresh_finite_clock_and_deadline_are_checked_at_name_request(request_now):
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        return 0.0 if calls == 1 else request_now

    client._now = clock
    client.perform_native(action)
    assert len(wire.sent) == 1
    assert client._npc.failed
    client._now = lambda: 0.0
    client.perform_native(action)
    assert len(wire.sent) == 1


@pytest.mark.parametrize(("pid", "stage"), [(0x1D4, "string_input"), (0x142, "unsupported_input")])
def test_input_ui_can_be_deliberately_closed_without_name_or_reward(pid, stage):
    wire, client = opened()
    wire.add(dialog(pid))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == stage
    action = current_prompt(client)
    if pid == 0x142:
        client.perform_native(action)
    assert len(wire.sent) == 1
    client.perform_native(NpcClose(321))
    assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
    client.perform_native(action)
    client.perform_native(NpcClose(321))
    assert len(wire.sent) == 2
    assert not client.build_native_state(Goal.GRIND).inventory


@pytest.mark.parametrize(
    "guard", ["map", "epoch", "vanish", "reuse", "death", "sit", "motion", "transport", "gap"]
)
def test_name_request_preserves_actual_client_received_safety_guards(guard):
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    if guard == "map":
        wire.add(map_frame())
    elif guard == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif guard in ("vanish", "reuse"):
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
        if guard == "reuse":
            raw = bytearray(monster(kind=6, aid=321))
            raw[59:62] = position(42, 38)
            wire.add(bytes(raw), dialog(0x1D4))
    elif guard == "death":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    elif guard == "sit":
        raw = bytearray(34)
        struct.pack_into("<HII", raw, 0, 0x8C8, wire.aid, 0)
        raw[29] = 2
        wire.add(bytes(raw))
    elif guard == "motion":
        wire.add(walk_ack((42, 37), (43, 37)))
    elif guard == "transport":
        wire.running = False
    else:
        wire.frames.append((9, 9.0, 0x1D4, dialog(0x1D4)))
    if guard in ("transport", "gap"):
        with pytest.raises(NativeTelemetryUnavailable):
            client.perform_native(action)
        assert client._npc.view is None
    else:
        client.perform_native(action)
    assert len(wire.sent) == 1


def test_name_request_limit_is_shared_and_never_reset_by_new_prompts():
    wire, client = opened()
    for _ in range(31):
        wire.add(dialog(0x1D4))
        client.perform_native(current_prompt(client))
    assert len(wire.sent) == 32
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    client.perform_native(action)
    client.perform_native(action)
    wire.add(dialog(0x1D4))
    client.perform_native(action)
    assert len(wire.sent) == 32
    assert client._npc.failed


def test_name_prompt_expires_before_action_and_later_frames_cannot_rearm():
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    now[0] = 15.0
    wire.add(dialog(0x1D4))
    client.perform_native(action)
    assert len(wire.sent) == 1
    assert client._npc.failed


def test_name_send_failure_preserves_origin_and_never_retries_or_claims_success():
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    origin = OSError("offline name send failed")
    attempts = []

    def fail(raw):
        attempts.append(raw)
        raise origin

    target: Any = wire
    target._send = fail
    with pytest.raises(OSError, match="offline name send failed") as error:
        client.perform_native(action)
    assert error.value is origin
    assert client._npc.failed
    client.perform_native(action)
    wire.add(dialog(0x1D4), dialog(0xB6))
    client.perform_native(action)
    state = client.build_native_state(Goal.GRIND)
    assert len(attempts) == 1
    assert len(wire.sent) == 1
    assert not state.inventory
    assert not state.npc_instructions_received


def test_successful_send_waits_for_actual_next_server_stage_without_reward():
    wire, client = opened()
    wire.add(dialog(0x1D4))
    client.perform_native(current_prompt(client))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "waiting"
    wire.add(dialog(0xB4, "Received continuation"), dialog(0xB5))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "next"
    assert state.npc_dialogue.pages == ("Received continuation",)
    assert len(wire.sent) == 2
    assert not state.inventory
    assert not state.npc_instructions_received


@pytest.mark.parametrize("raw", [dialog(0x1D4)[:-1], dialog(0x1D4) + b"\0"])
def test_malformed_received_string_prompt_never_authorizes_a_name(raw):
    wire, client = opened()
    wire.add(raw)
    client.perform_native(current_prompt(client))
    assert len(wire.sent) == 1
    assert client._npc.failed


def test_foreign_prompt_never_supplies_matching_name_intent():
    wire, client = opened()
    wire.add(dialog(0x1D4, npc=0xFFFFFFFF))
    client.perform_native(current_prompt(client))
    assert len(wire.sent) == 1
    assert client._npc.view is not None
    assert client._npc.view.stage == "opening"


def test_later_nonstring_stage_and_menu_cancel_never_accept_old_name_action():
    wire, client = opened()
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    wire.add(dialog(0xB7, "One:Two"))
    client.perform_native(action)
    assert len(wire.sent) == 1
    client.perform_native(NpcSelect(321, 255))
    client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 255)
    assert len(wire.sent) == 2
    wire.add(dialog(0x1D4))
    client.perform_native(action)
    assert len(wire.sent) == 2
    client.perform_native(current_prompt(client))
    assert len(wire.sent) == 3


def test_absolute_conversation_deadline_cannot_be_extended_by_prompts():
    now = [0.0]
    wire, client = opened(now)
    for moment in range(0, 120, 8):
        now[0] = float(moment)
        wire.add(dialog(0x1D4))
        action = current_prompt(client)
    now[0] = 120.0
    wire.add(dialog(0x1D4))
    client.perform_native(action)
    assert len(wire.sent) == 1
    assert client._npc.failed


def test_received_prompt_never_causes_brain_or_mechanical_autoanswer():
    wire, client = opened()
    wire.add(dialog(0x1D4))
    state = client.build_native_state(Goal.GRIND)
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    brain.start(state)
    assert brain.step_script(state).actions == ()
    assert client.mechanical_actions(state, ()) == ()
    assert len(wire.sent) == 1


def test_high_prompt_id_requires_a_current_received_npc_actor():
    wire = npc_wire()
    npc_id = 0xFFFFFFFF
    raw = bytearray(monster(kind=6, aid=npc_id))
    raw[59:62] = position(42, 38)
    wire.add(bytes(raw))
    client = PlayingClient(wire, monotonic=lambda: 0.0)
    client.perform_native(TalkToNpc(npc_id))
    wire.add(dialog(0x1D4, npc=npc_id))
    action = current_prompt(client)
    assert action.npc_id == npc_id
    client.perform_native(action)
    value = wire.char_name.encode("utf-8")
    assert wire.sent[-1] == struct.pack("<HHI", 0x1D5, 8 + len(value), npc_id) + value


def test_unsolicited_name_action_has_no_prompt_authority():
    wire = npc_wire()
    wire.add(dialog(0x1D4))
    client = PlayingClient(wire, monotonic=lambda: 0.0)
    client.perform_native(NpcSubmitName(321, 1, 5))
    assert not wire.sent
    assert client._npc.view is None
    client.perform_native(TalkToNpc(321))
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1)]


def test_stale_name_action_never_revives_a_deliberately_closed_ui():
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0x1D4))
    action = current_prompt(client)
    client.perform_native(NpcClose(321))
    now[0] = 20.0
    client.perform_native(action)
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "close_requested"
    assert not client._npc.failed
    assert len(wire.sent) == 2
