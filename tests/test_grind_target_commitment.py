"""Target commitment until death: keep hitting one mob until it dies (RED first).

Window 22 (run/reviews/playing-grind-operator-live-window22-analysis.json)
proved the attributed kill chain live but closed with no actual kill: both
Novices attack for ~1 damage per hit (fixture_0: 19 attacks -> 18 bot-dealt
damage) while the goal scripts re-pick the CLOSEST monster on every
evaluation, spreading single hits across the roaming cluster — no mob ever
accumulates the pinned server's Poring pool (rathena db/pre-re/mob_db.yml:134
`Id: 1002 ... Hp: 50`; the brief's 60 came from the official-iRO DB, not this
pin). The fix: when a grasp goal script has attacked a target id within the
bounded KILL_COMMIT_WINDOW (script evaluations), it keeps attacking THAT id
while it stays visible — across script re-creation (the brain re-installs
GrindScript/FarmScript on every heartbeat review, brain.py:305/460, so the
commitment is keyed per bot name, not per script instance). The commitment
releases when the id leaves the received state (death/vanish), on rest, on
loot, and after the window of evaluations without a landed attack; FarmScript
only ever holds an id that passes its current plan filter (strict targeting
and the bounded widening are unchanged), and rest keeps precedence.
"""

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace

import pytest

from robots.app import scripts
from robots.app.scripts import FarmScript, GrindScript
from robots.domain.actions import Attack, Loot, MoveTo, Rest
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, BotState, Goal

# RED-compatibility import: the commitment contract does not exist on the
# unchanged window-22 source yet; the behavioral assertions below name the gap.
KILL_COMMIT_WINDOW: int = getattr(scripts, "KILL_COMMIT_WINDOW", 0)

BOT_A = "killcommit-a"
BOT_B = "killcommit-b"


@dataclass(frozen=True)
class LocatedMonster(ActorRef):
    """ActorRef plus the tracker cell the projected state may carry."""

    x: int = 0
    y: int = 0


def _committed_id(bot: str) -> int | None:
    commitment = scripts._kill_commitment(bot, KILL_COMMIT_WINDOW)
    return commitment._target_id


@pytest.fixture(autouse=True)
def _clean_commitments() -> Iterator[None]:
    commitments: dict[str, object] | None = getattr(scripts, "_KILL_COMMITMENTS", None)
    if commitments is not None:
        commitments.clear()
    yield
    if commitments is not None:
        commitments.clear()


def _state(
    nearby: Sequence[ActorRef],
    *,
    name: str = BOT_A,
    hp: int = 100,
    max_hp: int = 100,
    x: int = 100,
    y: int = 100,
    inventory: dict[str, int] | None = None,
    goal: Goal = Goal.GRIND,
) -> BotState:
    return BotState(
        name=name,
        job="Novice",
        base_level=1,
        hp=hp,
        max_hp=max_hp,
        sp=10,
        max_sp=10,
        map_name="prt_fild08",
        x=x,
        y=y,
        goal=goal,
        in_party=False,
        nearby=tuple(nearby),
        inventory=inventory if inventory is not None else {},
        pending_invites=(),
        recent_chat=(),
    )


def _plan(targets: tuple[str, ...] = ("Poring",)) -> FarmPlan:
    return FarmPlan(
        plan_id=1,
        map_name="prt_fild08",
        target_mobs=targets,
        duration_s=300.0,
        interrupt_level_above=0,
    )


def _mob(species: str, mob_id: int, *, x: int, y: int) -> LocatedMonster:
    distance = math.hypot(x - 100, y - 100)  # the bot stands at (100, 100)
    return LocatedMonster(mob_id, species, "monster", distance, x=x, y=y)


def _poring(mob_id: int, *, x: int = 101, y: int = 100) -> LocatedMonster:
    return _mob("Poring", mob_id, x=x, y=y)


def _lunatic(mob_id: int, *, x: int = 101, y: int = 100) -> LocatedMonster:
    return _mob("Lunatic", mob_id, x=x, y=y)


