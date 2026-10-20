"""Group objectives: coordination-through-game-socials (the operator directive).

The agent-level + character-level planning layer where a group's shared goal
(a GroupObjective) travels ONLY through in-game socials: the leader forms it,
the party invites / party chat / whisper premades are the sole channels, and
members join by accepting the in-game invite — never by out-of-band state
mutation. The roster itself is injected knowledge at agent creation (persona
names + character names), which is how friends FIND each other in-game.
"""

import inspect
from typing import Any, Literal

import pytest

import robots.society.objectives as objectives_module
import robots.society.relations as relations_module
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain, TickResult
from robots.domain.actions import AcceptInvite, InviteToParty, PartyChat, Say, WhisperTo
from robots.domain.events import ChatHeard, Heartbeat, InviteReceived
from robots.domain.model import BotState, ChatLine, Goal, PartyInvite
from robots.popgen import GeneratedPopulation, PopulationSpec, generate_population
from robots.society.objectives import (
    OBJECTIVE_ACTIVE,
    OBJECTIVE_DISSOLVED,
    OBJECTIVE_INVITED,
    OBJECTIVE_KINDS,
    OBJECTIVE_PROPOSED,
    BoundCoordinator,
    GroupCoordinator,
    GroupObjective,
    GroupObjectiveBook,
    meet_premade,
    objective_goal,
    objective_premade,
    parse_objective_premade,
    seed_roster,
)
from robots.society.relations import RelationshipLedger, _pair_key
from tests.test_brain import base_answers


def pop_2_2_1() -> GeneratedPopulation:
    """The acceptance example: two 2-member friend groups + 1 solo, seed 7."""
    return generate_population(
        PopulationSpec(friend_groups=2, friends_per_group=(2, 2), solo_agents=1, seed=7)
    )


# -- the premade protocol (the in-game message content) -----------------------


def test_objective_premade_texts_are_the_game_channel_vocabulary() -> None:
    assert objective_premade("hunt", "prt_fild08", "porings") == (
        "hunting porings prt_fild08, join me"
    )
    assert objective_premade("farm", "prontera", "jellopy") == ("farming jellopy prontera, join me")
    assert objective_premade("town", "prontera") == "idling in prontera, join me"
    # A hunt without a named target still reads like a player line.
    assert objective_premade("hunt", "prt_fild08") == "hunting prt_fild08, join me"


def test_objective_premade_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        objective_premade("wedding", "prontera")  # type: ignore[arg-type]


def test_objective_premade_round_trips_through_the_parser() -> None:
    for kind, map_name, target in (
        ("hunt", "prt_fild08", "porings"),
        ("farm", "prontera", "jellopy"),
        ("town", "prontera", None),
    ):
        announcement = parse_objective_premade(objective_premade(kind, map_name, target or ""))
        assert announcement is not None
        assert announcement.kind == kind
        assert announcement.map_name == map_name
        assert announcement.target == target


def test_parser_ignores_everyday_chat() -> None:
    assert parse_objective_premade("gg wp") is None
    assert parse_objective_premade("Hi all!") is None
    assert parse_objective_premade("meet at prontera 156,22 at 19:00") is None


def test_meet_premade_is_the_offline_coordination_whisper_text() -> None:
    assert meet_premade("prontera 156,22", "19:00") == "meet at prontera 156,22 at 19:00"


def test_objective_goal_maps_kind_to_drive() -> None:
    assert objective_goal("hunt") == Goal.GRIND
    assert objective_goal("farm") == Goal.FARM_ITEM
    assert objective_goal("town") == Goal.IDLE_TOWN


# -- the objective lifecycle ---------------------------------------------------


def make_book(**kwargs: Any) -> GroupObjectiveBook:
    return GroupObjectiveBook(**kwargs)


def propose_hunt(book: GroupObjectiveBook) -> GroupObjective:
    return book.propose(
        "obj-1",
        "pop_g00",
        "pop_0007_g00m00",
        "hunt",
        "prt_fild08",
        target="porings",
        invited=("pop_0007_g00m01",),
    )


def test_propose_starts_the_objective_as_proposed() -> None:
    book = make_book()
    objective = propose_hunt(book)
    assert objective.status == OBJECTIVE_PROPOSED
    assert objective.group_id == "pop_g00"
    assert objective.leader_id == "pop_0007_g00m00"
    assert objective.kind == "hunt"
    assert objective.map_name == "prt_fild08"
    assert objective.target == "porings"
    assert objective.accepted == ()
    assert book.objective("obj-1") == objective


def test_unknown_kind_is_rejected_at_propose() -> None:
    book = make_book()
    with pytest.raises(ValueError, match="kind"):
        book.propose("obj-x", "pop_g00", "lead", "wedding", "prontera")


def test_mark_invited_moves_proposed_to_invited() -> None:
    book = make_book()
    propose_hunt(book)
    objective = book.mark_invited("obj-1", ("pop_0007_g00m01",))
    assert objective.status == OBJECTIVE_INVITED
    assert objective.invited == ("pop_0007_g00m01",)


def test_first_join_activates_the_objective() -> None:
    book = make_book()
    propose_hunt(book)
    book.mark_invited("obj-1", ("pop_0007_g00m01",))
    objective = book.record_join("obj-1", "pop_0007_g00m01")
    assert objective.status == OBJECTIVE_ACTIVE
    assert objective.accepted == ("pop_0007_g00m01",)


