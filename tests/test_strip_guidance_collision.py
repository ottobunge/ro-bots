"""Offline leg-84 regression: an admitted stripped buyer outranks preparation."""

import logging
import struct
from dataclasses import replace

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import (
    MERCHANT_ROUTE,
    GrindScript,
    IdleTownScript,
    NpcGuidanceScript,
    ScriptStatus,
    merchant_admission_refusal,
    needs_npc_preparation,
    script_for,
)
from robots.domain.actions import MoveTo, TalkToNpc
from robots.domain.model import Goal
from tests.test_native_entry_npc_names import actor_entry
from tests.test_native_npc_guidance import npc_wire
from tests.test_playing_runtime import position


@pytest.fixture(autouse=True)
def _clear_drive_history():
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()


def _brain() -> EventDrivenBrain:
    return EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator())


def _client(*, cache: MapCache | None = None) -> PlayingClient:
    wire = npc_wire()
    wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 156, 25))
    return PlayingClient(wire, cache=cache, seed_zeny=115)


def _npc_frame(sprite: int, *, aid: int = 444, pid: int = 0x09FE) -> bytes:
    raw = bytearray(actor_entry(pid, name=b"Received NPC", aid=aid))
    struct.pack_into("<H", raw, 23, sprite)
    offset = 63 if pid == 0x09FD else 59
    raw[offset : offset + 3] = position(156, 26)
    if pid == 0x09FD:
        # WBUFPOS2 carries a destination too; keep the observed warp adjacent.
        raw[offset + 2] |= 156 >> 6
        raw[offset + 3] = (156 << 2) & 0xFF
        raw[offset + 4] = 26
    return bytes(raw)


@pytest.mark.parametrize("goal", list(Goal))
def test_affordable_empty_native_novice_takes_drive_before_guidance(goal: Goal):
    client = _client()
    client.wire.add(_npc_frame(45))  # the nearest actor is a received warp
    state = client.build_native_state(goal)
    assert state.inventory_known
    assert not state.inventory
    assert not state.npc_instructions_received
    assert merchant_admission_refusal(state) is None
    brain = _brain()
    assert brain._plan is None
    outcome = brain.step_script(state)
    assert outcome.actions == (MoveTo(*MERCHANT_ROUTE["prontera"]),)
    assert outcome.status is ScriptStatus.ACTIVE
    assert not isinstance(brain._script, NpcGuidanceScript)
    # A patient drive tick retains ownership without falling into guidance.
    assert brain.step_script(state).actions == ()


@pytest.mark.parametrize("goal", [Goal.GRIND, Goal.FARM_ITEM, Goal.IDLE_TOWN, Goal.SOCIAL])
def test_factory_releases_preparation_to_the_goal_when_drive_admits(goal: Goal):
    client = _client()
    state = client.build_native_state(goal)
    assert not needs_npc_preparation(state)
    script = script_for(goal, state)
    assert isinstance(
        script, GrindScript if goal in (Goal.GRIND, Goal.FARM_ITEM) else IdleTownScript
    )


@pytest.mark.parametrize("goal", list(Goal))
def test_runtime_honors_admitted_drive_precedence(goal: Goal):
    client = _client()
    state = client.build_native_state(goal)
    assert client._npc_mechanical(state, ()) is None


@pytest.mark.parametrize(
    ("zeny", "map_name", "suspended", "reason"),
    [
        (0, "unknown_route", False, "no_stock_below_zeny_floor"),
        (0, "prontera", False, "no_stock_below_zeny_floor"),
        (115, "unknown_route", False, "map_not_on_merchant_route"),
        (115, "prontera", True, "buy_suspended"),
    ],
)
def test_refused_empty_novice_keeps_guidance_and_names_refusal(
    zeny: int, map_name: str, suspended: bool, reason: str, caplog
):
    client = _client()
    client.wire.add(_npc_frame(100))
    state = replace(
        client.build_native_state(Goal.GRIND),
        zeny=zeny,
        map_name=map_name,
        merchant_buy_suspended=suspended,
    )
    verdict = merchant_admission_refusal(state)
    assert verdict is not None
    assert verdict[0] == reason
    assert needs_npc_preparation(state)
    assert isinstance(script_for(state.goal, state), NpcGuidanceScript)
    assert client._npc_mechanical(state, ()) == ()
    # Clear the tap after checking the predicate/factory: the brain must also
    # surface why the merchant path did not take ownership.
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    with caplog.at_level(logging.WARNING):
        outcome = _brain().step_script(state)
    assert outcome.actions == (TalkToNpc(444),)
    assert any(reason in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("sprite", [45, 139])
@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
def test_guidance_skips_received_warp_sprite_for_farther_guide(sprite: int, pid: int):
    client = _client()
    client.wire.add(_npc_frame(sprite, pid=pid), _npc_frame(100, aid=555))
    state = client.build_native_state(Goal.QUEST)
    assert len(state.nearby) == 2
    assert state.nearby[0].npc_sprite == sprite
    assert state.nearby[0].distance == 1
    guide = replace(state.nearby[1], distance=4, x=159, y=25)
    state = replace(state, nearby=(state.nearby[0], guide), zeny=0)
    outcome = NpcGuidanceScript().step(state)
    assert outcome.actions == (TalkToNpc(555),)


@pytest.mark.parametrize("sprite", [45, 139])
def test_only_warp_is_named_no_guidance_candidate_and_allows_exploration(sprite: int, caplog):
    cache = MapCache((WalkMap("prontera", 320, 320, bytes(320 * 320)),))
    client = _client(cache=cache)
    client.wire.add(_npc_frame(sprite))
    state = replace(client.build_native_state(Goal.GRIND), zeny=0)
    with caplog.at_level(logging.DEBUG):
        outcome = NpcGuidanceScript().step(state)
    assert outcome.actions == ()
    assert outcome.status is ScriptStatus.FAILED
    assert any("no_non_warp_guidance_npc" in r.getMessage() for r in caplog.records)
    actions = client._npc_mechanical(state, outcome.actions)
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert client._npc_explorations == 1


def test_admitted_patient_tick_never_explores_for_guidance():
    cache = MapCache((WalkMap("prontera", 320, 320, bytes(320 * 320)),))
    client = _client(cache=cache)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == ()
    assert client._npc_explorations == 0


def test_buy_completion_keeps_the_retained_social_goal_script():
    client = _client()
    state = client.build_native_state(Goal.SOCIAL)
    brain = _brain()
    brain._script = brain._goal_script(state.goal, state)
    assert isinstance(brain._script, IdleTownScript)
    assert brain.step_script(state).actions == (MoveTo(*MERCHANT_ROUTE["prontera"]),)
    state = replace(state, inventory={"1201": 1})
    assert brain.step_script(state).actions == (MoveTo(state.x, state.y + 1),)


@pytest.mark.parametrize("sprite", [45, 139])
def test_new_received_entry_replaces_warp_exclusion(sprite: int):
    client = _client()
    client.wire.add(_npc_frame(sprite))
    state = client.build_native_state(Goal.QUEST)
    assert NpcGuidanceScript().step(state).actions == ()
    client.wire.add(_npc_frame(100))
    state = client.build_native_state(Goal.QUEST)
    assert NpcGuidanceScript().step(state).actions == (TalkToNpc(444),)
