"""The persona owns 1-N characters (feature/character-switching).

The popgen slice: every persona carries a character roster (the primary at
slot 0), extras are generated on demand with the play-style-constrained
class/build from the existing builds sidecars, and the artifacts (fixture
SQL, manifest, population.json) hold the account's characters — the rAthena
char-server provides 3 slots per account by default.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from robots.app.agent_runtime import load_manifest
from robots.popgen import (
    ACCOUNT_ID_BASE,
    BUILDS,
    CHAR_ID_BASE,
    CHAR_SLOTS,
    EXTRA_CHAR_ID_BASE,
    PopulationSpec,
    extend_roster,
    generate_population,
    load_population,
)

CHAR_ROW_RE = re.compile(
    r"INSERT INTO `char` \([^)]+\) VALUES \((\d+), (\d+), (\d+), X'([0-9a-f]*)'"
)


def make_spec(seed: int = 7, **overrides: Any) -> PopulationSpec:
    base: dict[str, Any] = {
        "friend_groups": 1,
        "friends_per_group": (2, 2),
        "solo_agents": 1,
        "seed": seed,
    }
    base.update(overrides)
    return PopulationSpec(**base)


def make_pop(seed: int = 7) -> Any:
    return generate_population(make_spec(seed=seed))


def persona_of(pop: Any, persona_id: str) -> Any:
    return next(p for p in pop.personas if p.persona_id == persona_id)


def char_rows(sql: str) -> list[tuple[int, int, int, str]]:
    return [
        (int(cid), int(aid), int(num), bytes.fromhex(hexed).decode())
        for cid, aid, num, hexed in CHAR_ROW_RE.findall(sql)
    ]


def build_family(build_path: str) -> str:
    return next(b.family for b in BUILDS if b.path == build_path)


# ----------------------------------------------------------- the primary slot


def test_every_persona_owns_a_primary_character() -> None:
    pop = make_pop()
    for index, persona in enumerate(pop.personas):
        assert persona.characters, "a persona owns at least its primary character"
        primary = persona.characters[0]
        assert primary.primary, "slot 0 is the primary"
        assert primary.name == persona.name
        assert primary.build == persona.build
        assert primary.char_num == 0
        assert primary.char_id == CHAR_ID_BASE + index


def test_roster_is_within_the_rathena_three_slots() -> None:
    assert CHAR_SLOTS == 3
    for persona in make_pop().personas:
        assert len(persona.characters) <= CHAR_SLOTS


# ------------------------------------------------------- on-demand extension


def test_extend_roster_adds_a_playstyle_constrained_character() -> None:
    pop = make_pop()
    target = pop.personas[0]
    extended, character = extend_roster(pop, target.persona_id)

    assert pop is not extended, "popgen objects are immutable: extension returns a new one"
    roster = persona_of(extended, target.persona_id).characters
    assert [c.char_num for c in roster] == [0, 1]
    assert character.char_num == 1
    assert character.name != target.name
    assert character.name not in {p.name for p in pop.personas}
    # the play-style constraint: the extra stays in the primary's class family
    assert build_family(character.build) == build_family(target.build)
    assert character.build in {b.path for b in BUILDS}
    assert character.char_id >= EXTRA_CHAR_ID_BASE
    assert all(c.char_id != character.char_id for p in pop.personas for c in p.characters)


def test_extend_roster_is_deterministic_and_stackable() -> None:
    pop = make_pop()
    target_id = pop.personas[0].persona_id
    first_pop, first_char = extend_roster(pop, target_id)
    second_pop, second_char = extend_roster(first_pop, target_id)

    again_pop, again_char = extend_roster(pop, target_id)
    assert again_pop.personas == first_pop.personas
    assert (
        again_char == first_char
    ), "the same seed, persona, and roster size generate the identical character"
    roster = persona_of(second_pop, target_id).characters
    assert [c.char_num for c in roster] == [0, 1, 2]
    assert second_char.name != first_char.name
    assert len({c.char_id for c in roster}) == len(roster)


def test_extend_roster_rejects_a_full_roster_and_unknown_personas() -> None:
    pop = make_pop()
    target_id = pop.personas[0].persona_id
    pop1, _ = extend_roster(pop, target_id)
    pop2, _ = extend_roster(pop1, target_id)
    with pytest.raises(ValueError, match="roster full"):
        extend_roster(pop2, target_id)
    with pytest.raises(ValueError, match="unknown persona"):
        extend_roster(pop, "pop_missing_zz")


# --------------------------------------------------------------- the fixtures


def test_fixture_sql_holds_the_account_characters() -> None:
    pop = make_pop()
    target = pop.personas[0]
    account_id = ACCOUNT_ID_BASE  # persona index 0
    single = char_rows(pop.fixture_sql)
    assert [row for row in single if row[1] == account_id] == [
        (target.characters[0].char_id, account_id, 0, target.name)
    ]

    extended, character = extend_roster(pop, target.persona_id)
    rows = [row for row in char_rows(extended.fixture_sql) if row[1] == account_id]
    assert [(row[0], row[2], row[3]) for row in rows] == [
        (target.characters[0].char_id, 0, target.name),
        (character.char_id, 1, character.name),
    ]
    assert len({row[0] for row in char_rows(extended.fixture_sql)}) == sum(
        len(p.characters) for p in extended.personas
    ), "every character has its own char_id"
    skill_rows = re.findall(
        r"INSERT INTO `skill` \([^)]+\) VALUES \((\d+), 1, 9, 0\);", extended.fixture_sql
    )
    assert len(skill_rows) == sum(len(p.characters) for p in extended.personas)


def test_multi_char_summary_rows_round_trip_through_load_population(
    tmp_path: Path,
) -> None:
    pop = make_pop()
    target_id = pop.personas[0].persona_id
    extended, _character = extend_roster(pop, target_id)
    path = tmp_path / "population.json"
    path.write_text(json.dumps(extended.summary(), indent=1) + "\n")

    loaded = load_population(path)
    for source in extended.personas:
        loaded_persona = persona_of(loaded, source.persona_id)
        assert loaded_persona.characters == source.characters

    row = extended.summary()["personas"][0]
    assert row["characters"] == [
        {"name": c.name, "char_num": c.char_num, "build": c.build, "char_id": c.char_id}
        for c in extended.personas[0].characters
    ]


def test_multi_char_manifest_rows_carry_the_roster(tmp_path: Path) -> None:
    pop = make_pop()
    target_id = pop.personas[0].persona_id
    extended, character = extend_roster(pop, target_id)
    rows = {row["persona_id"]: row for row in extended.manifest["accounts"]}

    target_row = rows[target_id]
    assert target_row["char_name"] == persona_of(extended, target_id).name
    assert target_row["characters"] == [
        {"name": c.name, "char_id": c.char_id, "slot": c.char_num, "build": c.build}
        for c in persona_of(extended, target_id).characters
    ]
    other_id = next(pid for pid in rows if pid != target_id)
    assert "characters" not in rows[other_id], "single-character rows keep the reference schema"

    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(extended.manifest))
    entries = load_manifest(path)
    entry = entries[target_id]
    assert [c.char_name for c in entry.roster] == [target_row["char_name"], character.name]
    assert [c.char_id for c in entry.roster] == [
        target_row["characters"][0]["char_id"],
        character.char_id,
    ]
    assert not entries[other_id].roster
