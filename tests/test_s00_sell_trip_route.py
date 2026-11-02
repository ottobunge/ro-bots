"""s00's field-side sell trip: the pay_fild04 route legs + the stock set.

Leg 67 (receipt 9e538f6c) held the field-to-town arc for s00 structurally
off: the agent parked on pay_fild04 holding 511 Green Herb x2 + 905 Stem
x3 + 906 Pointed Scale x1 at zeny 0 and (1) the sellable sets carried only
the prt_fild08 drop species, so ``has_stock`` read False all window;
(2) ``MERCHANT_ROUTE`` had no pay_fild04 key, so even with stock the drive
returned None (fail-closed, "Unknown maps are absent"); (3) the travel
network (``TRAVEL_ROUTES``/``EXIT_CELLS``/``ONWARD``) had no pay_fild04
exit, so no resolver leg existed either.

The route is pinned public warp bytes (rathena e985006171d2, the same
pre-re tree the merchant trip already cites):
- ``npc/pre-re/warps/fields/payon_fild.txt:30``
  ``pay_fild04,17,165,0  warp  payf002  2,8,moc_fild01,376,162`` - the
  field's way out toward the prt_fild08 arc;
- ``npc/pre-re/warps/fields/morroc_fild.txt:24``
  ``moc_fild01,239,382,0  warp  mocf006  12,1,prt_fild08,233,20`` - the
  moc_fild01 leg that lands ON prt_fild08, whose field->prontera->prt_in
  dealer arc three leg-67 sellers already walked. pay_fild04's other exit
  (``pay_fild04,194,17 -> moc_fild02,350,336``, payon_fild.txt:31) leads
  into the desert interior chain, not toward the dealer map set - the one
  cited exit is the dealer-bound one.

The stock set is re-derived from the pinned pay_fild04 spawn declarations
(``npc/pre-re/mobs/fields/payon.txt:63-70``: Poring 1002, Drops 1113,
Poporing 1031, Marin 1242, Ghostring 1120, Mastering 1090, Angeling 1096,
Deviling 1582) through their served ``db/pre-re/mob_db.yml`` Drops rows
(served image verified identical to the repo tree) resolved against the
pre-re item dbs, EXCLUDING the drop Knife_ 1202 (a NOVICE_WANTED_WEAPONS
member the setup phase wears; a worn weapon stays in received inventory, so
inside the sellable set it would false-arm the sell arm of every equipped
Novice — the leg-40 release pins the split). The zeny floor is NOT part of
this fix's behavior: the
drive's ``affordable or has_stock`` gate already admits the sell arm on
stock at zeny 0 (the trip EARNS zeny); ``MERCHANT_ZENY_MIN`` governs only
the BUY arm's travel budget. The tests below pin that split so the floor
can never grow back into the sell arm.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters.native_navigation import MapCache, WalkMap  # noqa: E402
from robots.app.brain import EventDrivenBrain  # noqa: E402
from robots.app.scripts import (  # noqa: E402
    MERCHANT_ROUTE,
    SELLABLE_ITEM_IDS,
    GrindScript,
    merchant_drive_cell,
)
from robots.app.travel_routing import ONWARD, travel_plan_for  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from robots.knowledge.travel_routes import EXIT_CELLS, TRAVEL_ROUTES  # noqa: E402
from tests.conftest import make_state  # noqa: E402
from tests.test_host_memory import memory_host  # noqa: E402
from tests.test_merchant_drive import _state  # noqa: E402

PAY_FILD04_EXIT = (17, 165)
MOC_FILD01_LEG = (239, 382)

#: The full field->dealer chain, every leg pinned (module docstring + the
#: leg-67 proven arc): exit warp -> moc_fild01 warp -> prt_fild08 field
#: warp -> prontera prt05 entry -> the dealer cell.
PAY_FILD04_PLAN = (
    ("pay_fild04", 17, 165),
    ("moc_fild01", 239, 382),
    ("prt_fild08", 170, 378),
    ("prontera", 177, 221),
    ("prt_in", 172, 130),
)

#: The derived pay_fild04 drop set: every Drops row of the pinned spawn
#: species, resolved to item ids on the served pre-re dbs.
PAY_FILD04_DROPS = (
    509,
    510,
    511,
    512,
    514,
    529,
    531,
    603,
    604,
    610,
    619,
    620,
    694,
    695,
    700,
    714,
    720,
    722,
    909,
    910,
    912,
    938,
    983,
    1002,
    1039,
    1059,
    1207,
    1602,
    2116,
    2254,
    2255,
    2257,
    2274,
    2282,
    2324,
    2336,
    4001,
    4004,
    4033,
    4047,
    4054,
    4174,
    4196,
    4197,
    5035,
    7023,
)


def test_merchant_route_carries_the_pay_fild04_chain() -> None:
    """The drive's engage cells: pay_fild04 walks INTO the payf002 warp and
    moc_fild01 walks INTO the mocf006 warp; the existing prt_fild08 ->
    prontera -> prt_in keys carry the rest (the leg-67 proven arc)."""
    assert MERCHANT_ROUTE["pay_fild04"] == PAY_FILD04_EXIT
    assert MERCHANT_ROUTE["moc_fild01"] == MOC_FILD01_LEG
    for map_name in ("pay_fild04", "moc_fild01", "prt_fild08", "prontera", "prt_in"):
        assert MERCHANT_ROUTE.get(map_name) is not None, map_name


def test_travel_network_carries_the_pay_fild04_exit() -> None:
    """The resolver's tables: ONE cited exit (unconditional resolution - the
    field is one walkable component), then the onward legs to the dealer."""
    assert EXIT_CELLS["pay_fild04"] == (PAY_FILD04_EXIT,)
    assert TRAVEL_ROUTES["pay_fild04"] == PAY_FILD04_PLAN
    assert ONWARD["pay_fild04"] == PAY_FILD04_PLAN[1:]


def test_travel_plan_resolves_the_pay_fild04_exit_live() -> None:
    """A grid carrying pay_fild04 resolves the exit from the agent's cell -
    s00 parked at (209,177) walks to the payf002 warp cell."""
    cache = MapCache((WalkMap("pay_fild04", 400, 400, bytes(400 * 400)),))
    plan = travel_plan_for(cache, "pay_fild04", (209, 177))
    assert plan == PAY_FILD04_PLAN


def test_sellable_sets_carry_the_pay_fild04_drops() -> None:
    """The shop-loop filter set carries the derived field drops - 511 Green
    Herb is what s00 actually holds (leg 67: inventory_counts frozen at
    {"511": 2, "905": 3, "906": 1, "1201": 1})."""
    for item_id in PAY_FILD04_DROPS:
        assert item_id in SELLABLE_ITEM_IDS, item_id


def test_drive_arms_on_s00s_actual_bag() -> None:
    """The leg-67 triple gate, end to end: a Novice parked on pay_fild04
    with s00's exact bag (511 x2 + 905 x3 + 906 x1 + the worn knife) at
    zeny 0 gets the engage cell - the trip EARNS the zeny. The worn knife
    (the leg-40 weapon release) does not block a stock holder."""
    state = _state(
        map_name="pay_fild04",
        x=209,
        y=177,
        inventory={"511": 2, "905": 3, "906": 1, "1201": 1},
        zeny=0,
    )
    assert merchant_drive_cell(state) == PAY_FILD04_EXIT


def test_drive_arms_mid_chain_on_moc_fild01() -> None:
    """The chain's middle map: an agent that warped onto moc_fild01 mid-trip
    walks the mocf006 leg toward prt_fild08 (unknown maps fail closed - this
    one must be known)."""
    state = _state(map_name="moc_fild01", x=376, y=162, inventory={"511": 2}, zeny=0)
    assert merchant_drive_cell(state) == MOC_FILD01_LEG


def test_sell_arm_admits_on_stock_regardless_of_zeny() -> None:
    """The zeny-floor decision (leg 67 gate 2): the sell trip is admissible
    when the bag has sellable stock REGARDLESS of zeny - the trip EARNS
    zeny. MERCHANT_ZENY_MIN governs the BUY arm only (a travel-cost guard
    for the spending trip); it must never grow back into the sell arm."""
    for zeny in (0, None):  # None = balance not yet received (fail-closed buy)
        state = _state(map_name="pay_fild04", inventory={"511": 2}, zeny=zeny)
        assert merchant_drive_cell(state) == PAY_FILD04_EXIT, zeny


def test_zeny_floor_still_governs_the_buy_arm() -> None:
    """The floor's real job: a Novice with NO sellable stock and zeny under
    the budget keeps farming - the trip would only spend."""
    state = _state(map_name="prontera", inventory={"1201": 1}, zeny=0)
    assert merchant_drive_cell(state) is None
    # unknown balance + no stock: fail-closed (window-28 contract)
    state = _state(map_name="prontera", inventory={"1201": 1}, zeny=None)
    assert merchant_drive_cell(state) is None


def test_grind_on_pay_fild04_gets_the_route_and_merchant_wiring(tmp_path) -> None:
    """brain._goal_script on pay_fild04 hands the GrindScript the pinned
    plan AND the resolver/merchant wiring - a plan-less farming goal on the
    Archer-village field can still run the sell drive (leg 67: s00's trip
    could never arm from pay_fild04)."""
    host = memory_host(tmp_path)
    try:
        agent = next(iter(host.agents.values()))
        brain = agent.brain
        assert brain is not None
        assert isinstance(brain, EventDrivenBrain)
    finally:
        host.stop()
    script = brain._goal_script(Goal.GRIND, make_state(map_name="pay_fild04"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == PAY_FILD04_PLAN
