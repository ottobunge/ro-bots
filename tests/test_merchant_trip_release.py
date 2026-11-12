"""Leg 95: merchant travel must yield a stalled slot without losing its stock."""

from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pytest

from robots.adapters.native_navigation import MapCache, shortest_path
from robots.app import scripts
from robots.app.scripts import FarmScript, merchant_admission_refusal, merchant_drive_cell
from robots.app.travel_routing import travel_plan_for
from robots.domain.actions import Attack, TalkToNpc
from robots.domain.model import ActorRef
from robots.knowledge.travel_routes import TRAVEL_ROUTES
from tests.test_merchant_drive import _plan, _state
from tests.test_sell_drive_rearm import _s00_brain

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def fresh_trip():
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()


def test_no_progress_releases_retained_farm_script_and_retries_later(monkeypatch, caplog):
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0], raising=False)
    state = _state(
        inventory={"511": 2, "1201": 1},
        zeny=125,
        nearby=(ActorRef(123, "Poring", "monster", 1.0, 171, 300),),
    )
    brain = _s00_brain()
    farm = FarmScript(_plan())
    brain._script = farm
    assert not any(isinstance(a, Attack) for a in brain.step_script(state).actions)
    now[0] = 60.0
    assert any(isinstance(a, Attack) for a in brain.step_script(state).actions)
    assert brain._script is farm
    assert state.inventory == {"511": 2, "1201": 1}
    assert "merchant_trip_released_no_progress" in caplog.text
    for now[0] in (61.0, 100.0, 179.0):
        assert any(isinstance(a, Attack) for a in brain.step_script(state).actions)
    now[0] = 180.0
    assert not any(isinstance(a, Attack) for a in brain.step_script(state).actions)
    assert "merchant_trip_retry" in caplog.text


@pytest.mark.parametrize("item", ["501", "511"])
@pytest.mark.parametrize("job", ["Novice", "Thief"])
def test_single_cheap_item_does_not_fund_a_cross_map_sell_trip(item, job, caplog):
    state = _state(map_name="pay_fild04", job=job, inventory={item: 1, "1201": 1}, zeny=125)
    assert merchant_drive_cell(state) is None
    assert merchant_admission_refusal(state) is not None
    assert "admitted" not in caplog.text
    if job == "Novice" and item == "511":
        assert "merchant_stock_below_trip_minimum" in caplog.text
        assert "stock=1" in caplog.text
        assert "trip_min=2" in caplog.text


def test_nonpositive_stock_never_admits():
    state = _state(inventory={"511": 0, "915": -1, "1201": 1}, zeny=125)
    assert merchant_drive_cell(state) is None


@pytest.mark.parametrize("progress", ["toward", "map_advance", "jitter", "map_backtrack", "veto"])
def test_only_received_progress_toward_dealer_extends_deadline(monkeypatch, progress):
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0], raising=False)
    state = _state(map_name="pay_fild04", x=200, y=200, inventory={"511": 2})
    assert scripts._merchant_step(state) is not None
    now[0] = 59.0
    target = None
    if progress == "toward":
        state = replace(state, x=150)
    elif progress == "map_advance":
        state = replace(state, map_name="moc_fild01", x=376, y=162)
    elif progress == "jitter":
        state = replace(state, x=201)
    elif progress == "map_backtrack":
        state = replace(state, map_name="prt_fild08", x=233, y=20)
    else:

        def target(*_):
            return None

    assert scripts._merchant_step(state, travel_target=target) is not None
    if progress == "map_backtrack":
        state = replace(state, map_name="pay_fild04", x=200, y=200)
        now[0] = 100.0
        assert scripts._merchant_step(state) is not None
        now[0] = 119.0
    else:
        now[0] = 60.0
    outcome = scripts._merchant_step(state, travel_target=target)
    assert (outcome is not None) == (progress in ("toward", "map_advance"))


def test_dealer_contact_keeps_existing_one_talk_hold(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0], raising=False)
    state = _state(
        map_name="prt_in",
        x=172,
        y=129,
        inventory={"511": 1},
        nearby=(ActorRef(999, "Weapon Dealer", "npc", 1.0, 172, 130),),
    )
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (TalkToNpc(999),)
    now[0] = 1000.0
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == ()


@pytest.mark.parametrize("source", ["pay_fild04", "moc_fild01", "prt_fild05"])
def test_route_resolves_and_each_hop_matches_pinned_warp_declarations(source):
    cache = MapCache.load(
        REPO / "rathena/db/map_cache.dat", REPO / "rathena/db/pre-re/map_cache.dat"
    )
    start = {"pay_fild04": (209, 177), "moc_fild01": (376, 162), "prt_fild05": (200, 200)}[source]
    plan = travel_plan_for(cache, source, start)
    assert plan is not None
    assert plan == TRAVEL_ROUTES[source]
    assert [leg[0] for leg in plan][-2:] == ["prontera", "prt_in"]
    files = [
        *(REPO / "rathena/npc/pre-re/warps/fields").glob("*.txt"),
        REPO / "rathena/npc/warps/cities/prontera.txt",
    ]
    warps = []
    for file in files:
        for line in file.read_text().splitlines():
            bits = line.split()
            if len(bits) >= 4 and bits[1] == "warp":
                m, raw_x, raw_y, _ = bits[0].split(",")
                rx, ry, dest, dx, dy = bits[3].split(",")
                warps.append(
                    (m, int(raw_x), int(raw_y), int(rx), int(ry), dest, (int(dx), int(dy)))
                )
    position = start
    for (m, x, y), next_leg in pairwise(plan):
        assert shortest_path(cache.get(m), position, (x, y))[-1] == (x, y)
        matches = [
            w
            for w in warps
            if w[0] == m and abs(x - w[1]) <= w[3] and abs(y - w[2]) <= w[4] and w[5] == next_leg[0]
        ]
        assert matches, (m, x, y, next_leg)
        position = matches[0][6]
    assert scripts.MERCHANT_ROUTE[source] == plan[0][1:]
