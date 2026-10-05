"""Tests for the SystemOne request schema built from domain state."""

from tests.conftest import make_state

from robots.domain.decisions import PREMADE_CHAT, build_decision_request
from robots.domain.model import ChatLine, Goal


def test_request_has_model_state_questions(state) -> None:
    request = build_decision_request(state)
    assert request["model"] == "clef"
    assert set(request) == {"model", "state", "questions", "goal_criterion_grind"}
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
