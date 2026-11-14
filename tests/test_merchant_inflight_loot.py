"""Leg 102: admission credits only this client's collectible live loot."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.trace_log import TraceLog
from robots.domain.actions import Loot, MoveTo
from robots.domain.farm import FarmPlan
from robots.domain.model import BotState, Goal
from tests.test_loot_attribution import ack
from tests.test_loot_priority import PICKUP, walk_ack
from tests.test_playing_runtime import Wire, entry_at, monster
from tests.test_trace_log import make_agent
from tests.test_zc_item_entry_floor import zc_item_entry


@pytest.fixture(autouse=True)
def fresh_trip():
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()


def client_with_loot(*, x: int = 48, item: int = 909, amount: int = 1) -> PlayingClient:
    wire = Wire()
    wire.frames = []
    wire.add(
        entry_at(42, 37),
        struct.pack("<H16sHH", 0x0091, b"prt_fild08", 42, 37),
        zc_item_entry(aid=321, item=item, x=x, y=38, amount=amount),
    )
    cache = MapCache(
        tuple(WalkMap(m, 100, 100, bytes(10000)) for m in ("prt_fild08", "moc_fild01"))
    )
    client = PlayingClient(wire, cache=cache)
    client.farm_map = "prt_fild08"
    return client


def stock_state(client: PlayingClient) -> BotState:
    return replace(
        client.build_native_state(Goal.FARM_ITEM),
        inventory={"511": 1, "1201": 1},
        inventory_known=True,
        zeny=0,
    )


@pytest.mark.parametrize("deferred", [False, True])
def test_one_stock_plus_live_loot_admits_and_collects_before_dealer(deferred, caplog):
    client = client_with_loot()
    if deferred:
        client.perform_native(Loot())
    state = stock_state(client)
    assert scripts.merchant_drive_cell(state) == scripts.MERCHANT_ROUTE[state.map_name]
    assert state.merchant_inflight_pending == int(deferred)
    assert state.merchant_inflight_visible == int(not deferred)
    assert "stock=1 inflight=1" in caplog.text
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (Loot(),)
    # A retained farm plan executes authored Loot without mechanical fallback.
    client.perform_native(outcome.actions[0])
    assert client.wire.moves[0] == (43, 37)
    assert not client.wire.sent
    for _ in range(8):
        if client.wire.sent:
            break
        point = client.wire.moves[-1]
        client.wire.add(walk_ack(point, point))
        client.drain_native_events()
    assert client.wire.sent == [PICKUP]
    assert scripts.merchant_drive_cell(stock_state(client)) is None  # no ack credit
    bagged = replace(stock_state(client), inventory={"511": 1, "909": 1, "1201": 1})
    outcome = scripts._merchant_step(bagged)
    assert outcome is not None
    assert outcome.actions != (Loot(),)


@pytest.mark.parametrize("end", ["vanish", "refused", "map", "session"])
def test_credit_decays_on_pickup_lifecycle_boundary(end):
    client = client_with_loot(x=43)
    client.build_native_state(Goal.FARM_ITEM)
    client._rest_seq = 0
    client.perform_native(Loot())
    assert scripts.merchant_drive_cell(stock_state(client)) is not None
    client._rest_seq = None
    if end == "vanish":
        client.wire.add(struct.pack("<HI", 0x00A1, 321))
    elif end == "refused":
        client.perform_native(Loot())
        client.wire.add(ack(6))
    elif end == "map":
        client.wire.add(struct.pack("<H16sHH", 0x0091, b"moc_fild01", 42, 37))
    else:
        client.wire.native_epoch += 1
        client.wire.selection_epoch = client.wire.map_epoch = client.wire.native_epoch
        client.wire.frames = []
        client.wire.add(
            entry_at(42, 37),
            struct.pack("<H16sHH", 0x0091, b"prt_fild08", 42, 37),
        )
    state = stock_state(client)
    assert state.merchant_inflight_pending + state.merchant_inflight_visible == 0
    assert scripts.merchant_drive_cell(state) is None


def test_one_stock_without_loot_keeps_trip_minimum(caplog):
    client = client_with_loot()
    client.wire.add(struct.pack("<HI", 0x00A1, 321))
    assert scripts.merchant_drive_cell(stock_state(client)) is None
    assert "merchant_stock_below_trip_minimum" in caplog.text


def test_visible_floor_on_another_farm_map_gets_no_credit():
    client = client_with_loot()
    client.farm_map = "pay_fild04"
    assert scripts.merchant_drive_cell(stock_state(client)) is None


def test_pending_and_visible_are_deduplicated_and_capped():
    client = client_with_loot(amount=100)
    client.perform_native(Loot())
    client.wire.add(zc_item_entry(aid=322, item=909, x=49, y=38, amount=100))
    state = stock_state(client)
    assert state.merchant_inflight_pending == 2
    assert state.merchant_inflight_visible == 0


@pytest.mark.parametrize("blocked", ["unsellable", "threat", "exhausted", "unreachable"])
def test_uncollectible_loot_does_not_admit(blocked):
    client = client_with_loot(item=1201 if blocked == "unsellable" else 909)
    client.build_native_state(Goal.FARM_ITEM)
    if blocked == "threat":
        client.wire.add(monster(at=(43, 38)))
    elif blocked == "exhausted":
        client._loot_settle_attempts[321] = 2
    elif blocked == "unreachable":
        client.cache = MapCache((WalkMap("prt_fild08", 100, 100, bytes([1]) * 10000),))
    assert scripts.merchant_drive_cell(stock_state(client)) is None


def test_town_single_bagged_unit_still_sells_without_off_map_credit():
    state = replace(stock_state(client_with_loot()), map_name="prt_in")
    assert scripts.merchant_drive_cell(state) == (172, 130)
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert all(not isinstance(a, Loot) for a in outcome.actions)
    assert any(isinstance(a, MoveTo) for a in outcome.actions)


def test_credited_pickup_takes_priority_over_unrelated_nearer_loot():
    client = client_with_loot()
    client.wire.add(zc_item_entry(aid=322, item=1201, x=43, y=38))
    outcome = scripts._merchant_step(stock_state(client))
    assert outcome is not None
    client.perform_native(outcome.actions[0])
    assert client.wire.moves == [(43, 37)]
    assert not client.wire.sent


def test_host_binds_only_its_own_retained_farm_map_and_runs_pickup_leg(tmp_path):
    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _, _ = make_agent(trace, tmp_path)
    client = client_with_loot()
    client.farm_map = None
    agent.client = client
    agent.goal = Goal.FARM_ITEM
    assert isinstance(agent.brain, EventDrivenBrain)
    agent.brain._plan = FarmPlan(1, "pay_fild04", ("Poring",), 300, 20)
    state = agent.build_state()
    assert state.merchant_inflight_visible == 0
    agent.brain._plan = replace(agent.brain._plan, map_name="prt_fild08")
    state = replace(agent.build_state(), inventory={"511": 1}, inventory_known=True)
    assert state.merchant_inflight_visible == 1
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert agent._script_actions(state, outcome.actions) == (Loot(),)
    agent.execute_actions(outcome.actions)
    assert client.wire.moves == [(43, 37)]
    trace.close()


def test_same_id_replacement_expires_old_credit():
    client = client_with_loot()
    client.perform_native(Loot())
    assert stock_state(client).merchant_inflight_pending == 1
    client.wire.add(zc_item_entry(aid=321, item=1201, x=48, y=38))
    state = stock_state(client)
    assert scripts.merchant_drive_cell(state) is None
    assert any(row["outcome"] == "expired" for row in client.loot_telemetry)


def test_other_agents_floor_frames_cannot_fund_admission():
    observer = client_with_loot()
    other = client_with_loot()
    other.wire.add(struct.pack("<HI", 0x00A1, 321))
    assert scripts.merchant_drive_cell(stock_state(observer)) is not None
    assert scripts.merchant_drive_cell(stock_state(other)) is None


def test_two_live_units_can_fund_pickup_before_an_empty_bag_sells():
    client = client_with_loot(amount=2)
    state = replace(stock_state(client), inventory={"1201": 1})
    assert scripts.merchant_drive_cell(state) is not None
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (Loot(),)
