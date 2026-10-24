"""The decide schema honours the facts: no party_join when already in a party.

Leg 16: the model picked party_join in 339 of 583 decides - including agents
already in a persisted party. The option was mechanically moot and the churn
starved grinding (123 grind picks, zero attacks). The schema now drops the
party actions the state's own facts make moot."""

from __future__ import annotations

from robots.domain.decisions import build_decision_request
from robots.domain.model import BotState
from tests.conftest import make_state


def _options(state: BotState) -> dict[str, str]:
    request = build_decision_request(state, memory_lines=[])
    criteria: dict[str, str] = request["questions"]["next_action"]["criteria"]
    return criteria


def test_party_join_absent_when_already_in_party() -> None:
    state = make_state(in_party=True)
    assert "party_join" not in _options(state)


def test_party_join_present_when_partyless() -> None:
    state = make_state(in_party=False)
    assert "party_join" in _options(state)


def test_other_options_survive_the_filter() -> None:
    state = make_state(in_party=True)
    options = _options(state)
    for keep in ("grind", "loot", "travel", "go_town"):
        assert keep in options
