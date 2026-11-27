"""Persistent patrol waypoint for the empty-view roam legs (leg-135 census).

The leg-135 movement census (run/reviews/leg135-movement-census.md) proved the
dominant MoveTo class is the empty-view roam patrol: the FarmScript/GrindScript
roam legs drew a fresh +/-8-cell patrol target every ~2 s brain tick, so every
authored walk was replaced by the next tick's fresh draw before arrival
(32,677/40,159 MoveTos, 99.09% abandoned-before-next, agents jitter-walking a
static prt_fild08 pocket). The fix: the roam legs HOLD the currently-aimed
absolute cell in the script instance and re-author THE SAME target each
empty-view tick until (a) the tracked position stands on it (arrival - then
the next offset is drawn), or (b) the aim is invalidated (the map changed, a
higher-priority action replaced the walk - the script did not author on the
previous evaluation - or the bounded re-aim horizon expired, which covers the
runtime's unwalkable-reroll / stuck-cell classes the script layer cannot see:
scripts read no grid).
"""

import json
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from robots.app import scripts as scripts_module
from robots.app.movement_census import ROAM_OFFSETS, summarize_movement_traces
from robots.app.scripts import FarmScript, GrindScript
from robots.domain.actions import MoveTo
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, BotState, Goal

# RED-compatibility imports: the waypoint contract does not exist on the
# unchanged leg-135 source yet; the behavioral assertions below name the gap.
ROAM_PATROL_OFFSETS: tuple[tuple[int, int], ...] = getattr(
    scripts_module, "ROAM_PATROL_OFFSETS", ()
)
ROAM_REAIM_HORIZON: int = getattr(scripts_module, "ROAM_REAIM_HORIZON", 0)

# The patrol draw set in the scripts' own order - the seeded mirrors below must
# draw the exact same sequence the script's rng does.
_PATROL_DRAWS: tuple[tuple[int, int], ...] = (
    (8, 0),
    (-8, 0),
    (0, 8),
    (0, -8),
    (5, 5),
    (-5, -5),
)

T0 = datetime(2026, 11, 27, 8, 0, tzinfo=UTC)
TICK_S = 2.0  # the ~2 s brain tick the census measured
WALK_LAG_S = 3.0  # a patrol walk outlasts one tick: the next authoring is held


def _state(
    x: int = 100,
    y: int = 100,
    *,
    map_name: str = "prt_fild08",
    goal: Goal = Goal.FARM_ITEM,
    nearby: Sequence[ActorRef] = (),
) -> BotState:
    return BotState(
        name="bot",
        job="Swordsman",
        base_level=1,
        hp=100,
        max_hp=100,
        sp=10,
        max_sp=10,
        map_name=map_name,
        x=x,
        y=y,
        goal=goal,
        in_party=False,
        nearby=tuple(nearby),
        inventory={},
        pending_invites=(),
        recent_chat=(),
    )


def _plan() -> FarmPlan:
    return FarmPlan(
        plan_id=1,
        map_name="prt_fild08",
        target_mobs=("Poring",),
        duration_s=300.0,
        interrupt_level_above=0,
    )


def _farm() -> FarmScript:
    return FarmScript(_plan())


@pytest.fixture
def grind_rng(monkeypatch: pytest.MonkeyPatch) -> random.Random:
    """Deterministic draws for the GrindScript roam leg (module random)."""
    rng = random.Random(7)
    # scripts.py does `import random`, so this is the very object its roam leg
    # calls random.choice on
    monkeypatch.setattr(random, "choice", rng.choice)
    return rng


def _farm_draws(count: int) -> list[tuple[int, int]]:
    """The seeded farm roam rng's draw sequence (mirrors the script's rng)."""
    mirror = random.Random("roam-1-prt_fild08")
    return [mirror.choice(_PATROL_DRAWS) for _ in range(count)]


def _moves(outcome: Any) -> list[MoveTo]:
    return [a for a in outcome.actions if isinstance(a, MoveTo)]


def _cell(move: MoveTo) -> tuple[int, int]:
    return (move.x, move.y)


def _mob(species: str, mob_id: int, *, x: int, y: int) -> ActorRef:
    return ActorRef(mob_id, species, "monster", float(abs(x - 100) + abs(y - 100)), x, y)


