"""Offline regressions for explicit goal choices versus review fallback."""

from dataclasses import replace

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.model import Goal


def test_start_honors_explicit_current_grind_despite_bad_review(state) -> None:
    answers = {"change_goal": {"choice": "grind"}, "goal_review": {"score": 0.1}}
    model = ScriptedDecisionModel(answers=answers)
    brain = EventDrivenBrain(model, StaticChatGenerator(["unused"]))

    result = brain.start(state)

    assert isinstance(brain.current_script(), GrindScript)
    assert not any(note.startswith("goal ") for note in result.notes)
    assert result.answers == answers
    assert state.goal is Goal.GRIND
    assert brain.decision_count == 1
    assert brain.escalation_count == 0


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("social", Goal.SOCIAL),
        ("grind", Goal.GRIND),
        ("farm", Goal.FARM_ITEM),
        ("town", Goal.IDLE_TOWN),
    ],
)
@pytest.mark.parametrize("same_goal", [True, False])
def test_supported_explicit_choice_overrides_bad_review(state, choice, expected, same_goal) -> None:
    current = expected if same_goal else Goal.QUEST
    state = replace(state, goal=current)
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(["unused"]))
    answers = {"change_goal": {"choice": choice}, "goal_review": {"score": 0.1}}
    notes: list[str] = []

    assert brain._review_goal(state, answers, notes) is expected
    assert notes == ([] if same_goal else [f"goal {current}->{expected}"])
    assert state.goal is current


# Intentional contract revision: explicit keep is authoritative, not a fallback.
@pytest.mark.parametrize("choice", [None, "unknown"])
@pytest.mark.parametrize("current", [Goal.GRIND, Goal.SOCIAL])
@pytest.mark.parametrize("score", [0.1, 0.5, 1.0, None])
def test_nonexplicit_choice_preserves_review_fallback(state, choice, current, score) -> None:
    state = replace(state, goal=current)
    answers = {}
    if choice is not None:
        answers["change_goal"] = {"choice": choice}
    if score is not None:
        answers["goal_review"] = {"score": score}
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(["unused"]))
    notes: list[str] = []
    expected = current
    if score is not None and score < 0.5:
        expected = Goal.SOCIAL if current is not Goal.SOCIAL else Goal.GRIND

    assert brain._review_goal(state, answers, notes) is expected
    assert notes == ([] if expected is current else [f"goal {current}->{expected} (bad review)"])
    assert state.goal is current


@pytest.mark.parametrize(
    "current", [Goal.GRIND, Goal.SOCIAL, Goal.FARM_ITEM, Goal.IDLE_TOWN, Goal.QUEST]
)
@pytest.mark.parametrize("score", [0.1, 0.5, 1.0, None])
def test_explicit_keep_is_authoritative(state, current, score) -> None:
    state = replace(state, goal=current)
    answers = {"change_goal": {"choice": "keep"}}
    if score is not None:
        answers["goal_review"] = {"score": score}
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(["unused"]))
    notes: list[str] = []

    assert brain._review_goal(state, answers, notes) is current
    assert notes == []
    assert state.goal is current
