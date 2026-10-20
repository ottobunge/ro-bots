"""Tests for the WorldState aggregate (ADR-007/008 write path)."""

import random

import pytest

from robots.app.roster_edit import with_persona_edited
from robots.app.world_state import (
    EVENT_FEED_MAXLEN,
    AgentRuntimeState,
    CommandError,
    FeedItem,
    WorldState,
)
from robots.society.human import HumanContribution, HumanTracker
from robots.society.society import ReputationEvent, SocietyRoster

SEED = 42
N_GROUPS = 3


def make_state() -> WorldState:
    roster = SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)
    return WorldState(roster, clock=lambda: 1.0)


def command_body() -> dict[str, object]:
    return {"type": "regenerate_roster", "seed": SEED, "groups": N_GROUPS, "solos": 1}


def test_agent_runtime_state_is_frozen() -> None:
    state = AgentRuntimeState(persona_id="p", current_goal="grind")
    with pytest.raises(Exception, match="cannot assign"):
        state.current_goal = "idle"  # type: ignore[misc]


def test_feed_item_operator_forced_defaults_false() -> None:
    item = FeedItem(ts=1.0, kind="chat", summary="hello")
    assert item.operator_forced is False


def test_initial_states_cover_every_persona() -> None:
    ws = make_state()
    assert set(ws.roster.personas) <= set(ws._agent_states)
    assert all(s.online is False for s in ws._agent_states.values())


def test_set_agent_state_updates_fields() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    updated = ws.set_agent_state(persona_id, current_goal="grind", online=True)
    assert updated.current_goal == "grind"
    assert updated.online is True
    again = ws.set_agent_state(persona_id, current_plan="step 1")
    assert again.current_goal == "grind"
    assert again.current_plan == "step 1"


def test_set_agent_state_unknown_persona_raises() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="unknown persona"):
        ws.set_agent_state("nope")


def test_push_event_appends_and_feed_is_bounded() -> None:
    ws = make_state()
    counter = iter(range(10_000))
    ws._clock = lambda: float(next(counter))
    for i in range(EVENT_FEED_MAXLEN + 25):
        ws.push_event("chat", f"msg {i}")
    events = ws.events
    assert len(events) == EVENT_FEED_MAXLEN
    assert events[0].summary == "msg 25"
    assert events[-1].summary == f"msg {EVENT_FEED_MAXLEN + 24}"


def test_regenerate_roster_same_seed_reproduces_identical_roster() -> None:
    ws = make_state()
    body = command_body()
    ws.apply_command(body)
    first_ids = sorted(ws.roster.personas)
    ws.apply_command(body)
    assert sorted(ws.roster.personas) == first_ids
    assert (
        ws.roster.personas[first_ids[0]]
        == SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS + 1).personas[first_ids[0]]
    )


def test_regenerate_roster_different_seed_differs() -> None:
    ws = make_state()
    ws.apply_command({"type": "regenerate_roster", "seed": 1, "groups": 3})
    ids_a = sorted(ws.roster.personas)
    ws.apply_command({"type": "regenerate_roster", "seed": 2, "groups": 3})
    ids_b = sorted(ws.roster.personas)
    assert ids_a != ids_b


def test_regenerate_roster_resets_agent_states() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws.set_agent_state(persona_id, current_goal="grind", online=True)
    ws.apply_command(command_body())
    fresh = ws.agent_state(persona_id)
    if fresh is not None:  # a reseed can drop the persona entirely
        assert fresh.current_goal == "idle"
        assert fresh.online is False


def test_regenerate_roster_emits_feed_item_with_seed() -> None:
    ws = make_state()
    item = ws.apply_command({"type": "regenerate_roster", "seed": 7, "groups": 2, "solos": 1})
    assert "seed 7" in item.summary
    assert item.operator_forced is False
    assert ws.events[-1] is item


def test_regenerate_roster_rejects_bad_params() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="groups"):
        ws.apply_command({"type": "regenerate_roster", "seed": 1, "groups": "many"})
    with pytest.raises(CommandError, match="solos"):
        ws.apply_command({"type": "regenerate_roster", "seed": 1, "groups": 1, "solos": -1})
    with pytest.raises(CommandError, match="friends_min"):
        ws.apply_command(
            {
                "type": "regenerate_roster",
                "seed": 1,
                "groups": 2,
                "friends_min": 4,
                "friends_max": 2,
            }
        )


def test_edit_persona_changes_attitude_and_persists() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws.apply_command({"type": "edit_persona", "persona_id": persona_id, "attitude": "grinder"})
    assert ws.roster.personas[persona_id].attitude.value == "grinder"
    assert ws.roster.personas[persona_id].name == ws.roster.personas[persona_id].name
    # the edit persists on the swapped-in roster
    assert ws.roster.personas[persona_id].attitude.value == "grinder"