def test_roam_reaim_horizon_is_bounded_and_documented() -> None:
    assert type(ROAM_REAIM_HORIZON) is int
    assert 1 <= ROAM_REAIM_HORIZON <= 60
    assert len(ROAM_PATROL_OFFSETS) == 6


def test_farm_roam_holds_one_target_across_consecutive_empty_ticks() -> None:
    """Consecutive empty-view ticks re-author the SAME aim (the leg-135 fix):
    the walk gets its full flight instead of being replaced by a fresh draw
    after ~1 cell."""
    script = _farm()
    targets = []
    for _ in range(4):
        outcome = script.step(_state())
        moves = _moves(outcome)
        assert len(moves) == 1
        targets.append(_cell(moves[0]))
    assert targets[0] != (100, 100)
    assert targets == [targets[0]] * 4


def test_farm_roam_keeps_the_anchored_cell_when_the_walk_falls_short() -> None:
    """The aim is the absolute cell it was drawn for (the census law: never
    re-anchor the offset on the drifted position) - a walk that ends short of
    the waypoint is re-authored toward the SAME cell."""
    script = _farm()
    first = _cell(_moves(script.step(_state()))[0])
    assert first == (100, 108)  # the seeded first draw is (0, 8)
    short = script.step(_state(x=100, y=104))
    assert _cell(_moves(short)[0]) == first


def test_farm_roam_redraws_after_arrival() -> None:
    """Arrival (the tracked position stands on the aim) is what releases the
    hold: the next empty-view tick draws the next offset."""
    script = _farm()
    first_draw, second_draw = _farm_draws(2)
    assert first_draw != second_draw
    first = _cell(_moves(script.step(_state()))[0])
    assert first == (100 + first_draw[0], 100 + first_draw[1])
    nxt = _cell(_moves(script.step(_state(*first)))[0])
    assert nxt == (first[0] + second_draw[0], first[1] + second_draw[1])


def test_farm_roam_redraws_when_a_higher_priority_walk_displaces_the_aim() -> None:
    """An authored action of higher priority (the approach walk) replaces the
    held patrol aim: the next empty-view tick draws fresh near the NEW cell."""
    script = _farm()
    first = _cell(_moves(script.step(_state()))[0])
    far_mob = _mob("Poring", 42, x=150, y=100)
    approach = script.step(_state(nearby=[far_mob]))
    approach_moves = _moves(approach)
    assert approach_moves
    assert _cell(approach_moves[0]) != first
    stood = _cell(approach_moves[0])
    fresh = _cell(_moves(script.step(_state(*stood)))[0])
    assert max(abs(fresh[0] - stood[0]), abs(fresh[1] - stood[1])) <= 8
    assert max(abs(fresh[0] - first[0]), abs(fresh[1] - first[1])) > 8


def test_farm_roam_redraws_after_the_map_changes() -> None:
    """A held aim belongs to its map: a warp invalidates it even when the new
    map's coordinates happen to contain the old cell."""
    script = _farm()
    first_draw, second_draw = _farm_draws(2)
    first = _cell(_moves(script.step(_state()))[0])
    assert first == (100 + first_draw[0], 100 + first_draw[1])
    nxt = _cell(_moves(script.step(_state(map_name="prt_fild04")))[0])
    assert nxt == (100 + second_draw[0], 100 + second_draw[1])
    assert nxt != first


def test_farm_roam_redraws_after_the_bounded_reaim_horizon() -> None:
    """The script layer reads no grid: a never-arrivable aim (the runtime's
    unwalkable-reroll / stuck-cell class) expires after the bounded horizon
    and the next empty-view tick draws a fresh offset."""
    script = _farm()
    first_draw, second_draw = _farm_draws(2)
    targets = [_cell(_moves(script.step(_state()))[0]) for _ in range(ROAM_REAIM_HORIZON + 1)]
    held = [(100 + first_draw[0], 100 + first_draw[1])] * ROAM_REAIM_HORIZON
    assert targets[:ROAM_REAIM_HORIZON] == held
    assert targets[ROAM_REAIM_HORIZON] == (100 + second_draw[0], 100 + second_draw[1])