def test_objective_without_join_is_never_active() -> None:
    book = make_book()
    propose_hunt(book)
    objective = book.mark_invited("obj-1", ("pop_0007_g00m01",))
    assert objective.status == OBJECTIVE_INVITED
    assert objective.accepted == ()


def test_leader_leaving_dissolves_the_objective() -> None:
    book = make_book()
    propose_hunt(book)
    book.mark_invited("obj-1", ("pop_0007_g00m01",))
    objective = book.dissolve("obj-1", reason="schedule window closed")
    assert objective.status == OBJECTIVE_DISSOLVED
    assert objective.reason == "schedule window closed"


def test_last_member_leaving_dissolves_the_objective() -> None:
    book = make_book()
    propose_hunt(book)
    book.mark_invited("obj-1", ("pop_0007_g00m01",))
    book.record_join("obj-1", "pop_0007_g00m01")
    objective = book.record_leave("obj-1", "pop_0007_g00m01")
    assert objective.status == OBJECTIVE_DISSOLVED


def test_surviving_members_keep_the_objective_active() -> None:
    book = make_book()
    book.propose(
        "obj-2",
        "pop_g01",
        "pop_0007_g01m00",
        "farm",
        "prontera",
        target="jellopy",
        invited=("pop_0007_g01m01", "pop_0007_g01m02"),
    )
    book.mark_invited("obj-2", ("pop_0007_g01m01", "pop_0007_g01m02"))
    book.record_join("obj-2", "pop_0007_g01m01")
    book.record_join("obj-2", "pop_0007_g01m02")
    objective = book.record_leave("obj-2", "pop_0007_g01m01")
    assert objective.status == OBJECTIVE_ACTIVE
    assert objective.accepted == ("pop_0007_g01m02",)


def test_objectives_for_group_filters_by_status() -> None:
    book = make_book()
    propose_hunt(book)
    book.propose(
        "obj-2", "pop_g00", "pop_0007_g00m00", "town", "prontera", invited=("pop_0007_g00m01",)
    )
    assert [o.objective_id for o in book.objectives_for_group("pop_g00")] == ["obj-1", "obj-2"]
    active_only = book.objectives_for_group(
        "pop_g00", statuses=(OBJECTIVE_INVITED, OBJECTIVE_ACTIVE)
    )
    assert active_only == ()


# -- persistence (the ledger JSON carries objectives across reconnects) ---------


def test_book_round_trip_preserves_every_objective() -> None:
    book = make_book()
    propose_hunt(book)
    book.mark_invited("obj-1", ("pop_0007_g00m01",))
    book.record_join("obj-1", "pop_0007_g00m01")
    book.record_leave("obj-1", "pop_0007_g00m01")
    restored = GroupObjectiveBook.from_dict(book.to_dict())
    assert restored.to_dict() == book.to_dict()
    assert restored.objective("obj-1") == book.objective("obj-1")


def test_book_round_trip_keeps_pending_whispers() -> None:
    book = make_book()
    propose_hunt(book)
    book.record_whisper("obj-1", "pop_0007_g01m01", meet_premade("prontera 156,22", "19:00"))
    restored = GroupObjectiveBook.from_dict(book.to_dict())
    assert restored.to_dict() == book.to_dict()


def test_kind_constants_are_exhaustive() -> None:
    assert set(OBJECTIVE_KINDS) == {"hunt", "farm", "town"}
    assert {OBJECTIVE_PROPOSED, OBJECTIVE_INVITED, OBJECTIVE_ACTIVE, OBJECTIVE_DISSOLVED} == {
        "proposed",
        "invited",
        "active",
        "dissolved",
    }


# -- the injected roster (agent-level knowledge, character-level identity) ------


def test_seed_roster_knows_group_character_names_without_contact() -> None:
    """At creation every group member knows the roster: persona ids AND the
    in-game character names — no chat, party or whisper ever exchanged."""
    population = pop_2_2_1()
    by_group: dict[str, list[str]] = {}
    for persona in population.personas:
        if persona.group_id is not None:
            by_group.setdefault(persona.group_id, []).append(persona.persona_id)
    names = {p.persona_id: p.name for p in population.personas}
    save_maps = {p.persona_id: p.save_map for p in population.personas}
    for group_id, members in by_group.items():
        ledger = RelationshipLedger()
        seed_roster(ledger, population)
        # The whole roster resolved to character names, zero in-game contact.
        for member in members:
            assert ledger.display_name(member) == names[member]
            assert ledger.persona_of(names[member]) == member
        assert ledger.group_members(group_id) == tuple(members)
        assert ledger.group_map(group_id) == save_maps[members[0]]
        # The decide-context group line shows CHARACTER names, not bare ids.
        lines = ledger.context_lines(members[0])
        assert any(names[m] in line for line in lines for m in members[1:])


def test_seed_roster_leaves_solos_registered_but_ungrouped() -> None:
    population = pop_2_2_1()
    solo = next(p for p in population.personas if p.group_id is None)
    ledger = RelationshipLedger()
    seed_roster(ledger, population)
    assert ledger.display_name(solo.persona_id) == solo.name
    assert ledger.group_of(solo.persona_id) is None


# -- the ledger carries the book (reconnect continuity) -------------------------


