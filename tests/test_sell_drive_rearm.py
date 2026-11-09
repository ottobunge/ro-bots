"""The sell-drive re-arm on incomplete trips + the goal-script interleave (leg 70).

Leg 70 (receipt 8477d851): s00's sell trip was ADMITTED verbatim
(``merchant-drive: sell arm admitted (map=pay_fild04 dest=(17, 165) zeny=0
stock=2)``), the walk advanced 213,325 -> 188,315 on accepted sends, and
then the drive's far authoring STOPPED MID-ROUTE: the heartbeat goal review
flipped grind->social (trace ``goal_review`` 19:16:58 UTC), ``_goal_script``
replaced the drive-bearing GrindScript with IdleTownScript, and the drive
was never REACHED again -- 425 IdleTownScript jitter steps to close, zero
merchant-drive evaluations after 19:17:54, no TalkToNpc, no sell, zeny 0.
The drive lives INSIDE ``FarmScript``/``GrindScript.step`` only, so any
goal flip orphans an armed-but-unfinished trip.

The contract under test: the sell drive is re-armed EVERY tick at the brain
level, ahead of whichever goal script is active. An admitted, incomplete
trip (sellable stock held, drive admits) keeps owning its route walk
(reaffirming every fifth evaluation, including across goal flips)
under ANY goal script until (a) the trip COMPLETES -- the stock sells, the
admission turns off, the goal script resumes -- or (b) the admission names
a refusal (terminal for the trip: the map is off ``MERCHANT_ROUTE``), in
which case the goal script applies unchanged. Farming interleaves without
starving: a refusing drive returns None and the farm/grind script's own
step (engage, roam) applies exactly as before.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import pytest  # noqa: E402

from robots.adapters.chat.stub import StaticChatGenerator  # noqa: E402
from robots.adapters.decision.stub import ScriptedDecisionModel  # noqa: E402
from robots.app import scripts  # noqa: E402
from robots.app.brain import EventDrivenBrain  # noqa: E402
from robots.app.scripts import (  # noqa: E402
    MERCHANT_ROUTE,
    GrindScript,
    ScriptStatus,
    merchant_admission_refusal,
)
from robots.domain.actions import Attack, MoveTo  # noqa: E402
from robots.domain.model import ActorRef, BotState, Goal  # noqa: E402

#: s00's leg-70 shape verbatim: pay_fild04 (213,325), 511 Green Herb x2 +
#: the worn knife, zeny 0. The drive admits on the stock alone.
S00_POS = (213, 325)
S00_INVENTORY = {"511": 2, "1201": 1}
PAY_FILD04_EXIT = MERCHANT_ROUTE["pay_fild04"]


def _answers(change_goal: str) -> dict:
    """Heartbeat-review answers with the goal review pre-decided."""
    return {
        "next_action": {"type": "choice", "choice": "grind", "confidence": 0.9},
        "target_choice": {"type": "choice", "choice": "closest", "confidence": 0.9},
        "should_reply": {"type": "noul", "noul": 0.1},
        "hp_critical": {"type": "noul", "noul": 0.05},
        "threat_near": {"type": "noul", "noul": 0.2},
        "accept_invite": {"type": "noul", "noul": 0.0},
        "use_premade": {"type": "noul", "noul": 0.0},
        "premade_pick": {"type": "choice", "choice": "none", "confidence": 0.9},
        "chat_urgency": {"type": "score", "score": 0.5},
        "goal_review": {"type": "score", "score": 1.0},
        "change_goal": {"type": "choice", "choice": change_goal, "confidence": 0.9},
        "react_monster": {"type": "choice", "choice": "ignore", "confidence": 0.9},
        "react_damage": {"type": "choice", "choice": "keep", "confidence": 0.9},
        "farm_duration": {"type": "score", "score": 1.0},
        "farm_target": {"type": "choice", "choice": "Poring", "confidence": 0.9},
    }


def _s00_brain() -> EventDrivenBrain:
    """A brain wired like production s00: resolver present, reachable None
    (agent_runtime wires travel_plan_factory only), scripted decisions."""
    model = ScriptedDecisionModel(answers=_answers("keep"), queue=[])
    return EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        travel_resolver=lambda _map, _x, _y: None,
    )


def _s00_state(**over: object) -> BotState:
    base: dict[str, object] = {
        "name": "rearm_fixture",
        "job": "Novice",
        "base_level": 1,
        "hp": 40,
        "max_hp": 40,
        "sp": 10,
        "max_sp": 10,
        "map_name": "pay_fild04",
        "x": S00_POS[0],
        "y": S00_POS[1],
        "goal": Goal.GRIND,
        "in_party": False,
        "nearby": (),
        "inventory": dict(S00_INVENTORY),
        "zeny": 0,
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(over)
    return BotState(**base)  # type: ignore[arg-type]


def _move(actions: tuple) -> MoveTo:
    moves = [action for action in actions if isinstance(action, MoveTo)]
    assert len(moves) == 1, actions
    return moves[0]


@pytest.fixture(autouse=True)
def _clear_merchant_latches():
    """The admission tap and the dealer-talk latch are module-level; keep
    tests isolated from each other's verdict history."""
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    scripts.reset_merchant_talk()
    yield
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    scripts.reset_merchant_talk()