def test_grind_roam_holds_one_target_across_consecutive_empty_ticks(
    grind_rng: random.Random,
) -> None:
    """The GrindScript twin (what goal-assigned agents without a plan run):
    the same hold contract as the farm roam leg."""
    script = GrindScript()
    targets = []
    for _ in range(4):
        outcome = script.step(_state(goal=Goal.GRIND))
        moves = _moves(outcome)
        assert len(moves) == 1
        targets.append(_cell(moves[0]))
    assert targets[0] != (100, 100)
    assert targets == [targets[0]] * 4


def test_grind_roam_keeps_the_anchored_cell_when_the_walk_falls_short(
    grind_rng: random.Random,
) -> None:
    script = GrindScript()
    first = _cell(_moves(script.step(_state(goal=Goal.GRIND)))[0])
    assert first == (100, 108)  # the mirror's first draw is (0, 8)
    short = script.step(_state(x=100, y=104, goal=Goal.GRIND))
    assert _cell(_moves(short)[0]) == first


def test_grind_roam_redraws_after_arrival(grind_rng: random.Random) -> None:
    script = GrindScript()
    first = _cell(_moves(script.step(_state(goal=Goal.GRIND)))[0])
    nxt = _cell(_moves(script.step(_state(*first, goal=Goal.GRIND)))[0])
    assert nxt != first  # the hold released by arrival: a fresh patrol draw
    assert max(abs(nxt[0] - first[0]), abs(nxt[1] - first[1])) <= 8


def test_grind_roam_redraws_when_a_higher_priority_walk_displaces_the_aim(
    grind_rng: random.Random,
) -> None:
    script = GrindScript()
    first = _cell(_moves(script.step(_state(goal=Goal.GRIND)))[0])
    far_mob = _mob("Lunatic", 7, x=150, y=100)
    approach = script.step(_state(goal=Goal.GRIND, nearby=[far_mob]))
    approach_moves = _moves(approach)
    assert approach_moves
    assert _cell(approach_moves[0]) != first
    stood = _cell(approach_moves[0])
    fresh = _cell(_moves(script.step(_state(*stood, goal=Goal.GRIND)))[0])
    assert max(abs(fresh[0] - stood[0]), abs(fresh[1] - stood[1])) <= 8
    assert max(abs(fresh[0] - first[0]), abs(fresh[1] - first[1])) > 8


def test_grind_roam_redraws_after_the_bounded_reaim_horizon(
    grind_rng: random.Random,
) -> None:
    script = GrindScript()
    # the patched rng is the script's own draw source; mirror from a fresh,
    # identically-seeded instance so expectations never consume its sequence
    mirror = random.Random(7)
    first_draw = mirror.choice(_PATROL_DRAWS)
    second_draw = mirror.choice(_PATROL_DRAWS)
    targets = [
        _cell(_moves(script.step(_state(goal=Goal.GRIND)))[0])
        for _ in range(ROAM_REAIM_HORIZON + 1)
    ]
    held = [(100 + first_draw[0], 100 + first_draw[1])] * ROAM_REAIM_HORIZON
    assert targets[:ROAM_REAIM_HORIZON] == held
    assert targets[ROAM_REAIM_HORIZON] == (100 + second_draw[0], 100 + second_draw[1])


# -- census replay proof -----------------------------------------------------
#
# The census tool (robots.app.movement_census) re-run over a synthetic trace
# session built from the two authoring contracts: BEFORE, the per-tick fresh
# draw the leg-135 window measured (each walk replaced unreached, ~1 cell per
# authoring); AFTER, the real fixed FarmScript driven tick by tick with walks
# that outlast one tick (the held re-aims the runtime pacing holds).


def _script_step() -> dict[str, Any]:
    return {
        "kind": "script_step",
        "script": "FarmScript",
        "status": "ACTIVE",
        "actions": ["MoveTo"],
        "nearest_monster_d": None,
        "nearby_n": 0,
    }


def _move_row(kind: str, pos: tuple[int, int], target: tuple[int, int], **fields: Any) -> dict:
    return {
        "kind": kind,
        "map": "prt_fild08",
        "x": pos[0],
        "y": pos[1],
        "action": "MoveTo",
        "params": {"x": target[0], "y": target[1]},
        **fields,
    }