def test_ledger_json_carries_objectives_across_reconnect(tmp_path) -> None:
    population = pop_2_2_1()
    leader = next(p for p in population.personas if p.group_id is not None)
    ledger = RelationshipLedger(persona_id=leader.persona_id)
    seed_roster(ledger, population)
    member = next(m for m in ledger.group_members(leader.group_id) if m != leader.persona_id)
    ledger.objectives.propose(
        "obj-1",
        leader.group_id,
        leader.persona_id,
        "hunt",
        "prt_fild08",
        target="porings",
        invited=(member,),
    )
    ledger.objectives.mark_invited("obj-1", (member,))
    path = tmp_path / "relations.json"
    ledger.save(path)
    restored = RelationshipLedger(path=path)
    objective = restored.objectives.objective("obj-1")
    assert objective is not None
    assert objective.status == OBJECTIVE_INVITED
    assert objective.target == "porings"


def test_a_fresh_ledger_has_an_empty_book() -> None:
    ledger = RelationshipLedger()
    assert ledger.objectives.joined_objectives() == ()
    assert RelationshipLedger.from_dict(ledger.to_dict()).to_dict() == ledger.to_dict()


# -- decide-context objective lines ----------------------------------------------


def test_leader_context_suggests_formation_when_window_opens() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("lead", "PartyLeader")
    ledger.register_persona("mate", "VelDrop")
    ledger.seed_group("g01", ("lead", "mate"), save_map="prt_fild08")
    lines = ledger.context_lines("lead", online_members=("lead", "mate"))
    suggestion = [line for line in lines if "you lead" in line]
    assert len(suggestion) == 1
    assert "your group g01 is online (2/2)" in suggestion[0]
    assert "suggests inviting VelDrop" in suggestion[0]


def test_no_formation_suggestion_without_copresent_friends() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("lead", "PartyLeader")
    ledger.register_persona("mate", "VelDrop")
    ledger.seed_group("g01", ("lead", "mate"))
    assert not any("you lead" in line for line in ledger.context_lines("lead"))
    assert not any(
        "you lead" in line
        for line in ledger.context_lines("lead", online_members=("lead", "stranger"))
    )


def test_live_objective_replaces_the_formation_suggestion() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("lead", "PartyLeader")
    ledger.register_persona("mate", "VelDrop")
    ledger.seed_group("g01", ("lead", "mate"))
    ledger.objectives.propose("obj-1", "g01", "lead", "hunt", "prt_fild08", target="porings")
    lines = ledger.context_lines("lead", online_members=("lead", "mate"))
    assert not any("suggests inviting" in line for line in lines)
    assert any("your objective: hunt porings on prt_fild08" in line for line in lines)


def test_member_context_shows_invited_then_active_lines() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("lead", "PartyLeader")
    ledger.register_persona("mate", "VelDrop")
    ledger.seed_group("g01", ("lead", "mate"))
    ledger.objectives.propose("obj-1", "g01", "lead", "hunt", "prt_fild08", target="porings")
    ledger.objectives.mark_invited("obj-1", ("mate",))
    invited_lines = [line for line in ledger.context_lines("mate") if "invited" in line]
    assert any("hunt porings on prt_fild08 by PartyLeader" in line for line in invited_lines)
    assert any("accept the party invite" in line for line in invited_lines)
    ledger.objectives.record_join("obj-1", "mate")
    active_lines = [line for line in ledger.context_lines("mate") if "active objective" in line]
    assert any("hunt porings on prt_fild08" in line for line in active_lines)
    assert any("your goal aligns" in line for line in active_lines)


def test_objective_lines_survive_the_context_cap() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("lead", "PartyLeader")
    ledger.register_persona("mate", "VelDrop")
    ledger.seed_group("g01", ("lead", "mate"))
    for i in range(20):
        ledger.register_persona(f"p{i:02d}", f"Peer{i:02d}")
        ledger.record_chat_exchange(f"p{i:02d}", "mate", ts=0.0)
    ledger.objectives.propose("obj-1", "g01", "lead", "hunt", "prt_fild08", target="porings")
    ledger.objectives.mark_invited("obj-1", ("mate",))
    lines = ledger.context_lines("mate", max_lines=3)
    assert len(lines) == 3
    assert any("invited" in line for line in lines)


# -- the coordinator: emissions are the ONLY channel ------------------------------


def make_pair(
    leader_id: str = "lead", mate_id: str = "mate", group_id: str = "g01"
) -> tuple[RelationshipLedger, GroupCoordinator, GroupCoordinator]:
    """A seeded 2-member group: PER-AGENT ledgers (own views) + coordinators."""
    roster = ((leader_id, "PartyLeader"), (mate_id, "VelDrop"))

    def build_viewer_ledger() -> RelationshipLedger:
        ledger = RelationshipLedger()
        for persona_id, name in roster:
            ledger.register_persona(persona_id, name)
        ledger.seed_group(group_id, (leader_id, mate_id), save_map="prt_fild08")
        return ledger

    leader_ledger = build_viewer_ledger()
    return (
        leader_ledger,
        GroupCoordinator(leader_ledger, leader_id),
        GroupCoordinator(build_viewer_ledger(), mate_id),
    )


def join_call() -> ChatLine:
    return ChatLine(
        channel="public", sender="PartyLeader", text="hunting porings prt_fild08, join me", at=1.0
    )


def test_formation_suggestion_names_the_online_friends() -> None:
    _, leader, mate = make_pair()
    suggestion = leader.formation_suggestion(("lead", "mate"))
    assert suggestion is not None
    assert suggestion.group_id == "g01"
    assert suggestion.invitee_ids == ("mate",)
    # Nobody but the formation leader gets a suggestion.
    assert mate.formation_suggestion(("lead", "mate")) is None
    # A lone online member is no window at all.
    assert leader.formation_suggestion(("lead",)) is None
    assert leader.formation_suggestion(("stranger", "mate")) is None