def test_goal_flip_to_social_does_not_orphan_the_armed_trip() -> None:
    """THE leg-70 defect, end to end: a trip armed under GRIND and walked
    mid-route survives the goal flip to SOCIAL -- the next steps still
    author the drive's route walk (before the fix the flip installed
    IdleTownScript and the drive was never evaluated again)."""
    brain = _s00_brain()
    state = _s00_state()
    brain._run_review(state, _answers("keep"), [])  # grind: GrindScript + wiring
    assert isinstance(brain._script, GrindScript)
    first = brain.step_script(state)
    assert _move(first.actions) == MoveTo(x=PAY_FILD04_EXIT[0], y=PAY_FILD04_EXIT[1])

    # The flip: grind -> social replaces the drive-bearing script with the
    # jitter script (the leg-70 trace shape, verbatim mechanism).
    brain._run_review(state, _answers("social"), [])
    assert type(brain._script).__name__ == "IdleTownScript"
    state = dataclasses.replace(state, goal=Goal.SOCIAL)

    # The re-arm retains ownership AND patience through the goal flip.
    for _ in range(4):
        outcome = brain.step_script(state)
        assert outcome.actions == ()
        assert outcome.status == ScriptStatus.ACTIVE
    assert _move(brain.step_script(state).actions) == MoveTo(*PAY_FILD04_EXIT)


def test_rearm_evaluates_every_tick_and_reaffirms_the_trip_per_cadence() -> None:
    """The drive keeps ownership under social; its walk author stays patient."""
    brain = _s00_brain()
    state = _s00_state()
    brain._run_review(state, _answers("keep"), [])
    brain._run_review(state, _answers("social"), [])
    state = dataclasses.replace(state, goal=Goal.SOCIAL)
    for tick in range(11):
        outcome = brain.step_script(state)
        assert outcome.status == ScriptStatus.ACTIVE
        assert outcome.actions == ((MoveTo(*PAY_FILD04_EXIT),) if tick % 5 == 0 else ())


def test_sold_stock_releases_the_trip_to_the_goal_script() -> None:
    """Completion: the stock sells (inventory counts drop the sellables),
    the admission turns off (no_stock_below_zeny_floor) and the goal
    script's own step applies again -- farming/social resumes, the trip
    does not latch forever."""
    brain = _s00_brain()
    state = _s00_state()
    brain._run_review(state, _answers("keep"), [])
    brain._run_review(state, _answers("social"), [])
    state = dataclasses.replace(state, goal=Goal.SOCIAL)
    outcome = brain.step_script(state)
    assert _move(outcome.actions) == MoveTo(x=PAY_FILD04_EXIT[0], y=PAY_FILD04_EXIT[1])

    state = dataclasses.replace(state, inventory={"1201": 1})  # the 511s sold
    refusal = merchant_admission_refusal(state)
    assert refusal is not None
    assert refusal[0] == "no_stock_below_zeny_floor"
    outcome = brain.step_script(state)
    move = _move(outcome.actions)
    # The jitter script's own 1-cell step (the (0,1) direction first), not
    # the dealer-bound walk: the sold stock released the trip.
    assert (move.x, move.y) == (S00_POS[0], S00_POS[1] + 1)


def test_off_route_map_is_a_terminal_refusal_and_farming_applies() -> None:
    """Terminal refusal: mid-trip the agent stands on a map absent from
    MERCHANT_ROUTE (moc_fild02, the desert chain) -- the drive fails closed
    (map_not_on_merchant_route), the re-arm stops, and the goal script's
    step applies instead of a walk into an unroutable dealer trip."""
    brain = _s00_brain()
    state = _s00_state(map_name="moc_fild02", x=350, y=336)
    brain._run_review(state, _answers("keep"), [])
    brain._run_review(state, _answers("social"), [])
    state = dataclasses.replace(state, goal=Goal.SOCIAL)
    refusal = merchant_admission_refusal(state)
    assert refusal is not None
    assert refusal[0] == "map_not_on_merchant_route"
    move = _move(brain.step_script(state).actions)
    assert (move.x, move.y) == (350, 337)  # the jitter step, not a trip leg


def test_farming_interleaves_with_the_trip_without_being_starved() -> None:
    """The interleave both ways: with sellable stock held the trip outranks
    the engage (existing contract), and once the stock sells the SAME
    farming goal resumes engaging the monster in view -- no state, no
    latch, just the want."""
    brain = _s00_brain()
    poring = ActorRef(id=7, name="Poring", kind="monster", distance=2.0, x=214, y=325)
    state = _s00_state(nearby=(poring,))
    brain._run_review(state, _answers("keep"), [])
    armed = brain.step_script(state)
    assert _move(armed.actions) == MoveTo(x=PAY_FILD04_EXIT[0], y=PAY_FILD04_EXIT[1])

    state = dataclasses.replace(state, inventory={"1201": 1})  # sold; want cleared
    resumed = brain.step_script(state)
    # The farm engage resumed: the Attack itself in range, or an approach
    # toward the monster -- anything but the dealer-bound warp leg.
    assert resumed.actions, "the sold stock must release the farm engage"
    for action in resumed.actions:
        if isinstance(action, MoveTo):
            assert (action.x, action.y) != (PAY_FILD04_EXIT[0], PAY_FILD04_EXIT[1])
        else:
            assert isinstance(action, Attack)