def test_commit_window_is_bounded_and_documented() -> None:
    assert type(KILL_COMMIT_WINDOW) is int
    assert 0 < KILL_COMMIT_WINDOW <= 100


def test_committed_target_is_kept_when_another_becomes_closer() -> None:
    script = GrindScript()
    first = script.step(_state([_poring(42)]))
    assert first.actions == (Attack(target_id=42),)
    # The Poring stepped diagonally (still melee) while a fresh Lunatic
    # spawned straight-adjacent (strictly closer): the committed id keeps the
    # hits so its damage accumulates.
    follow = script.step(_state([_poring(42, x=101, y=101), _lunatic(7)]))
    assert follow.actions == (Attack(target_id=42),)


def test_commitment_survives_goal_script_recreation() -> None:
    # The brain re-installs the script on every heartbeat review; the live
    # window only closes a kill if the commitment outlives that re-creation.
    GrindScript().step(_state([_poring(42)]))
    recreated = GrindScript()
    outcome = recreated.step(_state([_poring(42, x=101, y=101), _lunatic(7)]))
    assert outcome.actions == (Attack(target_id=42),)


def test_two_bots_do_not_share_a_commitment() -> None:
    GrindScript().step(_state([_lunatic(42)], name=BOT_A))
    other = GrindScript().step(_state([_lunatic(42, x=101, y=101), _poring(7)], name=BOT_B))
    assert other.actions == (Attack(target_id=7),)


def test_commitment_releases_when_the_target_leaves_the_state() -> None:
    script = GrindScript()
    script.step(_state([_poring(42)]))
    assert script.step(_state([_lunatic(7)])).actions == (Attack(target_id=7),)
    # Death released the first commitment: with both visible again the
    # committed Lunatic is kept, the dead Poring id is not resumed.
    both = script.step(_state([_poring(42, x=105, y=100), _lunatic(7)]))
    assert both.actions == (Attack(target_id=7),)


def test_commitment_expires_after_the_bounded_window_without_a_landed_attack() -> None:
    script = GrindScript()
    script.step(_state([_lunatic(42)]))
    far = _state([_lunatic(42, x=105, y=100), _poring(7)])
    for _ in range(KILL_COMMIT_WINDOW):
        assert script.step(far).actions == (MoveTo(x=105, y=100),)
    # The window of approach-only evaluations is exhausted: closest-picking
    # resumes instead of chasing an unreachable id forever.
    assert script.step(far).actions == (Attack(target_id=7),)


def test_landed_attacks_rearm_the_window_mid_fight() -> None:
    # A pinned-server Poring dies at 50 HP; a Novice lands ~1 damage per
    # attack, so a kill needs more consecutive attack evaluations than the
    # commit window — every landed attack must rearm the commitment.
    script = GrindScript()
    script.step(_state([_poring(42, x=101, y=101)]))  # establish the commitment
    barrage = _state([_poring(42, x=101, y=101), _lunatic(7)])
    for _ in range(KILL_COMMIT_WINDOW * 2 + 5):
        outcome = script.step(barrage)
        assert outcome.actions == (Attack(target_id=42),)


def test_rest_releases_the_commitment() -> None:
    script = GrindScript()
    script.step(_state([_lunatic(42)]))
    hurt = _state([_lunatic(42), _poring(7)], hp=10)
    assert script.step(hurt).actions == (Rest(),)
    healed = _state([_lunatic(42, x=101, y=101), _poring(7)])
    assert script.step(healed).actions == (Attack(target_id=7),)


def test_loot_releases_the_commitment() -> None:
    script = GrindScript()
    script.step(_state([_lunatic(42)]))
    loot = _state([], inventory={"Jellopy": 3})
    assert script.step(loot).actions == (Loot(),)
    back = _state([_lunatic(42, x=101, y=101), _poring(7)])
    assert script.step(back).actions == (Attack(target_id=7),)


def test_positionless_committed_target_keeps_the_honest_attack() -> None:
    script = GrindScript()
    script.step(_state([ActorRef(42, "Poring", "monster", 3.0)]))
    outcome = script.step(_state([ActorRef(42, "Poring", "monster", 1.5), _lunatic(7)]))
    assert outcome.actions == (Attack(target_id=42),)


