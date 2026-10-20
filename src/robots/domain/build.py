"""Character builds and item cognition (ADR-009).

Mechanics are pre-calculated, never modeled: an adapter over the rAthena
item/skill DB turns raw rows into typed :class:`ItemDigest` /
:class:`SkillDigest` values. Agents see the normalized digest text —
never raw numbers, never any math of their own. A :class:`Build` is the
plan of what a character will become, authored by the agent (Clef) at
character creation; :class:`BuildProgress` is how far along it is.
"""

from dataclasses import dataclass, field
from typing import final


@final
@dataclass(frozen=True, slots=True)
class ItemDigest:
    """Normalized, pre-calculated view of one item (ADR-009)."""

    item_id: int
    name: str
    slot: str
    stat_effects: tuple[tuple[str, int], ...]
    required_level: int
    price_tier: int | None  # 0-3 market band; None means market value is unknown
    digest_text: str  # pre-rendered metadata, not a character damage calculation
    aegis_name: str | None = None
    ruleset: str | None = None
    locations: tuple[str, ...] = ()  # exact rAthena location flags, including Both_Hand
    jobs: tuple[tuple[str, bool], ...] = ()  # raw permission masks, not expanded job families
    classes: tuple[tuple[str, bool], ...] = ()
    gender: str | None = None
    maximum_level: int | None = None
    card_slots: int | None = None
    unknown_effects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.price_tier is not None and not 0 <= self.price_tier <= 3:
            msg = f"price_tier must be 0-3, got {self.price_tier}"
            raise ValueError(msg)


@final
@dataclass(frozen=True, slots=True)
class SkillDigest:
    """Normalized, pre-calculated view of one skill (ADR-009)."""

    skill_id: str
    name: str
    required_level: int  # legacy; YAML adapter mirrors declared BaseLevel, not learn order
    digest_text: str
    max_level: int | None = None  # selected class tree capped against skill DB
    database_max_level: int | None = None
    required_base_level: int | None = None
    required_job_level: int | None = None
    prerequisites: tuple[tuple[str, int], ...] = ()
    class_name: str | None = None
    ruleset: str | None = None
    unknown_effects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.skill_id or not self.name:
            msg = "skill_id and name must be non-empty"
            raise ValueError(msg)


@final
@dataclass(frozen=True, slots=True)
class Build:
    """The plan of what one character will become (authored by the agent)."""

    build_id: str
    persona_id: str
    char_name: str
    class_path: tuple[str, ...]  # e.g. ("Novice", "Swordsman", "Knight")
    stat_plan: dict[str, int]
    skill_goals: tuple[str, ...]
    equip_goals: dict[str, str]  # slot -> target item name
    milestone_levels: tuple[int, ...]
    skill_levels: dict[str, int] = field(default_factory=dict)
    ruleset: str = "unvalidated"
    validation_issues: tuple[str, ...] = ("Executable build validity has not been established.",)

    def goal_for_slot(self, slot: str) -> str | None:
        """Target item name for ``slot``, or None if the build doesn't care."""
        return self.equip_goals.get(slot)


@final
@dataclass(frozen=True, slots=True)
class BuildProgress:
    """Snapshot of how far a character has come along its build."""

    build: Build
    equip_met: tuple[str, ...]  # slots whose goal item is equipped
    equip_missed: tuple[str, ...]  # slots whose goal item is not (yet) equipped
    skills_learned: int  # count of build skill goals already learned
    milestone_index: int  # highest milestone level reached (index into milestone_levels)

    def summary(self) -> str:
        """One line: 'build <id>: 2/3 equip goals, 1/4 skills, milestone 1/2'."""
        return (
            f"build {self.build.build_id}: "
            f"equip {len(self.equip_met)}/{len(self.equip_met) + len(self.equip_missed)}, "
            f"skills {self.skills_learned}/{len(self.build.skill_goals)}, "
            f"milestone {self.milestone_index}/{len(self.build.milestone_levels)}"
        )


@final
@dataclass(frozen=True, slots=True)
class CharacterSheet:
    """What a character currently is: level, learned skills, equipped items."""

    level: int
    learned_skills: frozenset[str] = field(default=frozenset())
    equipped: dict[str, str] = field(default_factory=dict)  # slot -> item name
    skill_levels: dict[str, int] = field(default_factory=dict)

    def progress_for(self, build: Build) -> BuildProgress:
        """Compare this sheet against ``build`` (pure; no model calls)."""
        equip_met = tuple(
            s for s, item in build.equip_goals.items() if self.equipped.get(s) == item
        )
        equip_missed = tuple(s for s in build.equip_goals if s not in equip_met)
        skills = sum(_skill_goal_met(s, self, build) for s in build.skill_goals)
        reached = sum(1 for m in build.milestone_levels if self.level >= m)
        return BuildProgress(
            build=build,
            equip_met=equip_met,
            equip_missed=equip_missed,
            skills_learned=skills,
            milestone_index=max(0, reached - 1),
        )


def _skill_goal_met(name: str, sheet: CharacterSheet, build: Build) -> bool:
    if name in build.skill_levels:
        return sheet.skill_levels.get(name, 0) >= build.skill_levels[name]
    return name in sheet.learned_skills
