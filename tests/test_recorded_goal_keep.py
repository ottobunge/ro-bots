"""Recorded Clef answer-summary replay; synthetic state, no inference/native I/O.

Source: playing-mvp-goal-behavior-diagnostic.json, fixtures 0 and 1.
Only answer summaries were recorded; all context here is synthetic.
"""

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.model import BotState, Goal

RECORDED_STARTUP_ANSWERS: list[dict[str, Any]] = [
    {
        "change_goal": {
            "type": "choice",
            "choice": "keep",
            "probabilities": {
                "farm": 0.2914796450995338,
                "grind": 0.2704688806072831,
                "keep": 0.32257937885253624,
                "social": 0.06011189805734616,
                "town": 0.05536019738330071,
            },
            "confidence": 0.15322422356567028,
        },
        "goal_review": {
            "type": "score",
            "score": 0.47613983195913184,
            "legend": {"0": "Badly, reconsider", "1": "Going okay", "2": "Going great"},
            "probabilities": {
                "0": 0.575745338642186,
                "1": 0.3723694907564962,
                "2": 0.05188517060131781,
            },
            "confidence": 0.28579025206130215,
        },
        "next_action": {
            "type": "choice",
            "choice": "grind",
            "probabilities": {
                "chat": 0.018841221487018184,
                "go_town": 0.028551436346959617,
                "grind": 0.7326862836350065,
                "idle": 0.03594221615845371,
                "loot": 0.013471080366091131,
                "party_invite": 0.025354329894044226,
                "party_join": 0.049953581954545835,
                "quest": 0.01907742889641724,
                "rest": 0.04464123211209369,
                "travel": 0.031481189149369836,
            },
            "confidence": 0.7029847595944517,
        },
    },
    {
        "change_goal": {
            "type": "choice",
            "choice": "keep",
            "probabilities": {
                "farm": 0.2992894882895806,
                "grind": 0.27588125743932557,
                "keep": 0.2996420168575097,
                "social": 0.06424255045061572,
                "town": 0.0609446869629685,
            },
            "confidence": 0.12455252107188709,
        },
        "goal_review": {
            "type": "score",
            "score": 0.455523213077666,
            "legend": {"0": "Badly, reconsider", "1": "Going okay", "2": "Going great"},
            "probabilities": {
                "0": 0.5909268718362671,
                "1": 0.36262304324979955,
                "2": 0.046450084913933244,
            },
            "confidence": 0.3167151803835009,
        },
        "next_action": {
            "type": "choice",
            "choice": "grind",
            "probabilities": {
                "chat": 0.021796618150778994,
                "go_town": 0.03221081742549342,
                "grind": 0.7211178541776226,
                "idle": 0.040092907377435365,
                "loot": 0.014064307203631651,
                "party_invite": 0.027236836513555757,
                "party_join": 0.04929126791646487,
                "quest": 0.020097726103368872,
                "rest": 0.03964260267505616,
                "travel": 0.034449062456592336,
            },
            "confidence": 0.6901309490862474,
        },
    },
]


@pytest.mark.parametrize("fixture_index", [0, 1])
def test_recorded_keep_start_selects_grind(state: BotState, fixture_index: int) -> None:
    # Empty perception/context prevents inventing a live target or farming catalogue.
    state = replace(
        state,
        name="RecordedKeepReplay",
        goal=Goal.GRIND,
        nearby=(),
        inventory={},
        pending_invites=(),
        recent_chat=(),
        in_party=False,
    )
    original_state = deepcopy(state)
    answers = deepcopy(RECORDED_STARTUP_ANSWERS[fixture_index])
    original_answers = deepcopy(answers)
    model = ScriptedDecisionModel(answers=answers)
    brain = EventDrivenBrain(model, StaticChatGenerator(["unused"]))

    result = brain.start(state)

    assert isinstance(brain.current_script(), GrindScript)
    assert brain.current_plan is None
    assert result.notes == ("event:periodic review #0", "script->GrindScript")
    assert not any(note.startswith("goal ") for note in result.notes)
    assert result.actions == ()
    assert result.answers == original_answers
    assert answers == original_answers
    assert state == original_state
    assert state.goal is Goal.GRIND
    assert model.calls == brain.decision_count == 1
    assert brain.escalation_count == 0
    assert result.escalated is False


@pytest.mark.parametrize(
    "directive", [{}, {"change_goal": {}}, {"change_goal": {"choice": "unknown"}}]
)
def test_missing_or_unsupported_goal_still_uses_bad_score(
    state: BotState, directive: dict[str, Any]
) -> None:
    answers = {**directive, "goal_review": {"score": 0.1}}
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(["unused"]))
    notes: list[str] = []

    assert brain._review_goal(state, answers, notes) is Goal.SOCIAL
    assert notes == ["goal grind->social (bad review)"]
    assert state.goal is Goal.GRIND
