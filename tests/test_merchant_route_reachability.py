"""The merchant legs respect interior components (leg 37 defect 2's second half).

MERCHANT_ROUTE["prt_in"] = (172,130) and MERCHANT_ROUTE_RETURN["prt_in"] =
(168,124) are pinned PRT05-interior cells. An agent that woke up in the prt03
interior (xXLunasongXx's leg-37 trap, one layer over) cannot walk to either:
the interiors are genuinely disconnected. The dealer trip must resolve
reachability like the exit door does — same-component keeps the pinned leg;
a foreign component walks the agent's OWN door first (and the prontera leg
of the route takes over from there).
"""

from __future__ import annotations

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.scripts import _merchant_step
from robots.app.travel_routing import TravelRouter
from robots.domain.actions import MoveTo
from tests.conftest import make_state


def walled_prt_in() -> MapCache:
    """The two-interior prt_in fixture (mirrors the brain-wiring tests)."""
    width, height = 300, 200
    tiles = bytearray([1]) * (width * height)
    rooms = {
        (53, 105): (40, 95, 60, 115),
        (168, 124): (160, 115, 175, 140),
    }
    for _door, (x0, y0, x1, y1) in rooms.items():
        for y in range(y0, y1):
            for x in range(x0, x1):
                tiles[x + y * width] = 0
    return MapCache((WalkMap("prt_in", width, height, bytes(tiles)),))


def _outbound_state(**over: object):
    """A Novice with sellable stock on prt_in: the outbound want holds."""
    base: dict[str, object] = {
        "job": "Novice",
        "inventory_known": True,
        "inventory": {"915": 3},
        "map_name": "prt_in",
        "x": 44,
        "y": 102,
        "nearby": (),
    }
    base.update(over)
    return make_state(**base)


def test_router_reachable_same_region_true_cross_component_false() -> None:
    router = TravelRouter(walled_prt_in())
    assert router.reachable("prt_in", (44, 102), (53, 105)) is True
    assert router.reachable("prt_in", (44, 102), (172, 130)) is False
    assert router.reachable("nowhere", (1, 1), (2, 2)) is None  # no authority


def test_trapped_merchant_walks_its_own_door_not_the_dealer_cell() -> None:
    """The prt03-interior agent cannot reach the dealer cell (PRT05): the
    outbound leg starts with the agent's OWN door; from prontera the route's
    own prontera leg re-enters through the prt05 warp."""
    router = TravelRouter(walled_prt_in())
    outcome = _merchant_step(
        _outbound_state(), resolver=router.travel_plan, reachable=router.reachable
    )
    assert outcome is not None
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (53, 105)


def test_same_component_merchant_keeps_the_dealer_leg() -> None:
    router = TravelRouter(walled_prt_in())
    outcome = _merchant_step(
        _outbound_state(x=166, y=137),
        resolver=router.travel_plan,
        reachable=router.reachable,
    )
    assert outcome is not None
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (172, 130)


def test_no_reachable_authority_keeps_the_pinned_leg() -> None:
    """Without the authority (no router wired) the pinned leg is unchanged."""
    outcome = _merchant_step(_outbound_state())
    assert outcome is not None
    (action,) = outcome.actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (172, 130)
