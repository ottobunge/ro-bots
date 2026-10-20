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
from robots.domain.actions import Attack, MoveTo, Rest
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


def _roam_moves(outcome) -> list:
    return [a for a in outcome.actions if isinstance(a, MoveTo)]


def test_widen_constant_is_bounded_and_documented() -> None:
    assert type(TARGET_WIDEN_STEPS) is int
    assert 0 < TARGET_WIDEN_STEPS <= 100


def test_strict_target_still_holds_fire_below_streak() -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS - 1):
        outcome = script.step(_state([_lunatic()]))
        assert _roam_moves(outcome)  # the roam leg: the empty view patrols
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
        assert _roam_moves(script.step(_state([])))  # the roam during the starved streak
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
        assert _roam_moves(
            script.step(_state([_lunatic()]))
        )  # the out-of-plan species: hold fire, roam
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
    assert _roam_moves(outcome)  # the roam leg: the empty view patrols
    assert outcome.status.name == "ACTIVE"


@pytest.mark.parametrize("species", ["Lunatic", "Fabre", "Willow"])
def test_widening_is_not_species_hardcoded(species: str) -> None:
    script, _ = _script()
    for _ in range(TARGET_WIDEN_STEPS):
        script.step(_state([_lunatic()]))
    other = LocatedMonster(11, species, "monster", 0.0, x=100, y=101)
    assert script.step(_state([other])).actions == (Attack(target_id=11),)


def test_farm_script_roams_when_no_mobs_in_view() -> None:
    """w59/w60 roam leg: an empty view must not stand still. The script
    emits a bounded patrol MoveTo near the current cell so the agent walks
    to find its plan's species (real players roam; the w59 receipt proved
    the stand-and-wait deadlock: plans authored, zero walks)."""
    script, _plan = _script()
    state = _state(nearby=[])
    outcome = script.step(state)
    moves = [a for a in outcome.actions if isinstance(a, MoveTo)]
    assert moves, "no-mob step must emit a roam MoveTo"
    x, y = moves[0].x, moves[0].y
    assert abs(x - state.x) <= 12
    assert abs(y - state.y) <= 12
    assert (x, y) != (state.x, state.y)


def test_farm_script_roam_is_deterministic_per_plan() -> None:
    """Same plan + same empty state -> the same roam cell (testable, no
    nondeterminism in the script layer)."""
    s1, _plan = _script()
    s2, _ = _script()
    a1 = [a for a in s1.step(_state(nearby=[])).actions if isinstance(a, MoveTo)]
    a2 = [a for a in s2.step(_state(nearby=[])).actions if isinstance(a, MoveTo)]
    assert a1
    assert a2
    assert (a1[0].x, a1[0].y) == (a2[0].x, a2[0].y)


def test_farm_script_prefers_targets_over_roam() -> None:
    """A visible plan target still yields an Attack, never a roam."""
    script, _ = _script()
    outcome = script.step(
        _state(
            nearby=[LocatedMonster(id=7, name="Poring", kind="monster", distance=0.0, x=100, y=100)]
        )
    )
    assert any(isinstance(a, Attack) for a in outcome.actions)