def test_form_emits_only_in_game_packets() -> None:
    _, leader, _ = make_pair()
    objective, actions = leader.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=False,
    )
    assert objective.status == OBJECTIVE_INVITED
    assert {type(action) for action in actions} <= {InviteToParty, PartyChat, Say, WhisperTo}
    invites = [a for a in actions if isinstance(a, InviteToParty)]
    assert [i.player for i in invites] == ["VelDrop"]  # invited by the KNOWN character name
    announcement = next(a for a in actions if isinstance(a, Say))
    assert announcement.text == "hunting porings prt_fild08, join me"
    inviting = [a for a in actions if isinstance(a, (Say, PartyChat)) and "inviting" in a.text]
    assert any("VelDrop" in a.text for a in inviting)


def test_form_in_party_uses_party_chat_not_public_say() -> None:
    _, leader, _ = make_pair()
    _, actions = leader.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=True,
    )
    assert any("join me" in c.text for c in actions if isinstance(c, PartyChat))
    assert [a for a in actions if isinstance(a, Say)] == []


def test_form_records_meet_whisper_for_offline_members_only() -> None:
    ledger, leader, mate = make_pair()
    ledger.register_persona("late", "LateComer")
    ledger.seed_group("g01", ("lead", "mate", "late"), save_map="prt_fild08")
    objective, actions = leader.form(
        "farm",
        map_name="prontera",
        target="jellopy",
        online_members=("lead", "mate"),
        in_party=False,
        meet_where="prontera 156,22",
        meet_when="19:00",
    )
    assert objective.status == OBJECTIVE_INVITED
    # Only the ONLINE mate gets an invite packet; the offline member gets none.
    assert [a.player for a in actions if isinstance(a, InviteToParty)] == ["VelDrop"]
    assert not [a for a in actions if isinstance(a, WhisperTo)]
    # The meet whisper stays recorded until BOTH are online, then delivers once.
    assert leader.deliver_whispers(("lead", "mate")) == ()
    delivered = leader.deliver_whispers(("lead", "mate", "late"))
    assert len(delivered) == 1
    whisper = delivered[0]
    assert isinstance(whisper, WhisperTo)
    assert whisper.to == "LateComer"
    assert whisper.text == "meet at prontera 156,22 at 19:00"
    assert leader.deliver_whispers(("lead", "mate", "late")) == ()


def test_member_joins_through_the_in_game_invite_only() -> None:
    _, leader, mate = make_pair()
    _, actions = leader.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=False,
    )
    # The member's own view: it HEARD the public announcement and got the invite.
    announcement = next(a for a in actions if isinstance(a, Say))
    mate.note_announcement("PartyLeader", announcement.text)
    joined = mate.accept_invite_from("PartyLeader")
    assert joined is not None
    assert joined.status == OBJECTIVE_ACTIVE
    assert joined.accepted == ("mate",)
    # The leader observes the party join (in-game event) and welcomes.
    welcome = leader.record_party_join("VelDrop")
    assert any(isinstance(a, PartyChat) and "VelDrop" in a.text for a in welcome)
    objective = leader.book.objectives_for_group("g01", statuses=(OBJECTIVE_ACTIVE,))[0]
    assert objective.accepted == ("mate",)


def test_member_without_the_announcement_joins_unaligned() -> None:
    _, _, mate = make_pair()
    # An invite alone (no heard announcement) cannot invent an objective.
    assert mate.accept_invite_from("PartyLeader") is None


def test_schedule_close_dissolves_and_says_goodbye() -> None:
    _, leader, mate = make_pair()
    leader.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=False,
    )
    mate.note_announcement("PartyLeader", "hunting porings prt_fild08, join me")
    mate.accept_invite_from("PartyLeader")
    leader.record_party_join("VelDrop")
    # The window closes: the mate disconnects.
    gone = leader.tick(("lead",), in_party=False)
    assert any(isinstance(a, Say) and a.text == "gg wp" for a in gone)
    objective = leader.book.objectives_for_group("g01", statuses=(OBJECTIVE_DISSOLVED,))[0]
    assert objective.reason == "schedule window closed"
    member_gone = mate.tick(("lead",), in_party=False)
    assert any(isinstance(a, Say) and a.text == "gg wp" for a in member_gone)
    assert mate.book.joined_objectives() == ()
    # An open window keeps everything alive.
    ledger2, leader2, _ = make_pair()
    del ledger2
    leader2.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=False,
    )
    assert leader2.tick(("lead", "mate"), in_party=False) == ()


def test_solo_drift_responds_to_public_join_call_affinity_gated() -> None:
    ledger, _, _ = make_pair()
    ledger.register_persona("solo", "Lorawing")
    solo = GroupCoordinator(ledger, "solo")
    # Neutral stranger announcing a hunt: the solo may whisper a join request.
    reply = solo.outsider_reply(join_call(), in_party=False, job="Swordsman", level=42)
    assert isinstance(reply, WhisperTo)
    assert reply.to == "PartyLeader"
    assert reply.text == "can I join? Swordsman lvl 42"
    # Already in a party: no outsider channel.
    assert solo.outsider_reply(join_call(), in_party=True, job="Swordsman", level=42) is None


