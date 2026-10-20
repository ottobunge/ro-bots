"""Offline vertical NPC guidance through received frames, brain and native sends."""

import struct
from dataclasses import replace
from typing import Any, cast

import httpx
import pytest

from robots.adapters import playing_backends
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import (
    Attack,
    Loot,
    MoveTo,
    NpcClose,
    NpcNext,
    NpcSelect,
    Rest,
    TalkToNpc,
)
from robots.domain.events import DamageTaken, MonsterSpotted, NpcDialogueReceived
from robots.domain.model import ActorRef, Goal
from robots.society.memory import Memory, StubSummarizer
from tests.test_playing_runtime import Wire, entry, map_frame, monster, position, walk_ack


def npc_wire() -> Wire:
    wire = Wire()
    wire.frames = []
    raw = bytearray(monster(kind=6, aid=321))
    raw[59:62] = position(42, 38)
    wire.add(entry(), map_frame(), bytes(raw), struct.pack("<HHi", 0x00B0, 24, 0))
    return wire


def dialog(pid: int, text: str = "", npc: int = 321) -> bytes:
    if pid in (0xB4, 0xB7):
        body = text.encode("utf-8") + b"\0"
        return struct.pack("<HHI", pid, 8 + len(body), npc) + body
    return struct.pack("<HI", pid, npc)


def field_map() -> bytes:
    """prt_fild08 map receipt: the real fixture field.

    The shared ``map_frame()`` stages prontera, but a spent Novice standing
    in town is the merchant return legs' exact claim (window 30): with no
    sellables, no zeny and no weapon the goal script walks home to the
    field instead of attacking. These guidance scenes grind on the field,
    where the drive and the return never fire and the attack contracts
    stay byte-identical.
    """
    return struct.pack("<H16sHH", 0x0091, b"prt_fild08", 42, 37)


def test_empty_native_novice_brain_talk_receives_instructions():
    wire = npc_wire()
    client = PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    assert [(a.id, a.kind, a.distance) for a in state.nearby] == [(321, "npc", 1.0)]
    brain = EventDrivenBrain(
        ScriptedDecisionModel({"change_goal": {"choice": "keep"}}), StaticChatGenerator()
    )
    wire.add(struct.pack("<HII24s24s", 0x0ADF, 321, 0, b"Received Guide", b""))
    state = client.build_native_state(Goal.GRIND)
    assert state.nearby[0].name == "Received Guide"
    brain.start(state)
    actions = brain.step_script(state).actions
    assert len(actions) == 1
    assert type(actions[0]).__name__ == "TalkToNpc"
    client.perform_native(actions[0])
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1)]
    wire.add(dialog(0xB4, "[Guide] Please speak to the trainer before fighting."), dialog(0xB5))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.pages[-1].endswith("before fighting.")
    assert state.goal == Goal.GRIND
    assert not state.inventory


class MenuDecision:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return {"answers": {"npc_menu": {"choice": "3"}, "change_goal": {"choice": "keep"}}}


def test_next_menu_clef_original_index_and_close_pipeline():
    wire = npc_wire()
    client = PlayingClient(wire)
    model = MenuDecision()
    brain = EventDrivenBrain(model, StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    brain.start(state)
    client.perform_native(brain.step_script(state).actions[0])
    wire.add(dialog(0xB4, "[Guide] Ask me how to prepare."), dialog(0xB5))
    state = client.build_native_state(Goal.GRIND)
    next_actions = brain.step_script(state).actions
    assert len(next_actions) == 1
    assert type(next_actions[0]).__name__ == "NpcNext"
    client.perform_native(next_actions[0])
    client.perform_native(next_actions[0])
    assert wire.sent[-1] == struct.pack("<HI", 0xB9, 321)
    assert len(wire.sent) == 2
    wire.add(dialog(0xB7, "Equipment::Training"))
    state = client.build_native_state(Goal.GRIND)
    events = client.drain_native_events()
    actions = tuple(a for e in events for a in brain.handle_event(state, e).actions)
    assert len(actions) == 1
    assert type(actions[0]).__name__ == "NpcSelect"
    request = model.requests[-1]
    assert set(request["questions"]) == {"npc_menu"}
    assert request["questions"]["npc_menu"]["criteria"] == {
        "1": "Equipment",
        "2": "",
        "3": "Training",
        "cancel": "Cancel this menu (255).",
    }
    assert request["state"]["npc_dialogue"]["pages"] == ["[Guide] Ask me how to prepare."]
    client.perform_native(actions[0])
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 3)
    wire.add(dialog(0xB4, "Defeat a Poring, then return."), dialog(0xB6))
    state = client.build_native_state(Goal.GRIND)
    close_actions = brain.step_script(state).actions
    assert len(close_actions) == 1
    assert type(close_actions[0]).__name__ == "NpcClose"
    client.perform_native(close_actions[0])
    assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
    assert not client.build_native_state(Goal.GRIND).inventory


