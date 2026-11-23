"""Leg-120 ring lifecycle, received click range and bag-before-trip regressions."""

import struct
import threading
from dataclasses import replace

import pytest

from robots.app import scripts
from robots.app.merchant_counter_lease import COUNTER_IDLE_SECONDS, COUNTER_REJOIN_SECONDS
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcClose, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_adjacency_rotation import _turn
from tests.test_dealer_queue_handover import _receive_bodies, _received_arrival
from tests.test_dealer_ring import _client, _step
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_merchant_inflight_loot import client_with_loot, stock_state
from tests.test_sell_conversion_recovery import _answer_sale, _blocked_offer
from tests.test_shop_sell_loop import DEALER, _dealer, _inv, _weight


@pytest.fixture(autouse=True)
def fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _quiet(client: PlayingClient) -> None:
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None


def test_stocked_idle_holder_releases_on_pump_then_hands_only_cell_to_fifo_seller(caplog):
    positions = {300: (172, 129), 100: (168, 124)}
    clients = {
        aid: _client(
            str(aid), at=point, aid=aid, blocked=tuple(p for p in NEIGHBOURS if p != (172, 129))
        )
        for aid, point in positions.items()
    }
    for aid, (client, _) in clients.items():
        _quiet(client)
        _receive_bodies(client, aid, positions, set())
        client.build_native_state(Goal.GRIND)
    owner, now = clients[300]
    waiter, _ = clients[100]
    # An authored but undispatched plan cannot own a conversation indefinitely.
    assert _step(owner, owner.build_native_state(Goal.GRIND)) == (TalkToNpc(DEALER),)
    owner.npc_recovery_hold = True
    _answer_sale(waiter)
    now[0] += COUNTER_IDLE_SECONDS - 0.01
    owner.drain_native_events()
    assert (owner._counter_lease.reason,) == (None,)
    assert owner.wire.moves == []
    now[0] += 0.01
    owner.build_native_state(Goal.GRIND)
    assert (owner._counter_lease.reason,) == (None,)  # state construction sends nothing
    owner._keepalive()
    assert owner._counter_lease.reason == "idle"
    assert owner.wire.moves
    assert not any(raw[:2] == b"\x90\x00" for raw in owner.wire.sent)
    assert scripts._DEALER_TALKED.get(owner.wire.char_name) is None
    # Intent to leave is not vacancy: the peer still observes the holder's body.
    waiter.drain_native_events()
    assert not any(raw[:2] == b"\x90\x00" for raw in waiter.wire.sent)
    for elapsed in range(40):
        for aid, (client, clock) in clients.items():
            clock[0] = 106.0 + elapsed
            _turn(client, aid, positions)
        if waiter.build_native_state(Goal.GRIND).zeny == 92:
            break
    assert waiter.build_native_state(Goal.GRIND).zeny == 92, positions
    assert elapsed < 40
    assert owner._counter_lease.reason == "idle"
    assert caplog.text.count("ring_lease_released_idle") == 1
    assert "sell_contact_authored (bot=100 action=TalkToNpc)" in caplog.text


def test_idle_release_requires_received_parking_and_wall_clock_rejoin():
    client, now = _client(at=(172, 129))
    _quiet(client)
    client.npc_recovery_hold = True
    now[0] += COUNTER_IDLE_SECONDS
    client.drain_native_events()
    assert client.cache is not None
    target = client._merchant_staging.yield_target(
        client.cache.get("prt_in"), client.build_native_state(Goal.GRIND)
    )
    assert target is not None
    assert max(abs(target[0] - 172), abs(target[1] - 130)) > 4
    now[0] += 300
    client.drain_native_events()
    assert client._counter_lease.reason == "idle"  # no received exit yet
    client.wire.add(_received_arrival(*target))
    client.drain_native_events()
    for _ in range(20):
        client.drain_native_events()
    assert client._counter_lease.reason == "idle"  # pump count is irrelevant
    now[0] += COUNTER_REJOIN_SECONDS - 0.01
    client.drain_native_events()
    assert client._counter_lease.reason == "idle"
    now[0] += 0.01
    client.drain_native_events()
    assert client._counter_lease.reason is None


@pytest.mark.parametrize("active", ["click", "offer", "sale"])
def test_idle_release_preserves_active_or_outstanding_shop_exchange(active, caplog):
    if active == "offer":
        client, now = _blocked_offer()
    else:
        client, now = _client(at=(172, 129))
        if active == "sale":
            _quiet(client)
            _answer_sale(client)
            send = client.wire._send

            def delayed_result(raw):
                if raw[:2] == b"\xc9\x00":
                    client.wire.sent.append(raw)
                    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
                else:
                    send(raw)

            client.wire._send = delayed_result
            for _ in range(4):
                client.drain_native_events()
            assert client._sell_pending is not None
        else:
            client.perform_native(TalkToNpc(DEALER))
    _quiet(client)
    client.npc_recovery_hold = True
    now[0] += COUNTER_IDLE_SECONDS
    client.drain_native_events()
    assert client._counter_lease.reason is None
    assert client.wire.moves == []
    assert "ring_lease_released_idle" not in caplog.text