def _position_row(pos: tuple[int, int]) -> dict[str, Any]:
    return {"kind": "state_tick", "map": "prt_fild08", "x": pos[0], "y": pos[1]}


def _one_cell_toward(pos: tuple[int, int], target: tuple[int, int]) -> tuple[int, int]:
    dx = (target[0] > pos[0]) - (target[0] < pos[0])
    if dx:
        return (pos[0] + dx, pos[1])
    dy = (target[1] > pos[1]) - (target[1] < pos[1])
    return (pos[0], pos[1] + dy)


def _trace(tmp_path: Path, persona: str, rows: list[dict[str, Any]]) -> Path:
    lines = []
    for i, row in enumerate(rows):
        stamp = (T0 + timedelta(seconds=i * TICK_S)).isoformat()
        lines.append(json.dumps({"t": stamp, "persona": persona, **row}) + "\n")
    path = tmp_path / f"{persona}.jsonl"
    path.write_text("".join(lines))
    return path


def _fleet(result: dict[str, Any], persona: str) -> dict[str, Any]:
    return cast(dict[str, Any], result["agents"][persona])


def test_census_replay_abandoned_before_next_collapses(tmp_path: Path) -> None:
    ticks = 12

    # BEFORE: the per-tick fresh draw from the drifted position (the documented
    # leg-135 contract, scripts.py before this fix). The ~2 s walk is replaced
    # by the next tick's fresh draw before arrival: one authoring buys ~1 cell.
    rng = random.Random(11)
    pos = (210, 365)  # the census pocket around prt_fild08 (210,365)
    before: list[dict[str, Any]] = []
    for _ in range(ticks):
        dx, dy = rng.choice(tuple(ROAM_OFFSETS))
        target = (max(0, pos[0] + dx), max(0, pos[1] + dy))
        before.append(_script_step())
        before.append(_move_row("action_executed", pos, target))
        before.append(_move_row("move_performed", pos, target, outcome="dispatched", reason="step"))
        pos = _one_cell_toward(pos, target)
        before.append(_position_row(pos))

    # AFTER: the real fixed script; each patrol walk outlasts one tick, so the
    # next empty-view tick re-authors the SAME aim and the runtime pacing
    # holds it (outcome pending) until the walk lands.
    script = _farm()
    pos = (210, 365)
    pending: tuple[int, int] | None = None
    pending_since = 0.0
    after: list[dict[str, Any]] = []
    for i in range(ticks):
        now = i * TICK_S
        if pending is not None and now - pending_since >= WALK_LAG_S:
            pos = pending
            after.append(_position_row(pos))
            pending = None
        outcome = script.step(_state(*pos))
        moves = _moves(outcome)
        assert len(moves) == 1
        target = _cell(moves[0])
        held = pending is not None
        after.append(_script_step())
        after.append(_move_row("action_executed", pos, target))
        after.append(
            _move_row(
                "move_performed",
                pos,
                target,
                outcome="pending" if held else "dispatched",
                reason="await_pending" if held else "step",
            )
        )
        if pending is None or target != pending:
            # a NEW aim starts its own walk clock; the held re-aims keep the
            # in-flight walk's clock running (that is the runtime's contract)
            pending = target
            pending_since = now

    before_result = _fleet(
        summarize_movement_traces([_trace(tmp_path, "before", before)]), "before"
    )
    after_result = _fleet(summarize_movement_traces([_trace(tmp_path, "after", after)]), "after")

    # both worlds author one patrol MoveTo per empty-view tick
    assert before_result["move_total"] == ticks
    assert after_result["move_total"] == ticks
    assert before_result["purpose"]["roam_patrol"] == ticks
    assert after_result["purpose"]["roam_patrol"] == ticks
    # the after world exercised the held re-aim path (the runtime pacing)
    assert after_result["dispatch"]["held_pending"] >= 1

    # the collapse: before, every authoring is abandoned before the next one;
    # after, the held aim arrives and only then is replaced.
    assert before_result["abandoned_compared"] == ticks - 1
    assert before_result["abandoned_before_next"] == ticks - 1
    assert before_result["abandoned_share_pct"] == 100.0
    assert after_result["abandoned_before_next"] == 0
    assert after_result["abandoned_share_pct"] == 0.0
