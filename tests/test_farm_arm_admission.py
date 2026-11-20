"""Leg-117: a drained merchant lease yields to farming, without a decide."""

import struct
import threading
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache
from robots.app import scripts
from robots.app.scripts import FarmScript
from robots.domain.actions import Attack, MoveTo
from robots.domain.model import ActorRef, Goal
from tests.test_dealer_queue_handover import _received_arrival
from tests.test_dealer_ring import _client
from tests.test_merchant_drive import _plan, _state
from tests.test_native_navigation import SOURCE
from tests.test_sell_drive_rearm import _s00_brain


@pytest.fixture(autouse=True)
def _fresh_arm():
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()


def test_drained_lease_releases_immediately_and_never_retries_after_cooldown(monkeypatch, caplog):
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    stock = _state(inventory={"909": 2, "1201": 1}, zeny=0)
    assert scripts._merchant_step(stock) is not None
    trip = scripts._MERCHANT_TRIPS[stock.name]
    now[0] = trip.no_progress_bound
    assert scripts._merchant_step(stock) is None
    retry_at = trip.retry_at
    drained = replace(
        stock,
        inventory={"909": 0, "915": -1, "1201": 1},
        nearby=(ActorRef(123, "Poring", "monster", 1.0, 171, 300),),
    )
    brain = _s00_brain()
    farm = FarmScript(_plan())
    brain._script = farm
    for at in (now[0] + 1, retry_at, retry_at + 300):
        now[0] = at
        assert any(isinstance(a, Attack) for a in brain.step_script(drained).actions)
        assert stock.name not in scripts._MERCHANT_TRIPS
        assert brain._script is farm
    assert drained.goal == Goal.FARM_ITEM
    assert caplog.text.count("merchant_arm_released_drained") == 1
    assert "merchant_trip_retry (" not in caplog.text
    refilled = replace(drained, inventory=stock.inventory)
    assert not any(isinstance(a, Attack) for a in brain.step_script(refilled).actions)
    assert scripts.merchant_trip_active(refilled.name)
    assert brain._script is farm


@pytest.mark.parametrize("reason", [None, "no_sellables", "completed", "retry_exhausted"])
def test_drained_pump_leaves_dealer_room_and_returns_to_field_without_decides(
    monkeypatch, caplog, reason
):
    client, now = _client(at=(169, 126))
    client.cache = MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    client._zeny_seed = 35
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = client.build_native_state(Goal.GRIND)
    assert scripts._merchant_trip_allows(state, scripts.MERCHANT_ROUTE["prt_in"])
    now[0] += scripts._MERCHANT_TRIPS[state.name].no_progress_bound
    assert not scripts._merchant_trip_allows(state, scripts.MERCHANT_ROUTE["prt_in"])
    retry_at = scripts._MERCHANT_TRIPS[state.name].retry_at
    client._counter_lease.observe(state, now[0])
    client._counter_lease.reason = reason
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    for _ in range(20):
        client.drain_native_events()
        now[0] += 2
        if client.wire.moves:
            point = client.wire.moves[-1]
            client.wire.add(_received_arrival(*point))
            if point == scripts.MERCHANT_ROUTE_RETURN["prt_in"]:
                break
    else:
        pytest.fail(f"drained agent stayed at dealer: {client.wire.moves}")
    assert now[0] < retry_at
    assert state.name not in scripts._MERCHANT_TRIPS
    # Received warps, never invented map/position progress. Continue the
    # same decide-independent pump beyond both former cooldown deadlines.
    client.wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 174, 218))
    now[0] = retry_at + 1
    client.drain_native_events()
    arrived = client.last_built_state
    assert arrived is not None
    assert arrived.map_name == "prontera"
    assert client.wire.moves[-1][1] < 218
    # A later received position reaches the city's field-warp trigger.
    client.wire.add(_received_arrival(156, 24))
    now[0] += 600
    client.drain_native_events()
    client.wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 170, 375))
    client.drain_native_events()
    field = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_drive_cell(field) is None
    assert not scripts.merchant_trip_active(field.name)
    assert field.goal == Goal.GRIND
    brain = _s00_brain()
    brain._script = FarmScript(_plan())
    target = ActorRef(123, "Poring", "monster", 1.0, 171, 375)
    assert any(
        isinstance(a, Attack) for a in brain.step_script(replace(field, nearby=(target,))).actions
    )
    assert "merchant_arm_released_drained" in caplog.text
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)


@pytest.mark.parametrize(
    ("inventory", "zeny", "known"), [({"909": 1}, 0, True), ({}, 80, True), ({}, 0, False)]
)
def test_release_does_not_override_stock_buy_budget_or_unknown_inventory(
    inventory, zeny, known, caplog
):
    state = _state(map_name="prt_in", inventory=inventory, zeny=zeny, inventory_known=known)
    destination = scripts.merchant_drive_cell(state)
    assert (destination is not None) == known
    assert scripts.merchant_return_cell(state) is None
    assert "merchant_arm_released_drained" not in caplog.text


def test_drained_return_bypasses_worn_weapon_hold_but_not_collectible_inflight():
    state = _state(map_name="prontera", inventory={"1201": 1}, zeny=0)
    returning = scripts._merchant_step(state)
    assert returning is not None
    assert returning.actions == (MoveTo(156, 22),)
    inflight = replace(state, merchant_pickup_target=(1, 2), merchant_inflight_visible=2)
    assert scripts.merchant_return_cell(inflight) is None


@pytest.mark.parametrize("barrier", ["poison", "cancel", "passive", "pending", "rest"])
def test_drained_return_keeps_wire_and_movement_barriers(barrier):
    client, now = _client(at=(169, 126))
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    client._zeny_seed = 0
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    if barrier == "poison":
        client._npc._deny("send_failure")
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "pending":
        client._pending = ((170, 126), 100, now[0], 0)
    else:
        client._rest_seq = 1
        client._standing = False
    client.drain_native_events()
    assert client.wire.moves == []
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)
