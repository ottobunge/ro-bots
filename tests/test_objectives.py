"""Group objectives: coordination-through-game-socials (the operator directive).

The agent-level + character-level planning layer where a group's shared goal
(a GroupObjective) travels ONLY through in-game socials: the leader forms it,
the party invites / party chat / whisper premades are the sole channels, and
members join by accepting the in-game invite — never by out-of-band state
mutation. The roster itself is injected knowledge at agent creation (persona
names + character names), which is how friends FIND each other in-game.
"""

import inspect
from typing import Any

import pytest

import robots.society.objectives as objectives_module
import robots.society.relations as relations_module
from robots.domain.actions import InviteToParty, PartyChat, Say, WhisperTo
from robots.domain.model import ChatLine, Goal
from robots.popgen import GeneratedPopulation, PopulationSpec, generate_population
from robots.society.objectives import (
    OBJECTIVE_ACTIVE,
    OBJECTIVE_DISSOLVED,
    OBJECTIVE_INVITED,
    OBJECTIVE_KINDS,
    OBJECTIVE_PROPOSED,
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


# -- the no-telepathy guard -------------------------------------------------------


def test_no_api_writes_another_agents_state_or_chat() -> None:
    """The coordination surface exposes NO cross-agent writer: one agent can
    never hand another agent its ledger/book/brain/state. Coordination leaves
    an agent only as emitted game packets (the emission-purity pin lives with
    the coordinator tests)."""
    forbidden_params = {"ledger", "book", "brain", "state", "bot_state", "other_agent"}
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