def opened(now: list[float] | None = None) -> tuple[Wire, PlayingClient]:
    wire = npc_wire()
    client = PlayingClient(wire, monotonic=(lambda: now[0]) if now is not None else (lambda: 0.0))
    client.perform_native(TalkToNpc(321))
    return wire, client


def test_current_actor_vanish_invalidates_next():
    wire, client = opened()
    wire.add(dialog(0xB5), struct.pack("<HIB", 0x80, 321, 0))
    client.perform_native(NpcNext(321))
    assert len(wire.sent) == 1
    assert client.build_native_state(Goal.GRIND).npc_dialogue is None


def test_map_receipt_invalidates_old_dialogue():
    wire, client = opened()
    wire.add(dialog(0xB5), map_frame())
    client.perform_native(NpcNext(321))
    assert len(wire.sent) == 1
    assert client.build_native_state(Goal.GRIND).npc_dialogue is None


def test_distance_change_invalidates_dialogue():
    wire, client = opened()
    wire.add(dialog(0xB5), struct.pack("<H16sHH", 0x91, b"prontera", 80, 80))
    client.perform_native(NpcNext(321))
    assert len(wire.sent) == 1


def test_dead_actor_cannot_click_and_zero_sp_can():
    wire = npc_wire()
    wire.status_params[7] = 0
    client = PlayingClient(wire)
    client.perform_native(TalkToNpc(321))
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1)]
    wire.add(struct.pack("<HIB", 0x80, wire.aid, 1), dialog(0xB5))
    client.perform_native(NpcNext(321))
    assert len(wire.sent) == 1
    assert client.build_native_state(Goal.GRIND).npc_dialogue is None


def test_epoch_resets_conversation_and_transport_invalidates():
    wire, client = opened()
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    assert client.build_native_state(Goal.GRIND).npc_dialogue is None
    client.perform_native(TalkToNpc(321))
    wire.running = False
    with pytest.raises(Exception, match="transport unavailable"):
        client.perform_native(NpcNext(321))
    assert client._npc.view is None


def test_frame_gap_invalidates_dialogue():
    wire, client = opened()
    wire.frames.append((9, 9.0, 0xB5, dialog(0xB5)))
    with pytest.raises(Exception, match="continuity unavailable"):
        client.build_native_state(Goal.GRIND)
    assert client._npc.view is None


def test_sends_are_stage_gated_indices_never_renumbered():
    wire, client = opened()
    client.perform_native(NpcNext(321))
    wire.add(dialog(0xB7, "A::C"))
    for invalid in (0, -1, 4, True, 3.0, "3"):
        client.perform_native(NpcSelect(321, cast("int", invalid)))
    client.perform_native(NpcSelect(999, 3))
    assert len(wire.sent) == 1
    client.perform_native(NpcSelect(321, 2))
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 2)
    client.perform_native(NpcSelect(321, 2))
    assert len(wire.sent) == 2
    wire.add(dialog(0xB7, "A::C"))
    client.perform_native(NpcSelect(321, 255))
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 255)


def test_foreign_and_unsolicited_dialogue_cannot_install_state():
    wire, client = opened()
    wire.add(dialog(0xB4, "Not our guide", npc=999), dialog(0xB5, npc=999))
    observed = client.build_native_state(Goal.GRIND).npc_dialogue
    assert observed is not None
    assert observed.pages == ()
    client.perform_native(NpcNext(999))
    assert len(wire.sent) == 1
    other = PlayingClient(npc_wire())
    other.wire.add(dialog(0xB4, "Unsolicited"))
    assert other.build_native_state(Goal.GRIND).npc_dialogue is None


def test_active_dialog_suppresses_retained_combat_motion_loot_but_rest_survives():
    wire, client = opened()
    wire.add(monster())
    for action in (Attack(123), MoveTo(43, 37), Loot(), TalkToNpc(321)):
        client.perform_native(action)
    assert len(wire.sent) == 1
    assert not wire.moves
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    assert brain.step_script(state).actions == ()
    hurt = replace(state, hp=10)
    assert brain.step_script(hurt).actions == (Rest(),)
    client.perform_native(Rest())
    assert wire.sent[-1] == "sit"


