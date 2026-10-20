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
from robots.domain.model import Goal
from robots.popgen import GeneratedPopulation, PopulationSpec, generate_population
from robots.society.objectives import (
    OBJECTIVE_ACTIVE,
    OBJECTIVE_DISSOLVED,
    OBJECTIVE_INVITED,
    OBJECTIVE_KINDS,
    OBJECTIVE_PROPOSED,
    GroupObjective,
    GroupObjectiveBook,
    meet_premade,
    objective_goal,
    objective_premade,
    parse_objective_premade,
    seed_roster,
)
from robots.society.relations import RelationshipLedger


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
