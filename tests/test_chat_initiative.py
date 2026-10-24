"""The chat initiative: goal-keyed premades on a slow cadence.

Leg 15's review announce path was dead code: URGENCY_TALK = 1.5 sits above
the chat_urgency score range (0-1), so no heartbeat ever announced. The
initiative is a cadence POLICY (the user's premade design: zero LLM cost) —
after CHAT_INITIATIVE_MIN_S a review may emit the goal-keyed premade with
probability CHAT_INITIATIVE_CHANCE."""

from __future__ import annotations

from robots.adapters.chat_prompt import initiative_due, initiative_premade
from robots.domain.model import Goal


def test_pick_is_goal_keyed() -> None:
    assert initiative_premade(Goal.GRIND, inventory=()) == "lfp"
    assert initiative_premade(Goal.FARM_ITEM, inventory=("Jellopy",)) == "lfp"
    assert initiative_premade(Goal.SOCIAL, inventory=()) == "lfp"
    assert initiative_premade(Goal.IDLE_TOWN, inventory=("Jellopy",)) == "sell_wts"
    assert initiative_premade(Goal.IDLE_TOWN, inventory=()) == "greet"


def test_cadence_gate() -> None:
    assert initiative_due(last_s=None, now_s=100.0, min_s=240.0)
    assert not initiative_due(last_s=90.0, now_s=300.0, min_s=240.0)
    assert initiative_due(last_s=90.0, now_s=330.1, min_s=240.0)


def test_chance_gate_uses_injected_rng() -> None:
    assert initiative_due(last_s=None, now_s=100.0, min_s=240.0, chance=0.5, roll=lambda: 0.1)
    assert not initiative_due(last_s=None, now_s=100.0, min_s=240.0, chance=0.5, roll=lambda: 0.9)
