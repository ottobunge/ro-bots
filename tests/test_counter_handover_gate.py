"""Leg-115 counter refusals, FIFO contacts and pump-only handover twins."""

import struct
import threading
from dataclasses import replace

import pytest

from robots.app import scripts
from robots.app.merchant_counter_lease import COUNTER_LEASE_SECONDS
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import Say, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_adjacency_rotation import _fleet, _turn
from tests.test_dealer_queue_handover import _receive_bodies, _received_arrival
from tests.test_dealer_ring import _client
from tests.test_sell_conversion_recovery import _answer_sale, _blocked_offer
from tests.test_shop_sell_loop import DEALER, _cb


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _pump_client() -> tuple[PlayingClient, list[float]]:
    client, now = _client(at=(172, 129))
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    return client, now


def _reasons(client: PlayingClient) -> set[str]:
    return {reason for _, reason in client._merchant_contact_gate_reasons}


@pytest.mark.parametrize("budget", [0, 80])
@pytest.mark.parametrize("planner_hold", [False, True])
def test_no_sellables_head_yields_on_first_pump_even_when_drive_refuses(
    budget, planner_hold, caplog
):
    client, _ = _pump_client()
    client._zeny_seed = budget
    client.npc_recovery_hold = planner_hold
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    client.build_native_state(Goal.GRIND)
    assert (client._counter_lease.reason, client.wire.moves) == (None, [])
    client.drain_native_events()
    client.perform_native(Say("social decisions do not own the exit"))
    assert client._counter_lease.reason == "no_sellables"
    assert client.wire.moves
    assert "contact.no_sellables" in _reasons(client)
    assert not any(isinstance(raw, bytes) and raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    assert "sell_contact_hold" in caplog.text


@pytest.mark.parametrize("barrier", ["poison", "cancel", "passive", "pending", "rest"])
def test_empty_head_yield_preserves_wire_safety_and_movement_barriers(barrier):
    client, now = _pump_client()
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    client.npc_recovery_hold = True
    if barrier == "poison":
        client._npc._deny("send_failure")
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "pending":
        client._pending = ((173, 129), 100, now[0], 0)
    else:
        client._rest_seq = 1
        client._standing = False
    client.drain_native_events()
    assert client.wire.moves == []
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)


def test_existing_contact_latch_names_its_hold_without_a_second_click(caplog):
    client, _ = _pump_client()
    state = client.build_native_state(Goal.GRIND)
    outcome = scripts._merchant_step(
        state, reachable=client.merchant_reachable, travel_target=client.merchant_travel_target
    )
    assert outcome is not None
    assert outcome.actions == (TalkToNpc(DEALER),)
    # Authoring consumed the latch; no primitive has been dispatched yet.
    client.drain_native_events()
    assert "contact.contact_latched" in _reasons(client)
    assert "contact_latched" in caplog.text
    assert client.wire.sent == []


def test_inventory_deletion_before_sale_result_does_not_turn_inflight_sale_into_empty_refusal():
    client, now = _pump_client()
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
        now[0] += 0.1
    assert "909" not in client.build_native_state(Goal.GRIND).inventory
    assert client._sell_pending is not None
    assert client._counter_lease.reason is None
    assert client.wire.moves == []
    client.wire.add(_cb(0))
    client.drain_native_events()
    assert client._counter_lease.reason == "completed"


def test_buy_list_head_without_sellables_closes_and_yields_before_lease_deadline():
    client, now = _blocked_offer()
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    now[0] += 2
    client.drain_native_events()
    assert now[0] - 100 < COUNTER_LEASE_SECONDS
    assert client._counter_lease.reason == "no_sellables"
    assert client._npc.view is None
    assert client._shop_context.offer is None
    assert struct.pack("<HI", 0x146, DEALER) in client.wire.sent
    assert client.wire.moves


def test_planner_hold_cannot_extend_the_physical_counter_deadline():
    client, now = _blocked_offer()
    client.npc_recovery_hold = True
    now[0] += COUNTER_LEASE_SECONDS
    client.drain_native_events()
    assert client._counter_lease.reason == "expired"
    assert client._npc.view is None
    assert client.wire.moves


def test_no_sellables_head_parks_and_next_fifo_seller_converts_without_decides(caplog):
    clients, positions = _fleet()
    buyer, _ = clients[300]
    buyer._zeny_seed = 80
    buyer.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    seller, _ = clients[100]
    _answer_sale(seller)
    for tick in range(85):
        for aid, (client, now) in clients.items():
            now[0] = 102.0 + tick * 2
            _turn(client, aid, positions)
        if seller.build_native_state(Goal.GRIND).zeny == 92:
            break
    assert seller.build_native_state(Goal.GRIND).zeny == 92, positions
    assert tick * 2 < COUNTER_LEASE_SECONDS
    assert buyer._counter_lease.reason == "no_sellables"
    assert max(abs(positions[300][0] - 172), abs(positions[300][1] - 130)) > 4
    assert "sell_contact_authored (bot=100 action=TalkToNpc)" in caplog.text