def test_solo_with_bad_history_never_whispers() -> None:
    ledger, _, _ = make_pair()
    ledger.register_persona("solo", "Lorawing")
    # A griefer: the solo's friendship with the announcer is negative. No
    # production path yields negative agent-agent friendship yet (dead-weight
    # and gossip are human-directed); this boundary pin holds the gate closed
    # for the first negative producer.
    ledger._friendship[_pair_key("solo", "lead")] = -0.6
    solo = GroupCoordinator(ledger, "solo")
    assert solo.outsider_reply(join_call(), in_party=False, job="Swordsman", level=42) is None
    # Everyday chat never triggers the outsider channel either.
    everyday = ChatLine(channel="public", sender="PartyLeader", text="gg wp", at=2.0)
    assert solo.outsider_reply(everyday, in_party=False, job="Swordsman", level=42) is None
    # Unknown senders (not in the injected roster) are treated as neutral.
    stranger_line = ChatLine(
        channel="public", sender="Mystery", text="hunting porings prt_fild08, join me", at=3.0
    )
    reply = solo.outsider_reply(stranger_line, in_party=False, job="Swordsman", level=42)
    assert isinstance(reply, WhisperTo)
    assert reply.to == "Mystery"


def test_group_members_are_not_outsiders() -> None:
    _, _, mate = make_pair()
    assert mate.outsider_reply(join_call(), in_party=False, job="Swordsman", level=42) is None


def test_every_emission_is_a_game_packet() -> None:
    """Emission purity: coordination leaves an agent ONLY as wire packets."""
    packet_types = {InviteToParty, PartyChat, Say, WhisperTo}
    ledger, leader, mate = make_pair()
    ledger.register_persona("solo", "Lorawing")
    solo = GroupCoordinator(ledger, "solo")
    outsider = solo.outsider_reply(join_call(), in_party=False, job="Swordsman", level=42)
    emissions = [
        leader.form(
            "hunt",
            map_name="prt_fild08",
            target="porings",
            online_members=("lead", "mate"),
            in_party=False,
        )[1],
        leader.deliver_whispers(("lead", "mate")),
        leader.record_party_join("VelDrop"),
        leader.tick((), in_party=False),
        (outsider,) if outsider is not None else (),
    ]
    for emission in emissions:
        for action in emission or ():
            assert type(action) in packet_types, f"non-packet emission: {action!r}"


# -- the brain hook: the objective question, the alignment, the outsider reply ----


class CapturingModel:
    """Scripted answers that also record every received request (the fake)."""

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        self._scripted = ScriptedDecisionModel(answers=answers)
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return self._scripted.decide(request)


def make_state(**overrides: object) -> BotState:
    """A deterministic BotState factory (mirrors tests/test_relations.py)."""
    base: dict[str, Any] = {
        "name": "PartyLeader",
        "job": "Swordsman",
        "base_level": 42,
        "hp": 800,
        "max_hp": 1000,
        "sp": 60,
        "max_sp": 80,
        "map_name": "prt_fild08",
        "x": 120,
        "y": 74,
        "goal": Goal.GRIND,
        "in_party": False,
        "nearby": (),
        "inventory": {"Red Potion": 5},
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(overrides)
    return BotState(**base)


def make_brain(
    coordination: BoundCoordinator | None = None,
    answers: dict[str, Any] | None = None,
    **kwargs: Any,
) -> tuple[EventDrivenBrain, CapturingModel]:
    model = CapturingModel(answers=answers)
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        coordination=coordination,
        **kwargs,
    )
    return brain, model


def leader_setup(
    kind_online: tuple[str, ...] = ("lead", "mate"),
) -> tuple[BoundCoordinator, GroupCoordinator]:
    _, leader, _ = make_pair()
    hook = BoundCoordinator(
        leader,
        online=lambda: kind_online,
        meet_where="prontera 156,22",
        meet_when="19:00",
    )
    return hook, leader


def test_brain_offers_the_objective_question_only_when_a_window_opens() -> None:
    hook, _ = leader_setup()
    brain, model = make_brain(coordination=hook, answers=base_answers())
    result = brain.handle_event(make_state(), Heartbeat(seq=1))
    assert result.actions == ()
    assert "objective_action" in model.requests[0]["questions"]
    assert "hunt" in model.requests[0]["questions"]["objective_action"]["criteria"]
    # A closed window adds no question.
    hook_closed, _ = leader_setup(kind_online=("lead",))
    brain2, model2 = make_brain(coordination=hook_closed, answers=base_answers())
    brain2.handle_event(make_state(), Heartbeat(seq=1))
    assert "objective_action" not in model2.requests[0]["questions"]


def test_brain_without_coordination_never_adds_the_question() -> None:
    brain, model = make_brain(answers=base_answers())
    result = brain.handle_event(make_state(), Heartbeat(seq=1))
    assert result.actions == ()
    assert "objective_action" not in model.requests[0]["questions"]


def test_brain_forms_the_objective_from_the_review_answer() -> None:
    hook, leader = leader_setup()
    answers = base_answers()
    answers["objective_action"] = {"type": "choice", "choice": "hunt", "confidence": 0.9}
    answers["farm_target"] = {"type": "choice", "choice": "porings", "confidence": 0.9}
    brain, _ = make_brain(coordination=hook, answers=answers)
    result = brain.handle_event(make_state(), Heartbeat(seq=1))
    invites = [a for a in result.actions if isinstance(a, InviteToParty)]
    assert [i.player for i in invites] == ["VelDrop"]
    assert any(isinstance(a, Say) and "join me" in a.text for a in result.actions)
    live = leader.book.live_objectives()
    assert len(live) == 1
    assert live[0].status == OBJECTIVE_INVITED
    assert live[0].target == "porings"


