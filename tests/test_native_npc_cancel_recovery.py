"""Offline cancel continuation/denial contracts; recovery remains a scoped blocker."""

import struct
from types import SimpleNamespace
from typing import Any, cast

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app import agent_runtime
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import NpcGuidanceScript, ScriptStatus, needs_npc_preparation
from robots.domain.actions import Attack, Loot, MoveTo, NpcNext, NpcSelect, Rest, Say, TalkToNpc
from robots.domain.events import Heartbeat
from robots.domain.model import Goal
from robots.society.models import Attitude, Playstyle, SocietyPersona
from tests.test_native_gameplay import actor as actor_frame
from tests.test_native_npc_guidance import dialog, npc_wire, opened
from tests.test_playing_runtime import Wire, monster, position


class CancelDecision:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return {"answers": {"npc_menu": {"choice": "cancel"}, "change_goal": {"choice": "keep"}}}


def cancel_trace() -> tuple[list[float], Wire, PlayingClient, EventDrivenBrain, CancelDecision]:
    now = [0.0]
    wire = npc_wire()
    client = PlayingClient(wire, monotonic=lambda: now[0])
    model = CancelDecision()
    brain = EventDrivenBrain(model, StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    brain.start(state)
    client.perform_native(brain.step_script(state).actions[0])
    wire.add(dialog(0xB4, "Received guide; no rewards observed."), dialog(0xB7, "A:B:C"))
    state = client.build_native_state(Goal.GRIND)
    actions = tuple(
        a for e in client.drain_native_events() for a in brain.handle_event(state, e).actions
    )
    assert actions == (NpcSelect(321, 255),)
    client.perform_native(actions[0])
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 255)
    observed = client.build_native_state(Goal.GRIND)
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "waiting"
    return now, wire, client, brain, model


def test_silent_cancel_abandons_locally_resumes_cognition_not_actuation():
    now, wire, client, brain, model = cancel_trace()
    now[0] = 5.1
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    observed = state
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "cancel_abandoned"
    assert not client._npc.active
    assert not client._npc.failed
    assert not state.npc_instructions_received
    assert not state.inventory
    assert needs_npc_preparation(state)
    assert NpcGuidanceScript().step(state).status == ScriptStatus.FAILED
    previous = len(model.requests)
    brain.handle_event(state, Heartbeat(seq=1))
    assert len(model.requests) == previous + 1
    wire.add(monster())
    forbidden = (Attack(123), Loot(), MoveTo(43, 37), TalkToNpc(321))
    for _ in range(100):
        state = client.build_native_state(Goal.GRIND)
        outcome = brain.step_script(state)
        assert outcome.status == ScriptStatus.FAILED
        assert outcome.actions == ()
        assert client.mechanical_actions(state, forbidden) == ()
        for action in forbidden:
            client.perform_native(action)
    assert len(wire.sent) == 2
    assert not wire.moves
    client.perform_native(Say("Safe cognition continues."))
    assert wire.sent[-1] == "Safe cognition continues."
    wire.status_params[5] = 10
    assert brain.step_script(client.build_native_state(Goal.GRIND)).actions == (Rest(),)
    client.perform_native(Rest())
    assert wire.sent[-1] == "sit"


def test_cancel_backward_clock_cannot_become_local_abandonment():
    now, wire, client = pending_cancel()
    now[0] = 4.0
    client.build_native_state(Goal.GRIND)
    now[0] = 3.0
    state = client.build_native_state(Goal.GRIND)
    assert client._npc.failed
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "blocked"
    now[0] = 6.0
    observed = client.build_native_state(Goal.GRIND)
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "blocked"
    assert client._npc.active
    assert len(wire.sent) == 2


@pytest.mark.parametrize("pid", [0xB4, 0xB5, 0xB6, 0xB7])
@pytest.mark.parametrize("npc", [321, 999])
def test_abandoned_late_ui_cannot_rearm(pid, npc):
    now, wire, client = pending_cancel()
    now[0] = 5.1
    terminal = client.build_native_state(Goal.GRIND).npc_dialogue
    wire.add(dialog(pid, "Late UI", npc=npc))
    assert client.build_native_state(Goal.GRIND).npc_dialogue == terminal
    client.perform_native(NpcSelect(321, 255))
    client.perform_native(TalkToNpc(321))
    assert len(wire.sent) == 2
    assert client._npc.cancel_uncertain