@pytest.mark.parametrize("barrier", ["poison", "cancel", "passive", "rest", "pending"])
def test_idle_release_keeps_existing_yield_safety_gates(barrier, caplog):
    client, now = _client(at=(172, 129))
    _quiet(client)
    client.npc_recovery_hold = True
    if barrier == "poison":
        client._npc._deny("send_failure")
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "rest":
        client._standing = False
        client._rest_seq = 1
    else:
        client._pending = ((173, 129), 100, now[0] + COUNTER_IDLE_SECONDS, 0)
    now[0] += COUNTER_IDLE_SECONDS
    client.drain_native_events()
    assert client._counter_lease.reason == "idle"
    assert client.wire.moves == []
    assert not any(isinstance(raw, bytes) and raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    assert caplog.text.count("ring_lease_released_idle") == 1


@pytest.mark.parametrize("distance", [1, 2, 3, 4])
@pytest.mark.parametrize("shift", [0, 1])
def test_contact_authorship_and_dispatch_require_received_dealer_adjacency(distance, shift, caplog):
    # Shift the received dealer within the cited-cell match; never use the hint
    # or ActorRef.distance as the click-range authority.
    dealer = (172 + shift, 130)
    client, _ = _client(at=(dealer[0] - distance, 129))
    _quiet(client)
    client.wire.add(
        _dealer(dealer),
        struct.pack("<HII24s24s", 0xADF, DEALER, 0, b"Weapon Dealer#prt", b""),
    )
    state = client.build_native_state(Goal.GRIND)
    client._start_merchant_sell_on_tick(state)
    authored = "sell_contact_authored" in caplog.text
    assert authored is (distance == 1)
    assert any(raw[:2] == b"\x90\x00" for raw in client.wire.sent) is (distance == 1)
    if distance > 1:
        assert "received_dealer_adjacency" in caplog.text
        assert not scripts.merchant_talk_pending(state.name, DEALER)
        # A retained primitive cannot bypass the same received range gate.
        client.perform_native(TalkToNpc(DEALER))
        assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    else:
        assert max(abs(state.x - dealer[0]), abs(state.y - dealer[1])) == 1


@pytest.mark.parametrize("stock", [0, 1])
def test_unfunded_sell_trip_cannot_create_or_burn_a_retry_lease(stock, monkeypatch):
    client = client_with_loot()
    state = replace(
        stock_state(client),
        inventory={"713": stock, "1201": 1},
        merchant_pickup_target=None,
        merchant_inflight_visible=0,
    )
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    destination = scripts.MERCHANT_ROUTE[state.map_name]
    for now[0] in (0.0, 300.0, 1000.0):
        assert not scripts._merchant_trip_allows(state, destination)
        assert state.name not in scripts._MERCHANT_TRIPS
    bagged = replace(state, inventory={"713": 2, "1201": 1})
    assert scripts._merchant_trip_allows(bagged, destination)
    assert scripts._MERCHANT_TRIPS[state.name].retry_at == 0.0


def test_floor_credit_funds_pickup_without_spending_trip_until_bag_receipt():
    client = client_with_loot(amount=2)
    state = replace(stock_state(client), inventory={"1201": 1})
    destination = scripts.MERCHANT_ROUTE[state.map_name]
    assert scripts.merchant_drive_cell(state) == destination
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions  # credited pickup stays admitted
    assert not scripts._merchant_trip_allows(state, destination)
    assert state.name not in scripts._MERCHANT_TRIPS
    client.wire.add(_inv(((6, 713, 2), (7, 1201, 1))), _weight())
    bagged = replace(client.build_native_state(Goal.FARM_ITEM), zeny=0)
    assert scripts._merchant_trip_allows(bagged, destination)


@pytest.mark.parametrize("stock", [0, 1])
def test_bag_depletion_releases_existing_trip_before_it_can_charge_cooldown(stock, monkeypatch):
    client = client_with_loot()
    state = replace(
        stock_state(client),
        inventory={"713": 2, "1201": 1},
        merchant_pickup_target=None,
        merchant_inflight_visible=0,
    )
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    destination = scripts.MERCHANT_ROUTE[state.map_name]
    assert scripts._merchant_trip_allows(state, destination)
    now[0] = 1000.0
    unfunded = replace(state, inventory={"713": stock, "1201": 1})
    assert not scripts._merchant_trip_allows(unfunded, destination)
    assert state.name not in scripts._MERCHANT_TRIPS
    assert scripts._merchant_trip_allows(state, destination)  # no burned retry


def test_explicitly_closed_dialogue_is_idle_even_with_retained_native_ui(caplog):
    client, now = _client(at=(172, 129))
    _quiet(client)
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(struct.pack("<HI", 0xB6, DEALER))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "close"
    client.perform_native(NpcClose(DEALER))
    closed = client._npc.view
    assert closed is not None
    assert closed.stage == "close_requested"
    assert not client._npc.active
    assert client.wire.moves == []
    client.npc_recovery_hold = True
    now[0] += COUNTER_IDLE_SECONDS
    client.drain_native_events()
    assert client._counter_lease.reason == "idle"
    assert client._npc.view is None
    assert client.wire.moves
    assert caplog.text.count("ring_lease_released_idle") == 1