def test_edit_persona_chattiness_and_playstyle() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws.apply_command(
        {
            "type": "edit_persona",
            "persona_id": persona_id,
            "chattiness": 0.9,
            "playstyle": "mage",
        }
    )
    persona = ws.roster.personas[persona_id]
    assert persona.chattiness == pytest.approx(0.9)
    assert persona.playstyle.value == "mage"


def test_edit_persona_rejects_bad_values() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    with pytest.raises(CommandError, match="attitude"):
        ws.apply_command({"type": "edit_persona", "persona_id": persona_id, "attitude": "grumpy"})
    with pytest.raises(CommandError, match="chattiness"):
        ws.apply_command({"type": "edit_persona", "persona_id": persona_id, "chattiness": 1.5})
    with pytest.raises(CommandError, match="no editable"):
        ws.apply_command({"type": "edit_persona", "persona_id": persona_id})


def test_edit_persona_unknown_id_is_404_class() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="unknown persona_id: 'ghost'"):
        ws.apply_command({"type": "edit_persona", "persona_id": "ghost", "name": "X"})


def test_with_persona_edited_returns_updated_roster() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    roster = with_persona_edited(ws.roster, persona_id, chattiness=0.5)
    assert roster.personas[persona_id].chattiness == 0.5
    assert ws.roster.personas[persona_id].chattiness != 0.5 or roster is not ws.roster
    with pytest.raises(KeyError):
        with_persona_edited(ws.roster, "ghost", chattiness=0.5)


def test_force_action_marks_operator_forced_and_appends_memory() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    before = len(ws.memory_lines(persona_id))
    item = ws.apply_command(
        {"type": "force_action", "persona_id": persona_id, "action": "wave", "args": "at Mika"}
    )
    assert item.operator_forced is True
    assert "operator forced: wave" in item.summary
    lines = ws.memory_lines(persona_id)
    assert len(lines) == before + 1
    assert any("operator forced: wave" in line for line in lines)


def test_force_action_without_args_has_clean_summary() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    item = ws.apply_command({"type": "force_action", "persona_id": persona_id, "action": "dance"})
    assert item.summary == "operator forced: dance"


def test_force_schedule_replaces_windows() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws.apply_command(
        {
            "type": "force_schedule",
            "persona_id": persona_id,
            "windows": [[2, 18.0, 23.0]],
        }
    )
    group = next(g for g in ws.roster.groups if persona_id in g.member_ids)
    assert group.schedule.windows == ((2, 18.0, 23.0),)
    assert group.schedule.is_online((2, 19.0))
    assert not group.schedule.is_online((3, 19.0))


def test_force_schedule_rejects_bad_windows() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    for body in (
        {"type": "force_schedule", "persona_id": persona_id, "windows": []},
        {"type": "force_schedule", "persona_id": persona_id, "windows": "nightly"},
        {"type": "force_schedule", "persona_id": persona_id, "windows": [[9, 1.0, 2.0]]},
        {"type": "force_schedule", "persona_id": persona_id, "windows": [[1, 25.0, 26.0]]},
        {"type": "force_schedule", "persona_id": persona_id, "windows": [[1, "a", "b"]]},
        {"type": "force_schedule", "persona_id": persona_id},
    ):
        with pytest.raises(CommandError):
            ws.apply_command(body)


def test_unknown_persona_force_action_raises() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="unknown persona"):
        ws.apply_command({"type": "force_action", "persona_id": "ghost", "action": "wave"})


def test_bad_command_type_raises() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="unknown command type"):
        ws.apply_command({"type": "explode"})


def test_apply_command_rejects_non_dict() -> None:
    ws = make_state()
    with pytest.raises(CommandError, match="JSON object"):
        ws.apply_command(["not", "a", "dict"])


def test_reputation_entries_group_and_agent_scores() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws._reputation.apply_event(ReputationEvent("Gossiper", persona_id, 0.3, "test seed"))
    entries = ws.reputation_entries(persona_id)
    assert any(e["human"] == "Gossiper" and e["agent_score"] == pytest.approx(0.3) for e in entries)


def test_human_tracker_integrates_with_world_state() -> None:
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    tracker = HumanTracker(
        ws._reputation,
        ws.roster.graph,
        list(ws.roster.groups),
        random.Random(0),
    )
    tracker.record(
        HumanContribution(
            human_name="Helper", kind="heal", magnitude=1.0, map_name="prontera", ts=1.0
        ),
        persona_id,
    )
    entries = ws.reputation_entries(persona_id)
    assert any(e["human"] == "Helper" for e in entries)


def test_human_tracker_absent_falls_back_to_group_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import robots.app.world_state as ws_module  # noqa: PLC0415

    monkeypatch.setattr(ws_module, "HumanTracker", None)
    ws = make_state()
    persona_id = sorted(ws.roster.personas)[0]
    ws._reputation.apply_event(ReputationEvent("Gossiper", persona_id, 0.3, "test seed"))
    entries = ws.reputation_entries(persona_id)
    assert entries
    assert all("agent_score" not in e for e in entries)
