"""Population generator (feature/population-generator): pure, deterministic.

Covers the operator's criterion 3 slice: configure friend groups / solo
agents / friends-per-group range, generate a population, and emit the three
artifacts (manifest.json, fixture.sql, population.json) without a DB.
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
    GeneratedPopulation,
    PopulationSpec,
    generate_population,
    main,
    overlap_fraction,
    schedule_to_slots,
    weekly_online_hours,
)
from robots.society.models import Schedule
from robots.society.wants import Personality

REPO = Path(__file__).resolve().parents[1]
REFERENCE_MANIFEST = (
    REPO / "run/worlds/test-first-live-86e7c36895db/host-idle-3c6ada4253/host-manifest.json"
)
BUILDS_DIR = REPO / "run/knowledge/builds/pre-re"


def make_spec(seed: int = 7, **overrides: Any) -> PopulationSpec:
    base: dict[str, Any] = {
        "friend_groups": 2,
        "friends_per_group": (2, 4),
        "solo_agents": 1,
        "seed": seed,
    }
    base.update(overrides)
    return PopulationSpec(**base)


def group_members(pop: GeneratedPopulation, group_id: str) -> list[str]:
    return [p.persona_id for p in pop.personas if p.group_id == group_id]


# --------------------------------------------------------------- determinism


def test_same_spec_and_seed_generates_identical_population() -> None:
    first = generate_population(make_spec(seed=7))
    second = generate_population(make_spec(seed=7))
    assert first.personas == second.personas
    assert first.fixture_sql == second.fixture_sql
    assert first.manifest == second.manifest
    assert first.summary() == second.summary()


def test_different_seed_generates_different_population() -> None:
    first = generate_population(make_spec(seed=7))
    second = generate_population(make_spec(seed=8))
    assert first.personas != second.personas
    assert first.fixture_sql != second.fixture_sql


# --------------------------------------------------------------- group sizes


def test_group_sizes_within_configured_range() -> None:
    pop = generate_population(
        PopulationSpec(friend_groups=3, friends_per_group=(2, 4), solo_agents=0, seed=11)
    )
    groups = {p.group_id for p in pop.personas if p.group_id is not None}
    assert len(groups) == 3
    for group_id in sorted(groups):
        size = len(group_members(pop, group_id))
        assert 2 <= size <= 4


def test_every_persona_has_expected_fields() -> None:
    pop = generate_population(make_spec(seed=7))
    total = len(pop.personas)
    assert total >= 3
    for persona in pop.personas:
        assert persona.persona_id
        assert re.fullmatch(r"[A-Za-z0-9_]{4,23}", persona.name)
        assert persona.playstyle
        assert persona.build
        assert persona.save_map
        assert 0 <= persona.save_point[0] < 512
        assert 0 <= persona.save_point[1] < 512
        assert persona.schedule, "every persona needs at least one connect window"


# ------------------------------------------------------------ solo isolation


def test_solo_agents_have_no_group_and_no_overlap() -> None:
    pop = generate_population(make_spec(seed=7))
    solos = [p for p in pop.personas if p.group_id is None]
    assert len(solos) == 1
    for solo in solos:
        others = [p for p in pop.personas if p.persona_id != solo.persona_id]
        assert others, "solo isolation needs at least one other persona"
        for other in others:
            assert (
                overlap_fraction(solo.schedule, other.schedule) == 0.0
            ), f"{solo.persona_id} overlaps {other.persona_id}"


# ---------------------------------------------------------- schedule overlap


def test_group_members_share_at_least_half_their_connect_windows() -> None:
    for seed in range(20):
        pop = generate_population(
            PopulationSpec(friend_groups=3, friends_per_group=(2, 4), solo_agents=1, seed=seed)
        )
        groups = {p.group_id for p in pop.personas if p.group_id is not None}
        for group_id in groups:
            members = [p for p in pop.personas if p.group_id == group_id]
            for i, left in enumerate(members):
                for right in members[i + 1 :]:
                    fraction = overlap_fraction(left.schedule, right.schedule)
                    assert fraction >= 0.5, (seed, group_id, left, right, fraction)


def test_schedules_are_valid_weekly_windows_for_the_schedule_model() -> None:
    pop = generate_population(make_spec(seed=7))
    for persona in pop.personas:
        schedule = Schedule(persona.schedule)  # accepts our windows
        assert schedule.is_online((0, 0.0)) in (True, False)
        total = weekly_online_hours(persona.schedule)
        assert total > 0.0
        for day, start, end in persona.schedule:
            assert 0 <= day <= 6
            assert 0.0 <= start < 24.0
            assert 0.0 <= end < 24.0


# ------------------------------------------------------------ name uniqueness


def test_names_and_accounts_are_unique_and_rathena_safe() -> None:
    pop = generate_population(
        PopulationSpec(friend_groups=4, friends_per_group=(3, 6), solo_agents=3, seed=42)
    )
    names = [p.name for p in pop.personas]
    accounts = [p.account for p in pop.personas]
    persona_ids = [p.persona_id for p in pop.personas]
    assert len(set(names)) == len(names)
    assert len(set(accounts)) == len(accounts)
    assert len(set(persona_ids)) == len(persona_ids)
    for name in names:
        assert re.fullmatch(r"[A-Za-z0-9_]{4,23}", name)
    for account in accounts:
        assert re.fullmatch(r"[a-z0-9_]{4,23}", account)


# --------------------------------------------------------------- fixture SQL


def test_fixture_sql_matches_persona_counts_and_two_bot_pattern() -> None:
    pop = generate_population(make_spec(seed=7))
    n = len(pop.personas)
    sql = pop.fixture_sql
    assert sql.startswith("USE `ragnarok`;\n")
    login_rows = re.findall(r"INSERT INTO `login` \([^)]+\) VALUES \((\d+), ", sql)
    assert len(login_rows) == n
    account_ids = [int(a) for a in login_rows]
    assert len(set(account_ids)) == n
    assert all(a >= ACCOUNT_ID_BASE for a in account_ids)
    char_rows = re.findall(r"INSERT INTO `char` \([^)]+\) VALUES \((\d+), (\d+), ", sql)
    assert len(char_rows) == n
    char_ids = [int(c) for c, _ in char_rows]
    assert len(set(char_ids)) == n
    assert all(c >= CHAR_ID_BASE for c in char_ids)
    for _, account_id in char_rows:
        assert int(account_id) in account_ids
    # novice start: status_point 48, skill_point 9, Basic Skill lv 9 per char
    assert len(re.findall(r", 0, 48, 9\);", sql)) == n
    assert len(re.findall(r"INSERT INTO `skill` \([^)]+\) VALUES \(\d+, 1, 9, 0\);", sql)) == n
    # names travel as X'..' hex literals like two-bot-e09b999a23/fixture.sql
    assert len(re.findall(r"X'[0-9a-f]+'", sql)) >= 2 * n


def test_fixture_sql_persona_rows_carry_generated_names() -> None:
    pop = generate_population(make_spec(seed=7))
    for persona in pop.personas:
        hex_name = f"X'{persona.name.encode().hex()}'"
        assert hex_name in pop.fixture_sql


# --------------------------------------------------------------- manifest


def test_manifest_schema_matches_reference_host_manifest() -> None:
    pop = generate_population(make_spec(seed=7))
    reference = json.loads(REFERENCE_MANIFEST.read_text())
    assert set(pop.manifest) >= {"login_host", "login_port", "accounts"}
    assert isinstance(pop.manifest["login_host"], str)
    assert isinstance(pop.manifest["login_port"], int)
    reference_rows = reference["accounts"]
    assert reference_rows
    for row in pop.manifest["accounts"]:
        assert set(row) == set(reference_rows[0])
        assert isinstance(row["persona_id"], str)
        assert isinstance(row["account"], str)
        assert isinstance(row["password"], str)
        assert isinstance(row["char_name"], str)
        assert isinstance(row["pincode"], str)
        assert re.fullmatch(r"[0-9]{4}", row["pincode"])


def test_manifest_is_consumable_by_load_manifest(tmp_path: Path) -> None:
    pop = generate_population(make_spec(seed=7))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(pop.manifest))
    entries = load_manifest(path)
    assert set(entries) == {p.persona_id for p in pop.personas}
    for persona in pop.personas:
        entry = entries[persona.persona_id]
        assert entry.account == persona.account
        assert entry.char_name == persona.name
        assert entry.password == persona.password


# ------------------------------------------------------------------ builds


def test_builds_come_from_the_knowledge_sidecars() -> None:
    if not BUILDS_DIR.is_dir():  # pragma: no cover - repo layout guarantee
        pytest.skip("builds knowledge dir missing")
    sidecars = {p.stem: json.loads(p.read_text()) for p in BUILDS_DIR.glob("*.json")}
    assert "novice-bootstrap" in sidecars
    known = {b.path: b.playstyle for b in BUILDS}
    for path, playstyle in known.items():
        assert path in sidecars, path
        assert sidecars[path]["playstyle_axis"] == playstyle, path


def test_group_members_share_a_playstyle_family() -> None:
    pop = generate_population(make_spec(seed=7))
    groups = {p.group_id for p in pop.personas if p.group_id is not None}
    for group_id in groups:
        members = [p for p in pop.personas if p.group_id == group_id]
        families = {b.family for b in BUILDS if b.path == members[0].build}
        for member in members:
            member_families = {b.family for b in BUILDS if b.path == member.build}
            assert member_families & families, (group_id, member.build)


# --------------------------------------------------------------- personality


def test_personas_carry_a_valid_wants_personality() -> None:
    """Design section 3/5: popgen assigns a wants personality per agent."""
    pop = generate_population(make_spec(seed=7))
    assert pop.personas
    valid = {p.value for p in Personality}
    for persona in pop.personas:
        assert persona.personality in valid, (persona.persona_id, persona.personality)


def test_friend_groups_mix_personalities() -> None:
    """Design section 3: the friend group mixes personalities."""
    pop = generate_population(make_spec(seed=7, friends_per_group=(3, 4)))
    groups = {p.group_id for p in pop.personas if p.group_id is not None}
    assert groups
    for group_id in groups:
        members = [p for p in pop.personas if p.group_id == group_id]
        assert len({m.personality for m in members}) >= 2, group_id


def test_summary_rows_carry_the_personality() -> None:
    pop = generate_population(make_spec(seed=7))
    valid = {p.value for p in Personality}
    rows = pop.summary()["personas"]
    assert rows
    for row in rows:
        assert row["personality"] in valid


# -------------------------------------------------------------- spec checks


def test_invalid_specs_are_rejected() -> None:
    with pytest.raises(ValueError, match="friend_groups"):
        generate_population(
            PopulationSpec(friend_groups=-1, friends_per_group=(2, 4), solo_agents=0, seed=1)
        )
    with pytest.raises(ValueError, match="friends_per_group"):
        generate_population(
            PopulationSpec(friend_groups=1, friends_per_group=(4, 2), solo_agents=0, seed=1)
        )
    with pytest.raises(ValueError, match="friends_per_group"):
        generate_population(
            PopulationSpec(friend_groups=1, friends_per_group=(1, 4), solo_agents=0, seed=1)
        )
    with pytest.raises(ValueError, match="solo_agents"):
        generate_population(
            PopulationSpec(friend_groups=0, friends_per_group=(2, 4), solo_agents=-1, seed=1)
        )
    with pytest.raises(ValueError, match="empty population"):
        generate_population(
            PopulationSpec(friend_groups=0, friends_per_group=(2, 4), solo_agents=0, seed=1)
        )


# --------------------------------------------------------------------- CLI


def test_cli_writes_the_three_artifacts(tmp_path: Path, capsys: Any) -> None:
    out_dir = tmp_path / "example-popgen"
    rc = main(
        [
            "--friend-groups",
            "2",
            "--friends-min",
            "2",
            "--friends-max",
            "4",
            "--solo",
            "1",
            "--seed",
            "7",
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text())
    summary = json.loads((out_dir / "population.json").read_text())
    sql = (out_dir / "fixture.sql").read_text()
    expected = generate_population(make_spec(seed=7))
    assert manifest == expected.manifest
    assert sql == expected.fixture_sql
    assert summary == expected.summary()
    assert "schedules" in summary
    assert set(summary["schedules"]) == {p.persona_id for p in expected.personas}
    assert capsys.readouterr().out  # reports what it wrote


def test_cli_rejects_bad_arguments() -> None:
    with pytest.raises(SystemExit):
        main(["--friend-groups", "2", "--friends-min", "0", "--seed", "1"])


# ------------------------------------------------------------ overlap helpers


def test_overlap_fraction_handles_wrap_and_disjoint_windows() -> None:
    # Tuesday 22:00 -> 02:00 wraps into Wednesday.
    late_night = ((1, 22.0, 2.0),)
    evening = ((1, 19.0, 23.0),)
    morning = ((1, 6.0, 9.0),)
    assert overlap_fraction(late_night, evening) > 0.0
    assert overlap_fraction(late_night, morning) == 0.0
    assert overlap_fraction(evening, evening) == 1.0
    assert overlap_fraction((), evening) == 0.0
    assert schedule_to_slots(late_night) == schedule_to_slots(((1, 22.0, 24.0), (2, 0.0, 2.0)))