def test_farm_commitment_stays_inside_the_plan_filter() -> None:
    script = FarmScript(_plan(("Poring",)))
    first = script.step(_state([_poring(42, x=101, y=101), _lunatic(7)], goal=Goal.FARM_ITEM))
    assert first.actions == (Attack(target_id=42),)
    # The strictly closer Lunatic never steals the hits; the plan species is
    # kept while it stays in melee range.
    follow = script.step(_state([_poring(42, x=101, y=101), _lunatic(7)], goal=Goal.FARM_ITEM))
    assert follow.actions == (Attack(target_id=42),)
    # When the committed plan target dies the strict filter holds fire again
    # — the out-of-filter id is never adopted as a commitment.
    empty = script.step(_state([_lunatic(7)], goal=Goal.FARM_ITEM))
    # the w60 roam leg: an empty view patrols (MoveTo) instead of standing
    assert all(isinstance(a, MoveTo) for a in empty.actions)
    assert empty.actions
    assert _committed_id(BOT_A) is None


def test_farm_commitment_released_on_rest_and_loot() -> None:
    script = FarmScript(_plan(("Poring",)))
    field = _state([_poring(42), _lunatic(7)], goal=Goal.FARM_ITEM)
    script.step(field)
    hurt = replace(field, hp=10)
    assert script.step(hurt).actions == (Rest(),)
    assert _committed_id(BOT_A) is None
    script.step(_state([_poring(42)], goal=Goal.FARM_ITEM))
    looted = _state([], inventory={"Jellopy": 3}, goal=Goal.FARM_ITEM)
    assert script.step(looted).actions == (Loot(),)
    assert _committed_id(BOT_A) is None


def test_farm_widening_persists_while_the_plan_species_stays_absent() -> None:
    script = FarmScript(_plan(("Poring",)))
    for _ in range(19):
        # the out-of-plan species holds fire but still roams (w60)
        assert all(
            isinstance(a, MoveTo)
            for a in script.step(_state([_lunatic(7)], goal=Goal.FARM_ITEM)).actions
        )
    widened = script.step(_state([_lunatic(7)], goal=Goal.FARM_ITEM))
    assert widened.actions == (Attack(target_id=7),)
    assert script.step(_state([_lunatic(7)], goal=Goal.FARM_ITEM)).actions == (Attack(target_id=7),)


def test_unheld_pick_prefers_the_lowest_pinned_hp_species() -> None:
    """Window-23 finding: 139 damage landed on one id without a kill - the
    closest-pick held a Pupa (pinned HP 427) while Porings (HP 50) stood in
    reach. A Novice (~1 dmg/hit) can only close a kill on the lowest-HP
    species, so the unheld pick prefers the pinned-HP order before
    distance (pinned mob_db.yml e985006171d2: Poring 1002 Hp 50, Lunatic
    1063 Hp 60, Drops 1013 Hp 60, Pupa 1008 Hp 427)."""
    script = GrindScript()
    pupa_closer = _mob("Pupa", 7, x=101, y=100)  # distance 1
    poring_farther = _mob("Poring", 42, x=103, y=100)  # distance 3
    outcome = script.step(_state([pupa_closer, poring_farther]))
    assert outcome.actions == (MoveTo(x=103, y=100),)  # approach the Poring
    arrived = _state([_mob("Pupa", 7, x=102, y=100), _poring(42, x=101, y=100)])
    assert script.step(arrived).actions == (Attack(target_id=42),)  # melee now


def test_unknown_species_falls_back_to_closest_pick() -> None:
    """Unknown species sort after every pinned-HP species; among unknowns the
    closest wins (the legacy tie-break)."""
    script = GrindScript()
    deviling_closer = _mob("Deviling", 9, x=101, y=100)
    golem_farther = _mob("Golem", 11, x=104, y=100)
    outcome = script.step(_state([deviling_closer, golem_farther]))
    assert outcome.actions == (Attack(target_id=9),)