def test_cancel_uncertainty_survives_map_invalidation_and_actor_id_reuse():
    now, wire, client = pending_cancel()
    now[0] = 5.1
    client.build_native_state(Goal.GRIND)
    wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37), monster(kind=6, aid=321))
    assert client.build_native_state(Goal.GRIND).npc_dialogue is None
    for action in (TalkToNpc(321), Attack(123), Loot(), MoveTo(43, 37)):
        client.perform_native(action)
    assert len(wire.sent) == 2
    assert not wire.moves
    assert client._npc.cancel_uncertain
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    client.build_native_state(Goal.GRIND)
    assert not client._npc.cancel_uncertain


def test_scheduled_cancel_terminal_ticks_keep_send_count_stable():
    now, wire, client, brain, _model = cancel_trace()
    persona = SocietyPersona("cancel", "cancel", Playstyle.MELEE, Attitude.GRINDER, 0.5, (1, 10))
    agent = ScheduledAgent(
        persona,
        ManifestEntry("cancel", "unused", "unused", wire.char_name),
        client=client,
        threaded=False,
    )
    agent.brain = brain
    now[0] = 5.1
    for _ in range(100):
        agent.tick()
    assert len(wire.sent) == 2
    assert not wire.moves
    assert client._npc.cancel_uncertain
    observed = client.build_native_state(Goal.GRIND)
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "cancel_abandoned"


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1.0, True])
def test_invalid_cancel_clock_remains_poison_not_abandonment(invalid):
    now, wire, client = pending_cancel()
    now[0] = invalid
    client.build_native_state(Goal.GRIND)
    now[0] = 6.0
    observed = client.build_native_state(Goal.GRIND)
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "blocked"
    assert client._npc.failed
    assert len(wire.sent) == 2


def test_cancel_wait_respects_original_absolute_budget():
    now = [0.0]
    wire, client = opened(now)
    now[0] = 4.0
    wire.add(dialog(0xB5))
    client.build_native_state(Goal.GRIND)
    for second in range(10, 120, 10):
        now[0] = float(second)
        wire.add(dialog(0xB5))
        client.build_native_state(Goal.GRIND)
    now[0] = 119.0
    wire.add(dialog(0xB7, "A:B"))
    client.perform_native(NpcSelect(321, 255))
    now[0] = 120.0
    observed = client.build_native_state(Goal.GRIND)
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "cancel_abandoned"
    assert client._npc.absolute_deadline == 120.0


def test_malformed_cancel_continuation_cannot_release_actuation_after_map_receipt():
    _, wire, client = pending_cancel()
    wire.add(dialog(0xB4, "bad")[:-1])
    client.build_native_state(Goal.GRIND)
    wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37), monster())
    client.perform_native(Attack(123))
    assert len(wire.sent) == 2
    assert client._npc.cancel_uncertain
    assert client._npc.failed


def pending_cancel() -> tuple[list[float], Wire, PlayingClient]:
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB4, "Received page, not equipment."), dialog(0xB7, "A:B:C"))
    client.perform_native(NpcSelect(321, 255))
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 255)
    return now, wire, client


@pytest.mark.parametrize("pid", [0xB4, 0xB5, 0xB7])
def test_cancel_preserves_received_prompt_continuation(pid):
    now, wire, client = pending_cancel()
    now[0] = 4.9
    wire.add(dialog(pid, "Continuation"))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    observed = state
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == {0xB4: "text", 0xB5: "next", 0xB7: "menu"}[pid]
    assert not state.npc_instructions_received
    assert state.job == "Novice"
    assert state.inventory == {}


@pytest.mark.parametrize("invalid", [True, False, 255.0, "255", 256, -1])
def test_invalid_cancel_does_not_consume_menu(invalid):
    wire, client = opened()
    wire.add(dialog(0xB7, "A:B:C"))
    client.perform_native(NpcSelect(321, cast("int", invalid)))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    observed = state
    assert observed.npc_dialogue is not None
    assert observed.npc_dialogue.stage == "menu"
    assert len(wire.sent) == 1


