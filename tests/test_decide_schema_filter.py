"""The decide schema honours the facts: no party_join when already in a party.

Leg 16: the model picked party_join in 339 of 583 decides - including agents
already in a persisted party. The option was mechanically moot and the churn
starved grinding (123 grind picks, zero attacks). The schema now drops the
party actions the state's own facts make moot."""

from __future__ import annotations

from robots.domain.decisions import build_decision_request
from robots.domain.model import BotState, PartyInvite
from tests.conftest import make_state


def _options(state: BotState, *, party_join_feasible: bool = True) -> dict[str, str]:
    request = build_decision_request(
        state, memory_lines=[], party_join_feasible=party_join_feasible
    )
    criteria: dict[str, str] = request["questions"]["next_action"]["criteria"]
    return criteria


def test_party_join_absent_when_already_in_party() -> None:
    state = make_state(in_party=True)
    assert "party_join" not in _options(state)


def test_party_join_present_when_partyless_and_coordination_unknown() -> None:
    state = make_state(in_party=False)
    assert "party_join" in _options(state)


def test_party_join_absent_when_coordination_knows_no_path() -> None:
    options = _options(make_state(), party_join_feasible=False)
    assert "party_join" not in options
    assert "grind" in options


def test_received_invite_supplies_path_despite_no_online_group_peer() -> None:
    state = make_state(pending_invites=(PartyInvite("Stranger", 1.0),))
    assert "party_join" in _options(state, party_join_feasible=False)


def test_party_membership_makes_pending_invite_moot() -> None:
    state = make_state(in_party=True, pending_invites=(PartyInvite("Stranger", 1.0),))
    assert "party_join" not in _options(state)


def test_other_options_survive_the_filter() -> None:
    state = make_state(in_party=True)
    options = _options(state)
    for keep in ("grind", "loot", "travel", "go_town"):
        assert keep in options