def test_getters_no_sends_and_close_button_not_reward():
    wire, client = opened()
    wire.add(dialog(0xB4, "Talk to the trainer."), dialog(0xB6))
    for _ in range(3):
        state = client.build_native_state(Goal.GRIND)
    assert len(wire.sent) == 1
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "close"
    assert state.inventory_known
    assert state.inventory == {}
    assert state.base_level == 10
    client.perform_native(NpcClose(321))
    client.perform_native(NpcClose(321))
    assert len(wire.sent) == 2
    observed = client.build_native_state(Goal.GRIND).npc_dialogue
    assert observed is not None
    assert observed.stage == "close_requested"


def test_opening_timeout_and_send_origin_poison_no_repeat():
    now = [0.0]
    wire, client = opened(now)
    now[0] = 6.0
    client.perform_native(TalkToNpc(321))
    assert len(wire.sent) == 1
    observed = client.build_native_state(Goal.GRIND).npc_dialogue
    assert observed is not None
    assert observed.stage == "blocked"
    wire = npc_wire()
    origin = OSError("synthetic send origin")

    def fail(raw):
        raise origin

    target: Any = wire
    target._send = fail
    client = PlayingClient(wire)
    with pytest.raises(OSError, match="synthetic send origin") as error:
        client.perform_native(TalkToNpc(321))
    assert error.value is origin
    client.perform_native(TalkToNpc(321))


def test_received_instructions_private_memory_reaches_clef_once():
    wire, client = opened()
    memory = Memory(StubSummarizer(max_chars=1000))
    peer_memory = Memory(StubSummarizer())
    model = MenuDecision()
    brain = EventDrivenBrain(model, StaticChatGenerator(), memory=memory)
    wire.add(dialog(0xB4, "Guide: defeat a Poring then return."), dialog(0xB7, "Help::Training"))
    state = client.build_native_state(Goal.GRIND)
    event = next(e for e in client.drain_native_events() if isinstance(e, NpcDialogueReceived))
    first = brain.handle_event(state, event)
    assert first.actions == (NpcSelect(321, 3),)
    assert "defeat a Poring then return" in model.requests[-1]["state"]["memory_view"]
    assert "epoch=1" in memory.view()[0]
    assert "NPC#321" in memory.view()[0]
    assert memory.log.notes()[0].kind == "npc_dialogue"
    assert not peer_memory.view()
    assert brain.handle_event(state, event).actions == ()
    assert len(memory.log) == 1


def test_guidance_does_not_restart_forever_after_received_instruction_close():
    wire, client = opened()
    wire.add(dialog(0xB4, "Defeat a Poring then return."), dialog(0xB6))
    client.perform_native(NpcClose(321))
    wire.add(field_map(), monster(at=(42, 38)))
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    assert brain.step_script(state).actions == (Attack(123),)


def test_preparation_overrides_retained_grind_script_not_explicit_goal():
    wire = npc_wire()
    client = PlayingClient(wire)
    model = ScriptedDecisionModel(
        {"react_monster": {"choice": "attack"}, "change_goal": {"choice": "keep"}}
    )
    brain = EventDrivenBrain(model, StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)

    brain.handle_event(state, MonsterSpotted(ActorRef(123, "Poring", "monster", 1)))
    assert brain.step_script(state).actions == (TalkToNpc(321),)
    assert state.goal == Goal.GRIND


def test_no_npc_observed_explores_only_public_walkable_map_bounded():

    wire = npc_wire()
    wire.add(struct.pack("<HIB", 0x80, 321, 0))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = PlayingClient(wire, cache=cache)
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert cache.get("prontera").walkable((actions[0].x, actions[0].y))
    assert abs(actions[0].x - state.x) <= 8
    assert abs(actions[0].y - state.y) <= 8


def test_malformed_dialogues_bounded_no_native_requests():
    for raw in (
        dialog(0xB4, "x")[:-1],
        struct.pack("<HHI", 0xB4, 10, 321) + b"\xff\0",
        dialog(0xB7, ":" * 254),
        dialog(0xB4, "x" * 4097),
    ):
        wire, client = opened()
        wire.add(raw)
        client.perform_native(NpcNext(321))
        assert len(wire.sent) == 1
        observed = client.build_native_state(Goal.GRIND).npc_dialogue
        assert observed is not None
        assert observed.stage == "blocked"


