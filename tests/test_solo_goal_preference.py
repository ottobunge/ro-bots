"""Leg 94: impossible party seeking must release the farming script slot."""

from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import FarmScript, IdleTownScript
from robots.domain.actions import Attack
from robots.domain.events import Heartbeat
from robots.domain.model import ActorRef, Goal, PartyInvite
from robots.society.objectives import BoundCoordinator, GroupCoordinator
from robots.society.relations import RelationshipLedger
from tests.conftest import make_state
from tests.test_brain import base_answers
from tests.test_wants import RecordingModel


def coordinator(*, grouped: bool, online: list[str]) -> BoundCoordinator:
    ledger = RelationshipLedger()
    for persona, name in (("self", "YuffieFy81"), ("peer", "Friend"), ("other", "Stranger")):
        ledger.register_persona(persona, name)
    if grouped:
        ledger.seed_group("friends", ("self", "peer"), save_map="pay_fild04")
    ledger.seed_group("outsiders", ("other",), save_map="prontera")
    return BoundCoordinator(GroupCoordinator(ledger, "self"), online=lambda: tuple(online))


def social_answers(change: str = "keep") -> dict[str, Any]:
    answers = base_answers()
    answers["change_goal"] = {"choice": change}
    answers["next_action"] = {"choice": "party_join", "confidence": 0.9}
    answers["farm_target"] = {"choice": "Drops"}
    return answers


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize(
    ("current", "change", "next_action"),
    [
        (Goal.SOCIAL, "keep", "party_join"),
        (Goal.SOCIAL, "keep", "grind"),
        (Goal.GRIND, "social", "party_join"),
    ],
)
def test_no_invite_path_releases_social_slot_and_authors_attacks(
    grouped, current, change, next_action
) -> None:
    # s00 after the merchant trip: healthy, armed, no stock, Drops in melee.
    state = make_state(
        name="YuffieFy81",
        goal=current,
        job="Novice",
        base_level=3,
        hp=86,
        max_hp=86,
        map_name="pay_fild04",
        inventory={"Knife": 1},
        nearby=(ActorRef(1001, "Drops", "monster", 1.0, x=121, y=74),),
    )
    answers = social_answers(change)
    answers["next_action"] = {"choice": next_action, "confidence": 0.9}
    model = RecordingModel(answers)
    brain = EventDrivenBrain(
        model,
        StaticChatGenerator(),
        coordination=coordinator(grouped=grouped, online=["self", "other"]),
        spawn_species=lambda _map: ("Drops",),
    )
    # Movement/chat can reset the old idle streak without making a join feasible.
    brain._actions_since_review = 4
    result = brain.start(state)

    assert isinstance(brain.current_script(), FarmScript)
    assert brain.current_plan is not None
    assert brain.current_plan.target_mobs == ("Drops",)
    assert any(isinstance(action, Attack) for action in brain.step_script(state).actions)
    request = model.requests[-1]
    assert "party_join" not in request["questions"]["next_action"]["criteria"]
    assert request["state"]["party_join_feasible"] is False
    assert any("no invite path" in note for note in result.notes)


@pytest.mark.parametrize("path", ["pending", "online_peer", "in_party"])
def test_genuine_party_paths_preserve_social_goal(path) -> None:
    state = make_state(
        name="YuffieFy81",
        goal=Goal.SOCIAL,
        in_party=path == "in_party",
        pending_invites=(PartyInvite("Stranger", 2.0),) if path == "pending" else (),
    )
    online = ["self", "peer"] if path == "online_peer" else ["self", "other"]
    model = RecordingModel(social_answers())
    brain = EventDrivenBrain(
        model,
        StaticChatGenerator(),
        coordination=coordinator(grouped=path == "online_peer", online=online),
    )

    result = brain.start(state)

    assert isinstance(brain.current_script(), IdleTownScript)
    options = model.requests[-1]["questions"]["next_action"]["criteria"]
    assert ("party_join" in options) is (path != "in_party")
    assert not any("no invite path" in note for note in result.notes)


def test_online_peer_evidence_is_refreshed_for_each_review() -> None:
    online = ["self", "peer"]
    model = RecordingModel(social_answers())
    brain = EventDrivenBrain(
        model,
        StaticChatGenerator(),
        coordination=coordinator(grouped=True, online=online),
    )
    state = make_state(name="YuffieFy81", goal=Goal.SOCIAL)
    brain.start(state)
    assert isinstance(brain.current_script(), IdleTownScript)

    online.remove("peer")
    brain.handle_event(state, Heartbeat(seq=1))
    assert "party_join" not in model.requests[-1]["questions"]["next_action"]["criteria"]
    assert not isinstance(brain.current_script(), IdleTownScript)