def test_adjacent_sellable_head_authors_exactly_one_contact_on_pump(caplog):
    client, now = _pump_client()
    for _ in range(4):
        client.drain_native_events()
        now[0] += 0.1
    assert client.wire.sent == [struct.pack("<HIB", 0x90, DEALER, 1)]
    assert "sell_contact_authored (bot=seller action=TalkToNpc)" in caplog.text


def test_adjacent_sellable_nonhead_cannot_author_or_dispatch_talk(caplog):
    client, _ = _client(at=(168, 124))
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    _receive_bodies(client, 999, {100: (171, 128)}, set())
    client.build_native_state(Goal.GRIND)
    client.wire.add(_received_arrival(172, 129))
    client.drain_native_events()
    assert not client._counter_lease.queue.admits(999)
    client.perform_native(TalkToNpc(DEALER))
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    assert "sell_contact_authored" not in caplog.text
    assert any("counter_turn" in reason for reason in _reasons(client))


def test_fresh_native_epoch_releases_old_one_contact_latch(caplog):
    client, now = _pump_client()
    client.drain_native_events()
    client.wire.native_epoch = client.wire.selection_epoch = client.wire.map_epoch = 2
    client.wire.add(struct.pack("<HII24s24s", 0xADF, DEALER, 0, b"Weapon Dealer#prt", b""))
    now[0] += 1
    client.drain_native_events()
    assert sum(raw[:2] == b"\x90\x00" for raw in client.wire.sent) == 2
    assert caplog.text.count("sell_contact_authored (bot=seller action=TalkToNpc)") == 2


@pytest.mark.parametrize(
    ("barrier", "reason"),
    [
        ("passive", "approach.mechanical_disabled"),
        ("hp", "approach.hp_not_safe"),
        ("cache", "approach.no_map_cache"),
        ("pose", "approach.not_standing"),
        ("stand", "approach.stand_pending"),
        ("rest", "approach.resting"),
        ("poison", "approach.npc_failed"),
        ("cancel", "approach.actuation_blocked"),
        ("lease", "approach.counter_released:expired"),
        ("planner", "contact.planner_hold"),
        ("dealer", "contact.dealer_not_adjacent"),
        ("pending", "motion.pending_walk"),
    ],
)
def test_real_contact_gate_barriers_name_the_refusal(barrier, reason, caplog):
    client, now = _pump_client()
    if barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "hp":
        client.wire.status_params[5] = 1
    elif barrier == "cache":
        client.cache = None
    elif barrier == "pose":
        client._standing = False
    elif barrier == "stand":
        client._stand_pending = (1, now[0], now[0], 0)
    elif barrier == "rest":
        client._rest_seq = 1
    elif barrier == "poison":
        client._npc._deny("malformed")
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "lease":
        now[0] += 181
        client.npc_recovery_hold = True  # retain expiry long enough to observe it
    elif barrier == "planner":
        client.npc_recovery_hold = True
    elif barrier == "dealer":
        client._npc_names[DEALER] = "Quest Guide"
    elif barrier == "pending":
        client._pending = ((173, 129), 100, now[0], 0)
    client.drain_native_events()
    assert reason in _reasons(client)
    assert reason.split(".", 1)[1] in caplog.text
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)


def test_simultaneous_refusals_are_all_named_and_steady_hold_logging_is_bounded(caplog):
    client, _ = _pump_client()
    client.mechanical_recovery_allowed = False
    client._rest_seq = 1
    client.npc_recovery_hold = True
    client._npc.cancel_uncertain = True
    for _ in range(20):
        client.drain_native_events()
    assert _reasons(client) >= {
        "approach.mechanical_disabled",
        "approach.resting",
        "approach.actuation_blocked",
        "shop_recovery.mechanical_disabled",
        "shop_recovery.planner_hold",
        "shop_recovery.cancel_uncertain",
    }
    assert caplog.text.count("sell_contact_hold") == 2
    assert len(client._merchant_contact_gate_reasons) <= 64


def test_shop_recovery_gate_names_every_safety_refusal(caplog):
    client, _ = _blocked_offer()
    client.mechanical_recovery_allowed = False
    client.npc_recovery_hold = True
    client._npc.cancel_uncertain = True
    client._npc._deny("malformed")
    client._npc_names[DEALER] = "Quest Guide"
    state = client.build_native_state(Goal.GRIND)
    assert not client._shop_recovery_safe(state)
    assert _reasons(client) >= {
        "shop_recovery.mechanical_disabled",
        "shop_recovery.planner_hold",
        "shop_recovery.cancel_uncertain",
        "shop_recovery.npc_poisoned",
        "shop_recovery.dialogue_not_dealer",
    }
    assert "sell_contact_hold" in caplog.text


def test_remaining_approach_conjuncts_are_observable_from_received_state():
    client, _ = _pump_client()
    state = client.build_native_state(Goal.GRIND)
    state = replace(
        state, alive=False, merchant_pickup_target=(172, 129), merchant_inflight_pending=2
    )
    state = replace(state, inventory={})
    client._tracker = None
    assert not client._merchant_approach_ready(state)
    assert _reasons(client) >= {
        "approach.no_tracker",
        "approach.not_alive",
        "approach.pickup_required",
    }