def test_exact_received_npc_kinds_approach_and_motion_pose_guards():
    for kind in (0, 5, 6, 12):
        wire = npc_wire()
        raw = bytearray(monster(kind=kind, aid=321))
        raw[59:62] = position(42, 38)
        wire.add(bytes(raw))
        client = PlayingClient(wire)
        client.perform_native(TalkToNpc(321))
        assert bool(wire.sent) == (kind in (6, 12))
    wire = npc_wire()
    raw = bytearray(monster(kind=6, aid=321))
    raw[59:62] = position(49, 38)
    wire.add(bytes(raw))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = PlayingClient(wire, cache=cache)
    client.perform_native(TalkToNpc(321))
    assert wire.moves
    assert not wire.sent
    client.perform_native(TalkToNpc(321))
    assert not wire.sent


def test_clef_provider_boundary_menu_selection_encodes_actual_received_index(monkeypatch):

    requests = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"answers": {"npc_menu": {"choice": "3"}}}

    def post(url, *, json, headers, timeout):
        requests.append(json)
        assert set(json) == {"model", "state", "questions"}
        assert json["model"] == "clef-flash"
        assert set(json["questions"]) == {"npc_menu"}
        assert json["questions"]["npc_menu"]["type"] == "choice"
        assert set(json["questions"]["npc_menu"]["criteria"]) == {"1", "2", "3", "cancel"}
        return Response()

    monkeypatch.setattr(httpx, "post", post)
    wire, client = opened()
    wire.add(dialog(0xB4, "Prepare before fighting."), dialog(0xB7, "Items::Training"))
    model = playing_backends.PlayingDecision(
        "http://127.0.0.1:1/v1/systemone", "", "clef-flash", 1.0
    )
    memory = Memory(StubSummarizer(max_chars=500))
    brain = EventDrivenBrain(model, StaticChatGenerator(), memory=memory)
    state = client.build_native_state(Goal.GRIND)
    for event in client.drain_native_events():
        for action in brain.handle_event(state, event).actions:
            client.perform_native(action)
    assert wire.sent[-1] == struct.pack("<HIB", 0xB8, 321, 3)
    assert "Prepare before fighting" in requests[0]["state"]["memory_view"]
    assert len(requests) == 1


def test_received_self_motion_denies_click_without_inferred_arrival():
    wire = npc_wire()
    wire.add(walk_ack((42, 37), (43, 37)))
    client = PlayingClient(wire)
    client.perform_native(TalkToNpc(321))
    assert not wire.sent
    assert not wire.moves


def test_nonfinite_clock_denies_npc_requests():
    wire = npc_wire()
    client = PlayingClient(wire, monotonic=lambda: float("nan"))
    client.perform_native(TalkToNpc(321))
    assert not wire.sent


def test_passive_stage_flood_is_finitely_bounded():
    wire, client = opened()
    wire.add(*(dialog(0xB5) for _ in range(65)))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "blocked"
    client.perform_native(NpcNext(321))
    assert len(wire.sent) == 1


def test_received_instruction_survives_map_change_without_claiming_gear():
    wire, client = opened()
    wire.add(dialog(0xB4, "Go to the field and defeat a Poring."), dialog(0xB6))
    client.perform_native(NpcClose(321))
    # The map change is the real town->field transition (window 30): the
    # goal script attacks the field monster, never claims gear.
    wire.add(field_map(), monster(at=(42, 38)))
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is None
    assert not state.inventory
    assert brain.step_script(state).actions == (Attack(123),)


def test_preparation_preserves_existing_recovery_pose_barrier():
    wire = npc_wire()
    client = PlayingClient(wire)
    model = ScriptedDecisionModel({"react_damage": {"choice": "rest"}})
    brain = EventDrivenBrain(model, StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    brain.handle_event(state, DamageTaken(5, 123))
    assert brain.step_script(state, can_resume=False).actions == ()
    assert brain.is_recovering


def test_unsupported_input_closes_shop_never_purchases():
    wire, client = opened()
    wire.add(dialog(0x142))
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())
    state = client.build_native_state(Goal.GRIND)
    assert brain.step_script(state).actions == (NpcClose(321),)
    client.perform_native(NpcClose(321))
    assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
    wire, client = opened()
    wire.add(dialog(0xC4))
    assert brain.step_script(client.build_native_state(Goal.GRIND)).actions == ()
    client.perform_native(NpcClose(321))
    assert len(wire.sent) == 1