def test_brain_delivers_due_whispers_during_review() -> None:
    ledger, leader, _ = make_pair()
    ledger.register_persona("late", "LateComer")
    ledger.seed_group("g01", ("lead", "mate", "late"), save_map="prt_fild08")
    hook = BoundCoordinator(leader, online=lambda: ("lead", "mate", "late"))
    leader.form(
        "hunt",
        map_name="prt_fild08",
        target="porings",
        online_members=("lead", "mate"),
        in_party=False,
        meet_where="prontera 156,22",
        meet_when="19:00",
    )
    brain, _ = make_brain(coordination=hook, answers=base_answers())
    result = brain.handle_event(make_state(), Heartbeat(seq=2))
    whispers = [a for a in result.actions if isinstance(a, WhisperTo)]
    assert [w.to for w in whispers] == ["LateComer"]
    assert whispers[0].text == "meet at prontera 156,22 at 19:00"
    # Delivered exactly once: the next review has nothing left to send.
    again = brain.handle_event(make_state(), Heartbeat(seq=3))
    assert not [a for a in again.actions if isinstance(a, WhisperTo)]


def test_brain_pins_the_goal_while_an_objective_is_active() -> None:
    _, _, mate = make_pair()
    mate.note_announcement("PartyLeader", "hunting porings prt_fild08, join me")
    mate.accept_invite_from("PartyLeader")
    hook = BoundCoordinator(mate, online=lambda: ("lead", "mate"))
    answers = base_answers()
    answers["change_goal"] = {"type": "choice", "choice": "town", "confidence": 0.9}
    brain, _ = make_brain(coordination=hook, answers=answers)
    result = brain.handle_event(make_state(name="VelDrop", goal=Goal.GRIND), Heartbeat(seq=2))
    # The model said "town" but the ACTIVE objective wins for its duration.
    notes = " | ".join(result.notes)
    assert "objective alignment" in notes
    assert "hunt" in notes and "prt_fild08" in notes


def test_brain_farm_plan_targets_the_objective_map() -> None:
    _, _, mate = make_pair()
    mate.note_announcement("PartyLeader", "farming jellopy prontera, join me")
    mate.accept_invite_from("PartyLeader")
    hook = BoundCoordinator(mate, online=lambda: ("lead", "mate"))
    answers = base_answers()
    answers["change_goal"] = {"type": "choice", "choice": "farm", "confidence": 0.9}
    brain, _ = make_brain(
        coordination=hook,
        answers=answers,
        spawn_species=lambda map_name: ("Poring",),  # noqa: ARG005 - map-agnostic fixture
    )
    brain.handle_event(
        make_state(name="VelDrop", goal=Goal.FARM_ITEM, map_name="gef_fild00"), Heartbeat(seq=2)
    )
    plan = brain.current_plan
    assert plan is not None
    # The objective's map wins over the bot's current map for the farm session.
    assert plan.map_name == "prontera"
    assert plan.target_mobs == ("Poring",)


def test_brain_records_the_member_join_on_accept() -> None:
    _, _, mate = make_pair()
    mate.note_announcement("PartyLeader", "hunting porings prt_fild08, join me")
    hook = BoundCoordinator(mate, online=lambda: ("lead", "mate"))
    answers = base_answers()
    answers["accept_invite"] = {"type": "noul", "noul": 0.9}  # the friend's invite: accept
    brain, _ = make_brain(coordination=hook, answers=answers)
    state = make_state(
        name="VelDrop", pending_invites=(PartyInvite(from_name="PartyLeader", at=2.0),)
    )
    result = brain.handle_event(
        state, InviteReceived(invite=PartyInvite(from_name="PartyLeader", at=2.0))
    )
    assert any(isinstance(a, AcceptInvite) for a in result.actions)
    joined = mate.book.joined_objectives()
    assert len(joined) == 1
    assert joined[0].status == OBJECTIVE_ACTIVE


def test_brain_solo_outsider_replies_to_a_public_join_call() -> None:
    ledger, _, _ = make_pair()
    ledger.register_persona("solo", "Lorawing")
    solo = GroupCoordinator(ledger, "solo")
    hook = BoundCoordinator(solo, online=lambda: ())
    brain, _ = make_brain(coordination=hook, answers=base_answers())
    line = ChatLine(
        channel="public", sender="PartyLeader", text="hunting porings prt_fild08, join me", at=1.0
    )
    result = brain.handle_event(make_state(name="Lorawing"), ChatHeard(line=line))
    whispers = [a for a in result.actions if isinstance(a, WhisperTo)]
    assert [w.to for w in whispers] == ["PartyLeader"]
    assert result.escalated is False


# -- the seed-7 week: the full offline loop through the fake packet bus ----------

HearChannel = Literal["party", "public", "whisper"]


