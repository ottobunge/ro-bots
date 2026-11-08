"""The dealer approach cell (leg-71 frontier b): the walk closes the last cells.

Leg-71 receipt (ad3f3850, frontier b): xXLunasongXx crossed into prt_in and
from ~23:05 UTC parked at (173-174,128-130) — Chebyshev 2 from the dealer
cell (172,130) — authoring MoveTo every tick and NEVER TalkToNpc (npc rows:
[]). The drive's walk-to-dealer targeted the DEALER'S OWN cell; that cell
can never be entered (the shop npc holds it), so the server stopped the
walk 2 cells out and ``_dealer_talk``'s adjacency gate (DEALER_TALK_RANGE,
the rAthena npc_click acceptance the live window proved: PipinWalker sold
FROM (173,129), Chebyshev 1) then refused every talk — the drive re-authored
the same doomed MoveTo forever, silent at range 2.

The sell arm closes the last cells: when the agent stands farther than
``DEALER_TALK_RANGE`` from the dealer (Chebyshev > 1), author the APPROACH
CELL walk — the proven ``_approach_cell`` intercept pattern from the attack
scripts (the neighbouring cell of the dealer nearest the agent, deterministic
tie-break) — until the agent is dealer-adjacent; only then does TalkToNpc
fire. When a dealer npc is received at the cited cell but the talk still
cannot fire, the drive taps ``dealer_talk_out_of_range`` naming the distance
(tap-before-fix: if the defect still fires, the log names it).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import logging  # noqa: E402

import pytest  # noqa: E402

from robots.app import scripts  # noqa: E402
from robots.app.scripts import (  # noqa: E402
    _MERCHANT_DRIVE_TAPPED,
    GrindScript,
    ScriptStatus,
    _approach_cell,
    _merchant_engage,
)
from robots.domain.actions import MoveTo, TalkToNpc  # noqa: E402
from robots.domain.model import ActorRef, BotState, Goal  # noqa: E402

DEALER_CELL = (172, 130)
"""The cited Weapon Dealer cell (npc/merchants/shops.txt:255)."""


def _state(**over: object) -> BotState:
    base: dict[str, object] = {
        "name": "fixture_0",
        "job": "Novice",
        "base_level": 1,
        "hp": 40,
        "max_hp": 40,
        "sp": 10,
        "max_sp": 10,
        "map_name": "prt_in",
        "x": 174,
        "y": 128,  # the leg-71 park: Chebyshev 2 from the dealer cell
        "goal": Goal.FARM_ITEM,
        "in_party": False,
        "nearby": (),
        "inventory": {"915": 1},  # sellable stock: the sell arm admits
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(over)
    return BotState(**base)  # type: ignore[arg-type]


def _dealer(id: int = 110001762, x: int | None = 172, y: int | None = 130) -> ActorRef:
    return ActorRef(id=id, name="Weapon Dealer#prt", kind="npc", distance=2.2, x=x, y=y)


@pytest.fixture(autouse=True)
def _fresh_merchant_memo():
    scripts.reset_merchant_talk()
    _MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()
    _MERCHANT_DRIVE_TAPPED.clear()


def test_parked_at_chebyshev_two_authors_the_approach_cell_walk() -> None:
    """THE leg-71 defect: parked at (174,128) with the dealer received, the
    drive must close the last cells — walk to the dealer's neighbouring cell
    nearest the agent — never re-author the dealer's own cell again."""
    state = _state(nearby=(_dealer(),))
    outcome = _merchant_engage(state, DEALER_CELL)
    assert outcome.status == ScriptStatus.ACTIVE
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == _approach_cell(*DEALER_CELL, state) == (173, 129)
    assert (action.x, action.y) != DEALER_CELL, "the shop cell itself is never the walk target"


def test_grind_script_step_closes_the_last_cells_the_same_way() -> None:
    """The same contract through the goal script's drive seam (the re-arm
    evaluates ``_merchant_step`` -> ``_merchant_engage`` every tick): the
    parked-at-2 agent's next authored action is the approach-cell walk."""
    outcome = GrindScript().step(_state(nearby=(_dealer(),)))
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (173, 129)


def test_talk_fires_only_at_dealer_adjacency() -> None:
    """The receipt's live proof (PipinWalker sold FROM (173,129), Chebyshev
    1): the talk requires the agent dealer-adjacent — at the park cell
    (174,128) the drive walks, at (173,129) it talks."""
    walking = _merchant_engage(_state(nearby=(_dealer(),)), DEALER_CELL)
    assert not any(isinstance(a, TalkToNpc) for a in walking.actions)
    adjacent = _state(x=173, y=129, nearby=(_dealer(),))
    outcome = _merchant_engage(adjacent, DEALER_CELL)
    (action,) = outcome.actions
    assert isinstance(action, TalkToNpc)
    assert action.npc_id == 110001762


def test_out_of_range_talk_taps_the_named_distance(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tap-before-fix: when a dealer npc IS received at the cited cell but
    the talk cannot fire (the agent out of range), the drive taps
    ``dealer_talk_out_of_range`` naming the Chebyshev distance, so a
    residual range-2 park names itself in the window log."""
    state = _state(nearby=(_dealer(),))
    with caplog.at_level(logging.WARNING, logger="robots.app.scripts"):
        _merchant_engage(state, DEALER_CELL)
    tap_lines = [
        record.getMessage()
        for record in caplog.records
        if "dealer_talk_out_of_range" in record.getMessage()
    ]
    assert tap_lines, "the out-of-range talk must name itself"
    assert "chebyshev=2" in tap_lines[0]


def test_walking_route_without_the_dealer_received_stays_quiet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The tap is for the received-but-unreachable dealer only: the plain
    route walk (no dealer npc in view yet) stays silent — it is the normal
    approach, not a talk-blocked state."""
    state = _state()
    with caplog.at_level(logging.WARNING, logger="robots.app.scripts"):
        outcome = _merchant_engage(state, DEALER_CELL)
    assert not [
        record.getMessage()
        for record in caplog.records
        if "dealer_talk_out_of_range" in record.getMessage()
    ]
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (173, 129)  # the approach cell from (174,128) sans dealer view


def test_field_warp_legs_keep_the_warp_cell_target() -> None:
    """The approach cell is the DEALER-cell correction only: the field/town
    legs walk INTO their warp cells (a neighbouring cell never fires the
    warp), so prt_fild08 keeps the pinned (170,378) target."""
    scripts.reset_merchant_talk()
    state = _state(map_name="prt_fild08", x=180, y=320, nearby=())
    outcome = GrindScript().step(state)
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (170, 378)
