"""Tests for the SystemOne request schema built from domain state."""

import pytest

from robots.domain.decisions import PREMADE_CHAT, build_decision_request, goal_summary
from robots.domain.model import ChatLine, Goal
from tests.conftest import make_state


def test_request_has_model_state_questions(state) -> None:
    request = build_decision_request(state)
    assert request["model"] == "clef"
    assert set(request) == {"model", "state", "questions"}
    assert request["state"]["bot"]["name"] == "SpikeBot01"


def test_schema_question_types(state) -> None:
    questions = build_decision_request(state)["questions"]
    assert questions["next_action"]["type"] == "choice"
    assert questions["should_reply"]["type"] == "noul"
    assert questions["chat_urgency"]["type"] == "score"
    assert set(questions["next_action"]["criteria"]) >= {"grind", "loot", "travel", "chat"}


def test_premade_chat_exposed_as_options(state) -> None:
    questions = build_decision_request(state)["questions"]
    assert set(PREMADE_CHAT) <= set(questions["premade_pick"]["criteria"])
    assert "none" in questions["premade_pick"]["criteria"]


def test_state_serialization_includes_world_facts(state) -> None:
    payload = build_decision_request(state)["state"]
    assert payload["bot"]["hp_ratio"] == 0.8
    assert "Poring" in payload["nearby_actors"]
    assert "Jellopy" in payload["inventory"]


def test_chat_and_invites_appear_in_state() -> None:
    state = make_state(
        goal=Goal.QUEST,
        pending_invites=(),
        recent_chat=(ChatLine(channel="party", sender="A", text="buffs?", at=1.0),),
    )
    payload = build_decision_request(state)["state"]
    assert "buffs?" in payload["recent_chat"]
    assert payload["pending_party_invites"] == "none"


def test_hp_ratio_zero_max() -> None:
    state = make_state(max_hp=0)
    assert state.hp_ratio == 0.0


@pytest.mark.parametrize(
    ("goal", "summary"),
    [
        (Goal.GRIND, "Level up by fighting monsters suited to my level."),
        (Goal.FARM_ITEM, "Farm for the specific item I am assigned."),
        (Goal.IDLE_TOWN, "Relax in town, maybe chat with passers-by."),
        (Goal.QUEST, "Work on a level-appropriate quest."),
        (Goal.SOCIAL, "Find and join other players, party or guild."),
    ],
)
def test_goal_summary_and_private_memory_preserved(goal, summary):
    state = make_state(goal=goal, inventory_known=False)
    lines = [f"private memory {n}" for n in range(45)]
    before = list(lines)
    request = build_decision_request(state, memory_lines=lines)
    assert set(request) == {"model", "state", "questions"}
    assert request["state"]["bot"]["goal"] == str(goal)
    assert request["state"]["inventory"] == "unknown"
    assert request["state"]["memory_view"] == "\n".join(lines[:40])
    assert lines == before
    assert "memory_view" not in build_decision_request(state)["state"]
    assert build_decision_request(state, memory_lines=[])["state"]["memory_view"] == ""
    assert goal_summary(goal) == summary