class FakePacketBus:
    """The server between the hosts: packet-level delivery, nothing else.

    Coordination reaches another agent ONLY as these packets (the invite
    packet, public/party chat, whispers) — the bus is the offline proof that
    no out-of-band channel exists in the loop.
    """

    def __init__(self) -> None:
        self.rigs: dict[str, AgentRig] = {}
        self.online: set[str] = set()
        self.trace: list[str] = []
        self._inviter: dict[str, str] = {}  # invited persona -> inviting persona

    def add(self, rig: AgentRig) -> None:
        self.rigs[rig.persona_id] = rig
        self.online.add(rig.persona_id)

    def online_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.online))

    def rig_by_name(self, name: str) -> AgentRig:
        for rig in self.rigs.values():
            if rig.name == name:
                return rig
        msg = f"no agent named {name!r}"
        raise ValueError(msg)

    def submit(self, sender_id: str, actions: Sequence[object]) -> None:
        for action in actions:
            self._deliver(sender_id, action)

    def _deliver(self, sender_id: str, action: object) -> None:
        sender = self.rigs[sender_id]
        match action:
            case InviteToParty(player=name):
                target = self.rig_by_name(name)
                self.trace.append(f"party-invite packet: {sender.name} invites {name}")
                self._inviter[target.persona_id] = sender_id
                received = target.brain.handle_event(
                    target.state(),
                    InviteReceived(invite=PartyInvite(from_name=sender.name, at=1.0)),
                )
                self.submit(target.persona_id, received.actions)
            case AcceptInvite():
                self.trace.append(f"party-invite packet: {sender.name} accepts")
                sender.in_party = True
                leader_id = self._inviter.get(sender.persona_id)
                if leader_id is not None:
                    leader = self.rigs[leader_id]
                    leader.in_party = True
                    self.submit(leader_id, leader.coordinator.record_party_join(sender.name))
            case PartyChat(text):
                self.trace.append(f"party chat: {sender.name}: {text}")
                for rig in self.rigs.values():
                    if (
                        rig.persona_id != sender_id
                        and rig.in_party
                        and rig.persona_id in self.online
                    ):
                        self._hear(rig, sender, "party", text)
            case Say(text):
                self.trace.append(f"public chat: {sender.name}: {text}")
                for rig in self.rigs.values():
                    if rig.persona_id != sender_id and rig.persona_id in self.online:
                        self._hear(rig, sender, "public", text)
            case WhisperTo(to=name, text=text):
                target = self.rig_by_name(name)
                self.trace.append(f"whisper: {sender.name} -> {name}: {text}")
                self._hear(target, sender, "whisper", text)
            case _:
                self.trace.append(f"(game action): {sender.name}: {type(action).__name__}")

    def _hear(self, rig: AgentRig, sender: AgentRig, channel: HearChannel, text: str) -> None:
        line = ChatLine(channel=channel, sender=sender.name, text=text, at=1.0)
        received = rig.brain.handle_event(rig.state(), ChatHeard(line=line))
        self.submit(rig.persona_id, received.actions)

    def heartbeat(self, persona_id: str, **state_overrides: Any) -> TickResult:
        rig = self.rigs[persona_id]
        result = rig.brain.handle_event(rig.state(**state_overrides), Heartbeat(seq=0))
        self.submit(persona_id, result.actions)
        return result

    def channels_used(self) -> set[str]:
        return {line.split(":", 1)[0] for line in self.trace}


class AgentRig:
    """One agent's host: its ledger, coordinator, brain and mutable state."""

    def __init__(self, bus: FakePacketBus, persona: Any, answers: list[dict[str, Any]]) -> None:
        self.persona_id = persona.persona_id
        self.name = persona.name
        self.group_id = persona.group_id
        self.in_party = False
        self.goal: Goal = Goal.GRIND
        self.ledger = RelationshipLedger()
        seed_roster(self.ledger, pop_2_2_1())  # the injected roster (creation-time)
        self.coordinator = GroupCoordinator(self.ledger, self.persona_id)
        self.hook = BoundCoordinator(
            self.coordinator,
            online=bus.online_names,
            meet_where="prontera 156,22",
            meet_when="19:00",
        )
        self.model = CapturingModel(answers=answers)
        self.brain = EventDrivenBrain(
            decision_model=self.model,
            chat=StaticChatGenerator(["gg", "nice", "ty", "hi", "ok", "sure", "later"]),
            coordination=self.hook,
            social_view=lambda: self.ledger.context_lines(
                self.persona_id, online_members=bus.online_names()
            ),
        )

    def state(self, **overrides: Any) -> BotState:
        base: dict[str, Any] = {
            "name": self.name,
            "job": "Swordsman",
            "base_level": 42,
            "hp": 800,
            "max_hp": 1000,
            "sp": 60,
            "max_sp": 80,
            "map_name": "prt_fild08",
            "x": 120,
            "y": 74,
            "goal": self.goal,
            "in_party": self.in_party,
            "nearby": (),
            "inventory": {"Red Potion": 5},
            "pending_invites": (),
            "recent_chat": (),
        }
        base.update(overrides)
        return BotState(**base)


