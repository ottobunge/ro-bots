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
    price_tier: int  # 0-3, market value band
    digest_text: str  # pre-rendered one-liner, e.g. "+4 STR, lvl req 45, sells ~2k"

    def __post_init__(self) -> None:
        if not 0 <= self.price_tier <= 3:
            msg = f"price_tier must be 0-3, got {self.price_tier}"
            raise ValueError(msg)


@final
@dataclass(frozen=True, slots=True)
class SkillDigest:
    """Normalized, pre-calculated view of one skill (ADR-009)."""

    skill_id: str
    name: str
    required_level: int
    digest_text: str

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

    def progress_for(self, build: Build) -> BuildProgress:
        """Compare this sheet against ``build`` (pure; no model calls)."""
        equip_met = tuple(
            s for s, item in build.equip_goals.items() if self.equipped.get(s) == item
        )
        equip_missed = tuple(s for s in build.equip_goals if s not in equip_met)
        skills = sum(1 for s in build.skill_goals if s in self.learned_skills)
        reached = sum(1 for m in build.milestone_levels if self.level >= m)
        return BuildProgress(
            build=build,
            equip_met=equip_met,
            equip_missed=equip_missed,
            skills_learned=skills,
            milestone_index=max(0, reached - 1),
        )
