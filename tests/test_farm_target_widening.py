"""Species-adaptive target widening: the window-14 starvation fix (RED first).

Window 14 (run/reviews/playing-grind-operator-live-window14-analysis.json,
fixture_0): 1780 script steps saw ONLY Lunatics while the authored plan
targeted a species not in sight -> zero attacks for the whole window. The
plan is NOT rewritten; the script's own target filter widens after a bounded
consecutive-evaluation starvation streak (TARGET_WIDEN_STEPS), preferring the
plan species again the moment it is present.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

import pytest

from robots.app.scripts import TARGET_WIDEN_STEPS, FarmScript
from robots.domain.actions import Attack, Rest
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, BotState, Goal


@dataclass(frozen=True)
class LocatedMonster(ActorRef):
    """ActorRef plus the tracker cell the projected state may carry."""

    x: int = 0
    y: int = 0


def _state(nearby: Sequence[ActorRef]) -> BotState:
    return BotState(
        name="bot",
        job="Swordsman",
        base_level=1,
        hp=100,
        max_hp=100,
        sp=10,
        max_sp=10,
        map_name="prt_fild08",
        x=100,
        y=100,
        goal=Goal.FARM_ITEM,
        in_party=False,
        nearby=tuple(nearby),
        inventory={},
        pending_invites=(),
        recent_chat=(),
    )


def _script() -> tuple[FarmScript, FarmPlan]:
    plan = FarmPlan(
        plan_id=1,
        map_name="prt_fild08",
        target_mobs=("Poring",),
        duration_s=300.0,
        interrupt_level_above=0,
    )
    return FarmScript(plan), plan


def _lunatic(mob_id: int = 7) -> LocatedMonster:
    return LocatedMonster(mob_id, "Lunatic", "monster", 0.0, x=100, y=101)


def test_widen_constant_is_bounded_and_documented() -> None:
    assert type(TARGET_WIDEN_STEPS) is int
    assert 0 < TARGET_WIDEN_STEPS <= 100


def test_strict_target_still_holds_fire_below_streak() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS - 1):
        outcome = script.step(_state([_lunatic()]))
        assert outcome.actions == ()
        assert outcome.status.name == "ACTIVE"  # keep farming, no target yet


def test_widens_after_streak_and_attacks_observed_species() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS - 1):
        script.step(_state([_lunatic()]))
    outcome = script.step(_state([_lunatic()]))
    assert outcome.actions == (Attack(target_id=7),)
    # widening persists while the plan species stays absent
    assert script.step(_state([_lunatic(8)])).actions == (Attack(target_id=8),)


def test_widening_counts_plan_absent_evaluations_including_empty_field() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS - 1):
        assert script.step(_state([])).actions == ()
    outcome = script.step(_state([_lunatic()]))
    assert outcome.actions == (Attack(target_id=7),)


def test_plan_species_is_preferred_again_and_resets_the_streak() -> None:
    script, plan = _script()
    for _ in range(TARGET_WIDEN_STEPS):
        script.step(_state([_lunatic()]))
    poring = LocatedMonster(42, "Poring", "monster", 0.0, x=100, y=99)
    assert script.step(_state([_lunatic(), poring])).actions == (Attack(target_id=42),)
    # the streak restarted: a foreign species alone holds fire again
    for _ in range(TARGET_WIDEN_STEPS - 1):
        assert script.step(_state([_lunatic()])).actions == ()
    assert script.step(_state([_lunatic(9)])).actions == (Attack(target_id=9),)
    # honesty: the plan was never rewritten
    assert plan.target_mobs == ("Poring",)


def test_low_hp_rest_still_outranks_widened_targets() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS):
        script.step(_state([_lunatic()]))
    state = replace(_state([_lunatic()]), hp=10)
    outcome = script.step(state)
    assert isinstance(outcome.actions[0], Rest)


def test_no_attackable_no_widened_action() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS):
        script.step(_state([]))
    outcome = script.step(_state([]))
    assert outcome.actions == ()
    assert outcome.status.name == "ACTIVE"


@pytest.mark.parametrize("species", ["Lunatic", "Fabre", "Willow"])
def test_widening_is_not_species_hardcoded(species: str) -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS):
        script.step(_state([_lunatic()]))
    other = LocatedMonster(11, species, "monster", 0.0, x=100, y=101)
    assert script.step(_state([other])).actions == (Attack(target_id=11),)
