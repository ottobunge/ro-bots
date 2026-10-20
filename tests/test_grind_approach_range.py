"""Range-aware melee approach: walk into range, then attack (window-14 frontier).

Window 13 (run/reviews/playing-grind-operator-live-window13-analysis.json):
1854 attacks authored and dispatched, attack 0x437 on the wire 1853 times, and
the server rejected every one with ZC_ATTACK_FAILURE_FOR_DISTANCE (0x0139,
x62603) — the clientless bot attacked from 14+ tiles while the real client
auto-approaches and rAthena pre-re does not server-side chase.

Melee range verified at the pinned checkout (flake.nix:10-16, rev
e985006171d2eb320ee512a653f4c83aea3d81b6, MAIN/pre-re 20180704):

- src/map/battle.cpp:8215-8230 ``battle_check_range``: BL_PC attackers use the
  circular client metric ``check_distance_client_bl`` (path.hpp:48), and any
  distance < 2 is accepted without a path check (battle.cpp:8226-8228).
- src/map/status.cpp:4216 ``if(base_status->rhw.range < 1) ... = 1`` — the
  unarmed range floor is 1 at this pin.
- There is NO ``attack_range`` battle config at this pin (grep over
  conf/battle/ and the battle.cpp registration table returns nothing; that
  setting postdates 2018-07-04).

So an unarmed attack is server-accepted at Chebyshev distance <= 1
(diagonal-adjacent included) and doomed with 0x0139 beyond it. The scripts'
MELEE_RANGE constant is 1 — not 2 — because a 2-tile straight attack still
receives 0x0139 (Chebyshev 2 > 1) and window 14 acceptance requires accepted
attacks. The scripts compare positions with the server's own Chebyshev metric.

The target cell is read from the state the script is handed each evaluation,
so an approach MoveTo re-evaluates every tick and never commits to a stale
cell. A state monster that carries no position keeps today's honest behavior:
attack anyway and let the server's range check fail (fail-closed honest).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from robots.app.scripts import (
    MELEE_RANGE,
    FarmScript,
    GrindScript,
    IdleTownScript,
    NpcGuidanceScript,
    ScriptOutcome,
    TravelScript,
    script_for,
)
from robots.domain.actions import Attack, Loot, MoveTo, Rest, TalkToNpc
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, BotState, Goal


@dataclass(frozen=True)
class LocatedMonster(ActorRef):
    """ActorRef plus the tracker cell the projected state may carry."""

    x: int = 0
    y: int = 0


def _state(
    *,
    nearby: Sequence[ActorRef] = (),
    x: int = 100,
    y: int = 100,
    hp: int = 100,
    max_hp: int = 100,
    inventory: dict[str, int] | None = None,
) -> BotState:
    return BotState(
        name="bot",
        job="Swordsman",
        base_level=1,
        hp=hp,
        max_hp=max_hp,
        sp=10,
        max_sp=10,
        map_name="prt_fild08",
        x=x,
        y=y,
        goal=Goal.GRIND,
        in_party=False,
        nearby=tuple(nearby),
        inventory=inventory if inventory is not None else {},
        pending_invites=(),
        recent_chat=(),
    )


def _grind(state: BotState) -> ScriptOutcome:
    return GrindScript().step(state)


def _farm(state: BotState, targets: tuple[str, ...] = ("Poring",)) -> ScriptOutcome:
    plan = FarmPlan(
        plan_id=1,
        map_name="prt_fild08",
        target_mobs=tuple(targets),
        duration_s=300.0,
        interrupt_level_above=0,
    )
    return FarmScript(plan).step(state)


def test_melee_range_is_the_verified_pinned_value():
    assert MELEE_RANGE == 1


def test_grind_approaches_out_of_range_target():
    state = _state(nearby=[LocatedMonster(42, "Poring", "monster", 14.0, x=114, y=100)])
    outcome = _grind(state)
    assert outcome.actions == (MoveTo(x=114, y=100),)
    assert outcome.status.name == "ACTIVE"


def test_farm_approaches_out_of_range_plan_target():
    targets = [
        LocatedMonster(42, "Poring", "monster", 14.0, x=114, y=100),
        LocatedMonster(7, "Drops", "monster", 1.0, x=101, y=100),
    ]
    outcome = _farm(_state(nearby=targets))
    # The plan target is approached; the adjacent non-target is still ignored.
    assert outcome.actions == (MoveTo(x=114, y=100),)


def test_in_range_target_attacks_immediately():
    # Diagonal-adjacent: server client-metric distance 1, accepted.
    diagonal = [LocatedMonster(42, "Poring", "monster", 1.4142135, x=101, y=101)]
    assert _grind(_state(nearby=diagonal)).actions == (Attack(target_id=42),)
    assert _farm(_state(nearby=diagonal)).actions == (Attack(target_id=42),)


def test_boundary_two_tiles_straight_approaches_instead_of_doomed_attack():
    # Chebyshev 2 > pinned unarmed range 1: attacking here is exactly the
    # window-13 0x0139 failure, so the script must keep approaching.
    two_straight = [LocatedMonster(42, "Poring", "monster", 2.0, x=102, y=100)]
    assert _grind(_state(nearby=two_straight)).actions == (MoveTo(x=102, y=100),)
    assert _farm(_state(nearby=two_straight)).actions == (MoveTo(x=102, y=100),)


def test_positionless_target_keeps_honest_attack():
    # Production ActorRef carries no cell today: attack anyway and let the
    # server's range check fail — the fail-closed honest fallback.
    state = _state(nearby=[ActorRef(42, "Poring", "monster", 14.0)])
    assert _grind(state).actions == (Attack(target_id=42),)
    assert _farm(_state(nearby=[ActorRef(42, "Poring", "monster", 14.0)])).actions == (
        Attack(target_id=42),
    )


def test_approach_refollows_moved_target_each_step():
    script = GrindScript()
    first = script.step(
        _state(nearby=[LocatedMonster(42, "Poring", "monster", 14.0, x=114, y=100)])
    )
    assert first.actions == (MoveTo(x=114, y=100),)
    # The Poring moved before the next evaluation: the next MoveTo must use
    # the fresh cell, never the stale one.
    moved = script.step(
        _state(nearby=[LocatedMonster(42, "Poring", "monster", 9.8488578, x=107, y=97)])
    )
    assert moved.actions == (MoveTo(x=107, y=97),)


def test_farm_non_target_mob_in_range_does_not_change_approach():
    targets = [
        LocatedMonster(42, "Poring", "monster", 14.0, x=114, y=100),
        LocatedMonster(7, "Drops", "monster", 1.0, x=101, y=100),
    ]
    outcome = _farm(_state(nearby=targets))
    assert Attack(target_id=7) not in outcome.actions


def test_hp_rest_still_precedes_approach():
    state = _state(
        nearby=[LocatedMonster(42, "Poring", "monster", 14.0, x=114, y=100)], hp=10, max_hp=100
    )
    assert _grind(state).actions == (Rest(),)
    assert _farm(state).actions == (Rest(),)


def test_no_monsters_tail_unchanged():
    assert _grind(_state(inventory={"Jellopy": 3})).actions == (Loot(),)
    # w65-69: the empty view roams (ACTIVE) instead of completing DONE
    assert _grind(_state()).status.name == "ACTIVE"
    outcome = _farm(_state(inventory={"Jellopy": 3}))
    assert outcome.actions == (Loot(),)  # loot still precedes keep-farming idle
    assert _farm(_state()).status.name == "ACTIVE"


def test_non_grasp_goal_scripts_unchanged():
    idle = script_for(Goal.IDLE_TOWN, _state())
    assert isinstance(idle, IdleTownScript)
    assert idle.step(_state()).actions == (MoveTo(x=100, y=101),)
    quest = script_for(Goal.QUEST, _state(nearby=[ActorRef(9, "Guide", "npc", 1.0)]))
    assert isinstance(quest, NpcGuidanceScript)
    assert quest.step(_state(nearby=[ActorRef(9, "Guide", "npc", 1.0)])).actions == (
        TalkToNpc(npc_id=9),
    )
    assert isinstance(script_for(Goal.GRIND, _state()), GrindScript)
    # Goal-level FARM_ITEM maps to GrindScript (scripts.py factory); the
    # plan-driven FarmScript is installed by the brain when a plan was
    # authored, and its behavior is exercised directly by the tests above.
    assert isinstance(script_for(Goal.FARM_ITEM, _state()), GrindScript)


def test_travel_script_unchanged():
    assert TravelScript(105, 102).step(_state()).actions == (MoveTo(x=101, y=101),)
