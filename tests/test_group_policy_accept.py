"""The member-side group-policy accept.

The coordination design (the user's knowledge model, 2026-10-22): the friend
group plays and parties TOGETHER by policy — the roster is injected knowledge
and the invites travel in-game. A same-group invite is therefore accepted
deterministically; Clef's bare ``accept_invite`` noul never crossed the 0.5
gate in leg 8 (~0.007 across 347 decides) and would leave every formation
hanging. Cross-group and solo accepts stay decide-driven.
"""

from __future__ import annotations

from typing import cast

from robots.app.brain import EventDrivenBrain
from robots.domain.actions import AcceptInvite
from robots.domain.events import InviteReceived
from robots.domain.model import PartyInvite
from robots.ports import ChatGenerator, DecisionModel
from robots.society.objectives import BoundCoordinator, GroupCoordinator
from robots.society.relations import RelationshipLedger


def _coordinator(ledger: RelationshipLedger, persona: str) -> GroupCoordinator:
    return GroupCoordinator(ledger, persona)


def test_same_group_members_are_same_group() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("g00", ("pop_a", "pop_b", "pop_c"))
    coord = _coordinator(ledger, "pop_b")
    assert coord.same_group("pop_a") is True


def test_cross_group_and_unknown_are_not_same_group() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("g00", ("pop_a", "pop_b"))
    ledger.seed_group("g01", ("pop_x",))
    coord = _coordinator(ledger, "pop_b")
    assert coord.same_group("pop_x") is False
    assert coord.same_group("pop_unknown") is False


def test_solo_without_group_is_never_same_group() -> None:
    ledger = RelationshipLedger()
    coord = _coordinator(ledger, "pop_solo")
    assert coord.same_group("pop_a") is False


def test_brain_accepts_same_group_invite_regardless_of_noul() -> None:
    """The leg-8 live wire: Clef's bare accept_invite noul stayed ~0.007 (347
    decides) — a same-group invite must accept by group policy."""

    ledger = RelationshipLedger()
    ledger.register_persona("pop_lead", "CharLead")
    ledger.register_persona("pop_member", "CharMember")
    ledger.seed_group("g00", ("pop_lead", "pop_member"))
    brain = EventDrivenBrain(
        decision_model=cast("DecisionModel", lambda _request: {"answers": {}}),
        chat=cast("ChatGenerator", lambda *_a, **_k: "gg"),
        coordination=cast("BoundCoordinator", _coordinator(ledger, "pop_member")),
    )
    event = InviteReceived(invite=PartyInvite(from_name="CharLead", at=0.0))
    actions = brain._invite_actions(event, {"accept_invite": {"noul": 0.007}})
    assert actions == (AcceptInvite(),)


def test_brain_keeps_the_model_gate_for_outsiders() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("pop_lead", "CharLead")
    ledger.register_persona("pop_member", "CharMember")
    ledger.register_persona("pop_out", "CharOut")
    ledger.seed_group("g00", ("pop_lead", "pop_member"))
    ledger.seed_group("g01", ("pop_out",))
    brain = EventDrivenBrain(
        decision_model=cast("DecisionModel", lambda _request: {"answers": {}}),
        chat=cast("ChatGenerator", lambda *_a, **_k: "gg"),
        coordination=cast("BoundCoordinator", _coordinator(ledger, "pop_member")),
    )
    event = InviteReceived(invite=PartyInvite(from_name="CharOut", at=0.0))
    assert brain._invite_actions(event, {"accept_invite": {"noul": 0.007}}) == ()