def make_week() -> tuple[FakePacketBus, dict[str, AgentRig]]:
    """The seed-7 example: two 2-member friend groups + 1 solo, all wired.

    Fixed answer mappings (not queues): every decide is stateless, and the
    coordination guard re-checks the window before forming, so a repeated
    ``objective_action`` answer cannot double-form.
    """
    bus = FakePacketBus()
    keep = base_answers()
    leader_a = {
        **keep,
        "objective_action": {"type": "choice", "choice": "hunt"},
        "farm_target": {"type": "choice", "choice": "porings"},
    }
    leader_b = {
        **keep,
        "objective_action": {"type": "choice", "choice": "farm"},
        "farm_target": {"type": "choice", "choice": "jellopy"},
    }
    member = {
        **keep,
        "accept_invite": {"type": "noul", "noul": 0.9},
        "change_goal": {"type": "choice", "choice": "town"},
    }
    by_group: dict[str, list[Any]] = {}
    solo_persona: Any = None
    for persona in pop_2_2_1().personas:
        if persona.group_id is None:
            solo_persona = persona
        else:
            by_group.setdefault(persona.group_id, []).append(persona)  # first = leader
    rigs: dict[str, AgentRig] = {}
    leader_answers = {"hunt": leader_a, "farm": leader_b}
    for index, group_id in enumerate(sorted(by_group)):
        members = by_group[group_id]
        kind = "hunt" if index == 0 else "farm"
        leader_rig = AgentRig(bus, members[0], leader_answers[kind])
        mate_rig = AgentRig(bus, members[1], dict(member))
        rigs[f"lead-{group_id}"] = leader_rig
        rigs[f"mate-{group_id}"] = mate_rig
        bus.add(leader_rig)
        bus.add(mate_rig)
    solo_rig = AgentRig(bus, solo_persona, dict(keep))
    rigs["solo"] = solo_rig
    bus.add(solo_rig)
    return bus, rigs


def test_seed7_week_full_loop_coordination_through_game_socials() -> None:
    bus, rigs = make_week()
    groups = sorted(rig.group_id for rig in rigs.values() if rig.group_id is not None)
    g_a, g_b = groups[0], groups[1]
    lead, mate = rigs[f"lead-{g_a}"], rigs[f"mate-{g_a}"]
    lead_b, mate_b = rigs[f"lead-{g_b}"], rigs[f"mate-{g_b}"]

    # t1: the schedule window opens; the LEADER's review authors the objective.
    bus.heartbeat(lead.persona_id)
    social = lead.model.requests[0]["state"]["social_relations"]
    assert "you lead" in social  # the decide context carried the formation window
    # The whole proposed -> invited -> active lifecycle ran inside the review:
    # the invites went out on the wire and the member accepted in-game.
    objective = lead.coordinator.book.objectives_for_group(g_a, statuses=(OBJECTIVE_ACTIVE,))
    assert len(objective) == 1
    assert objective[0].accepted == (mate.persona_id,)
    assert mate.in_party and lead.in_party
    assert any("accepts" in line for line in bus.trace)

    # t2: the member's goal review ADOPTS the objective (the model said town).
    member_review = bus.heartbeat(mate.persona_id)
    assert any("objective alignment" in note for note in member_review.notes)

    # The solo drift: it heard the PUBLIC join call and whispered a join request.
    join_call_line = f"whisper: {solo_name if (solo_name := rigs['solo'].name) else ''} -> "
    assert any(
        join_call_line in line and "can I join? Swordsman lvl 42" in line for line in bus.trace
    )
    # The leader received the whisper IN GAME (its escalation path answered).
    assert any(f"public chat: {lead.name}: gg" in line for line in bus.trace)

    # t3: the second group's leader forms its own objective the same way.
    bus.heartbeat(lead_b.persona_id)
    assert len(lead_b.coordinator.book.live_objectives()) == 1
    assert mate_b.in_party

    # The welcome premade fired at each join transition.
    assert sum(f"party chat: {lead.name}: welcome, {mate.name}!" in l for l in bus.trace) == 1
    assert sum(f"welcome, {mate_b.name}!" in line for line in bus.trace) == 1

    # t4: the schedule window closes (only the leaders stay online).
    bus.online -= {mate.persona_id, mate_b.persona_id, rigs["solo"].persona_id}
    gone = bus.heartbeat(lead.persona_id)
    # The goodbye premade fires on the leader's current channel (in a party).
    assert any(isinstance(a, (Say, PartyChat)) and a.text == "gg wp" for a in gone.actions)
    dissolved = lead.coordinator.book.objectives_for_group(g_a, statuses=(OBJECTIVE_DISSOLVED,))
    assert dissolved[0].reason == "schedule window closed"
    bus.heartbeat(mate.persona_id)
    member_dissolved = mate.coordinator.book.objectives_for_group(
        g_a, statuses=(OBJECTIVE_DISSOLVED,)
    )
    assert len(member_dissolved) == 1

    # Every trace line is an in-game channel — no out-of-band delivery exists.
    assert bus.channels_used() <= {
        "party-invite packet",
        "public chat",
        "party chat",
        "whisper",
        "(game action)",
    }


# -- the no-telepathy guard -------------------------------------------------------


def test_no_api_writes_another_agents_state_or_chat() -> None:
    """The coordination surface exposes NO cross-agent writer: one agent can
    never hand another agent its ledger/book/brain/state. Coordination leaves
    an agent only as emitted game packets (the emission-purity pin lives with
    the coordinator tests)."""
    forbidden_params = {"ledger", "book", "brain", "other_agent"}
    for module in (relations_module, objectives_module):
        for name, member in vars(module).items():
            if not inspect.isclass(member) or member.__module__ != module.__name__:
                continue
            for method_name, method in vars(member).items():
                if method_name.startswith("_"):
                    continue
                try:
                    signature = inspect.signature(method)
                except TypeError, ValueError:
                    continue
                params = {p for p in signature.parameters if p != "self"}
                clashes = params & forbidden_params
                assert not clashes, (
                    f"{module.__name__}.{name}.{method_name} accepts {sorted(clashes)}: "
                    "a cross-agent state writer must not exist — coordination travels "
                    "only as game packets"
                )