def test_cancel_repeated_request_never_resends_waiting_stage():
    _, wire, client = pending_cancel()
    for _ in range(4):
        client.perform_native(NpcSelect(321, 255))
        client.perform_native(TalkToNpc(321))
    assert len(wire.sent) == 2
    assert not client.build_native_state(Goal.GRIND).npc_instructions_received


def test_foreign_response_does_not_extend_cancel_window():
    now, wire, client = pending_cancel()
    deadline = client._npc.deadline
    now[0] = 4.9
    wire.add(dialog(0xB5, npc=999))
    client.build_native_state(Goal.GRIND)
    assert client._npc.deadline == deadline
    assert client._npc.presentations == 2


@pytest.mark.parametrize("origin", [OSError("cancel send"), KeyboardInterrupt(), SystemExit()])
def test_cancel_send_failure_retains_exact_origin_and_poison(origin):
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB7, "A:B:C"))

    def fail(raw):
        raise origin

    target: Any = wire
    target._send = fail
    with pytest.raises(type(origin)) as caught:
        client.perform_native(NpcSelect(321, 255))
    assert caught.value is origin
    assert client._npc.failed
    now[0] = 6.0
    client.perform_native(NpcSelect(321, 255))
    assert len(wire.sent) == 1
    assert client._npc.active


@pytest.mark.parametrize("boundary", ["epoch", "map", "actor", "transport", "gap"])
def test_cancel_cannot_cross_received_context_boundary(boundary):
    _, wire, client = pending_cancel()
    if boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37))
    elif boundary == "actor":
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
    elif boundary == "transport":
        wire.running = False
    else:
        wire.frames.append((99, 1.0, 0xB5, dialog(0xB5)))
    if boundary in ("transport", "gap"):
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
    else:
        assert client.build_native_state(Goal.GRIND).npc_dialogue is None
    assert client._npc.view is None
    assert len(wire.sent) == 2


def native_pending_cancel() -> tuple[list[float], Any, PlayingClient]:
    """Actual native dispatcher/snapshot/send facade; no sockets or connections."""
    factory: Any = cast("Any", agent_runtime)._BotClient
    assert factory is not None
    wire = factory("offline", "unused", "WireNovice", verbose=False)
    baseline = npc_wire()
    for name in (
        "aid",
        "gid",
        "native_epoch",
        "selection_epoch",
        "map_epoch",
        "class_fresh",
        "selected_character_snapshot",
        "status_params",
        "running",
        "connected_map",
    ):
        setattr(wire, name, getattr(baseline, name))
    wire.sent = []
    wire.sock = SimpleNamespace(sendall=wire.sent.append)
    wire.rx_thread = SimpleNamespace(is_alive=lambda: True)

    def receive(*raws: bytes) -> None:
        for raw in raws:
            wire._dispatch(int.from_bytes(raw[:2], "little"), raw)

    wire.add = receive
    receive(*(frame[3] for frame in baseline.frames))
    assert wire.sent == [b"\x7d\x00"]  # Actual dispatcher map-entry ACK, not cancellation.
    wire.sent.clear()
    now = [0.0]
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client.perform_native(TalkToNpc(321))
    receive(dialog(0xB4, "Received page, not equipment."), dialog(0xB7, "A:B:C"))
    client.perform_native(NpcSelect(321, 255))
    assert len(wire.sent) == 2
    return now, wire, client


def test_native_actor_vanish_before_continuation_cannot_send_attack():
    now, wire, client = native_pending_cancel()
    now[0] = 4.0
    wire.add(struct.pack("<HIB", 0x80, 321, 0), dialog(0xB5), monster())
    client.build_native_state(Goal.GRIND)
    client.perform_native(Attack(123))
    actual_attack_sent = bytes.fromhex("37047b00000000") in wire.sent
    assert not actual_attack_sent, "actual_attack_sent after NPC disappeared before continuation"
    assert client._npc.cancel_uncertain
    assert len(wire.sent) == 2


@pytest.mark.parametrize("pid", [0xB4, 0xB5, 0xB7])
@pytest.mark.parametrize(
    "boundary", ["reuse", "foreign_then_reuse", "map", "death", "walking", "range"]
)
def test_native_earlier_context_loss_cannot_be_repaired_by_later_ui(pid, boundary):
    now, wire, client = native_pending_cancel()
    now[0] = 4.0
    stationary = actor_frame(0x09FE, 321, 6)
    if boundary in ("reuse", "foreign_then_reuse"):
        if boundary == "foreign_then_reuse":
            wire.add(dialog(pid, "Foreign UI", npc=654))
        wire.add(struct.pack("<HIB", 0x80, 321, 0), stationary)
    elif boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37), stationary)
    elif boundary == "death":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1), struct.pack("<HIH", 0x148, wire.aid, 0))
    elif boundary == "walking":
        wire.add(actor_frame(0x09FD, 321, 6), stationary)
    else:
        distant = bytearray(stationary)
        distant[59:62] = position(80, 80)
        wire.add(bytes(distant), stationary)
    wire.add(dialog(pid, "Later UI cannot invent earlier identity."), monster())
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is None
    assert client._npc.cancel_uncertain
    assert client._npc.presentations == 2
    for _ in range(5):
        for action in (Attack(123), Loot(), MoveTo(43, 37), TalkToNpc(321)):
            client.perform_native(action)
    assert bytes.fromhex("37047b00000000") not in wire.sent
    assert wire.sent == [
        struct.pack("<HIB", 0x90, 321, 1),
        struct.pack("<HIB", 0xB8, 321, 255),
        *([b"\x7d\x00"] if boundary == "map" else []),
    ]
    assert not state.npc_instructions_received


@pytest.mark.parametrize("pid", [0xB4, 0xB5, 0xB7])
@pytest.mark.parametrize("later_vanish", [False, True])
def test_native_continuous_prompt_accepted_before_future_disappearance(pid, later_vanish):
    now, wire, client = native_pending_cancel()
    now[0] = 4.0
    wire.add(struct.pack("<HIB", 0x80, 654, 0), dialog(pid, "Valid continuation"))
    if later_vanish:
        wire.add(struct.pack("<HIB", 0x80, 321, 0))
    state = client.build_native_state(Goal.GRIND)
    assert not client._npc.cancel_uncertain
    assert client._npc.presentations == 3
    # Received NEXT/MENU now allow 30s planning; plain text retains its 15s window.
    assert client._npc.deadline == (19.0 if pid == 0xB4 else 34.0)
    assert client._npc.absolute_deadline == 120.0
    if later_vanish:
        assert state.npc_dialogue is None
    else:
        assert state.npc_dialogue is not None
        assert state.npc_dialogue.stage == {0xB4: "text", 0xB5: "next", 0xB7: "menu"}[pid]
        if pid == 0xB5:
            client.perform_native(NpcNext(321))
            assert wire.sent[-1] == struct.pack("<HI", 0xB9, 321)
    assert not state.npc_instructions_received


@pytest.mark.parametrize("boundary", ["gap", "replay", "epoch"])
def test_native_sequence_boundary_cannot_rearm_old_cancel(boundary):
    now, wire, client = native_pending_cancel()
    now[0] = 5.1
    client.build_native_state(Goal.GRIND)
    if boundary == "gap":
        wire._native_frame_seq += 1
    elif boundary == "replay":
        wire._native_frame_seq -= 1
    else:
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.add(dialog(0xB5))
    if boundary == "gap":
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
    else:
        state = client.build_native_state(Goal.GRIND)
        if boundary == "epoch":
            assert state.npc_dialogue is None
            assert not client._npc.cancel_uncertain  # Fresh native session reset, not UI authority.
        else:
            assert state.npc_dialogue is not None
            assert state.npc_dialogue.stage == "cancel_abandoned"
    if boundary != "epoch":
        assert client._npc.cancel_uncertain
    assert len(wire.sent) == 2


def test_non_cancel_timeout_still_retains_fail_closed_barrier():
    now = [0.0]
    wire, client = opened(now)
    wire.add(dialog(0xB5))
    client.perform_native(NpcNext(321))
    now[0] = 5.1
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "blocked"
    assert client._npc.failed
    assert client._npc.active
