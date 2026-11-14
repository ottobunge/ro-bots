"""Leg-102 final-cell and bounded counter ownership, entirely offline."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache
from robots.app import scripts
from robots.domain.actions import MoveTo, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_queue_handover import _receive_bodies, _received_arrival
from tests.test_dealer_ring import _client, _step
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_native_navigation import SOURCE
from tests.test_shop_sell_loop import DEALER, _c4, _dealer, _inv


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


@pytest.mark.parametrize("buy", [False, True])
def test_last_cell_goes_to_nearest_received_waiter_instead_of_distant_low_aid(buy):
    client, _ = _client(
        at=(173, 128), aid=200, blocked=tuple(p for p in NEIGHBOURS if p != (173, 129))
    )
    # The low-ID body can reach the counter via (172,128), but has not walked it.
    body = bytearray(_dealer((170, 128), npc_id=100))
    body[4] = 0
    client.wire.add(bytes(body))
    state = client.build_native_state(Goal.GRIND)
    if buy:
        state = replace(state, inventory={}, inventory_known=True, zeny=100)
    assert _step(client, state) == (MoveTo(173, 129),)
    assert client._move(state, (173, 129)) == "dispatched"
    assert client.wire.moves[-1] == (173, 129)


@pytest.mark.parametrize("buy", [False, True])
def test_free_alternate_and_received_vacancy_both_close_the_last_cell(buy):
    client, _ = _client(at=(172, 128))
    client.cache = MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")
    state = client.build_native_state(Goal.GRIND)
    if buy:
        state = replace(state, inventory={}, inventory_known=True, zeny=100)
    occupied = replace(state, occupied_cells=((172, 129),))
    assert _step(client, occupied) == (MoveTo(173, 129),)
    # A full ring must not prevent immediate reallocation when perception changes.
    _step(client, replace(state, occupied_cells=NEIGHBOURS))
    assert _step(client, state) == (MoveTo(172, 129),)


@pytest.mark.parametrize("buy", [False, True])
@pytest.mark.parametrize("retained_plan", [False, True])
def test_stalled_dialogue_yields_counter_and_received_waiter_enters(buy, retained_plan):
    owner, clock = _client(
        "owner", at=(172, 129), aid=100, blocked=tuple(p for p in NEIGHBOURS if p != (172, 129))
    )
    waiter, waiter_clock = _client(
        "waiter", at=(172, 128), aid=200, blocked=tuple(p for p in NEIGHBOURS if p != (172, 129))
    )
    if buy:
        owner.wire.add(_inv(()))
        owner._zeny_seed = 100
        waiter.wire.add(_inv(()))
        waiter._zeny_seed = 100
    state = owner.build_native_state(Goal.GRIND)
    owner.perform_native(TalkToNpc(DEALER))
    owner.wire.add(_c4(DEALER))
    state = owner.build_native_state(Goal.GRIND)
    # No result arrives: a shop contact cannot own the ring for the window.
    clock[0] += 181
    state = owner.build_native_state(Goal.GRIND)
    seam = owner.shop_actions if retained_plan else owner.mechanical_actions
    actions = seam(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert max(abs(actions[0].x - 172), abs(actions[0].y - 130)) >= 2
    assert owner._npc.view is None
    assert any(frame[:2] == b"\x46\x01" for frame in owner.wire.sent)
    positions = {100: (172, 129), 200: (172, 128)}
    handed = False
    # Independent clients, only received bodies and walk acknowledgements cross.
    for tick in range(120):
        for aid, client, now in ((100, owner, clock), (200, waiter, waiter_clock)):
            now[0] = 282.0 + tick * 2
            client.wire.add(_received_arrival(*positions[aid]))
            _receive_bodies(client, aid, positions, set())
            state = client.build_native_state(Goal.GRIND)
            if aid == 200 and max(abs(state.x - 172), abs(state.y - 130)) <= 1:
                handed = True
                break
            actions = client.shop_actions(state, ())
            if actions is None:
                actions = _step(client, state)
            for action in actions:
                if isinstance(action, MoveTo):
                    before = len(client.wire.moves)
                    client._move(state, (action.x, action.y))
                    if len(client.wire.moves) > before:
                        positions[aid] = client.wire.moves[-1]
        if handed:
            break
    assert handed, positions


def test_completed_dialogue_yields_even_when_next_buy_is_still_admitted():
    client, _ = _client(at=(172, 129))
    state = client.build_native_state(Goal.GRIND)
    assert _step(client, state) == (TalkToNpc(DEALER),)
    client.perform_native(TalkToNpc(DEALER))
    client.build_native_state(Goal.GRIND)
    client._npc.complete_shop()  # existing result-bound completion seam
    state = replace(client.build_native_state(Goal.GRIND), inventory={}, zeny=100)
    assert scripts.merchant_admission_refusal(state) is None
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert max(abs(actions[0].x - 172), abs(actions[0].y - 130)) >= 2
    # A completed contact must release its script latch even with no UI left.
    assert scripts._merchant_engage(state, (172, 130)).actions == (TalkToNpc(DEALER),)


def test_completed_sale_releases_the_counter_without_waiting_for_lease_deadline():
    client, _ = _client(at=(172, 129))
    client.build_native_state(Goal.GRIND)
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    client._merchant_returning = True
    state = client.build_native_state(Goal.GRIND)
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)


def test_bound_buy_offer_cannot_bypass_counter_expiry():
    client, now = _client(at=(172, 129))
    client.wire.add(_inv(()))
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(_c4(DEALER))
    client.build_native_state(Goal.GRIND)
    selection = client.npc_shop_buy_selection()
    assert selection is not None
    client.perform_native(selection)
    client.wire.add(struct.pack("<HHIIBH", 0xC6, 15, 50, 50, 4, 1201))
    sequence, _, pid, raw = client.wire.frames[-1]
    client.wire.frames[-1] = (sequence, now[0], pid, raw)
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    now[0] += 179
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    # Expiry is based on physical occupancy, not offer progress or script recreation.
    now[0] += 1
    state = client.build_native_state(Goal.GRIND)
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert client._npc.view is None
    assert client._shop_context.offer is None
    assert not any(raw[:2] == b"\xc8\x00" for raw in client.wire.sent)


@pytest.mark.parametrize("barrier", ["cancel_uncertain", "poison", "send_failure"])
def test_counter_expiry_preserves_uncertain_dialogue_barriers(barrier):
    client, now = _client(at=(172, 129))
    client.perform_native(TalkToNpc(DEALER))
    now[0] += 181
    state = client.build_native_state(Goal.GRIND)
    if barrier == "cancel_uncertain":
        client._npc.cancel_uncertain = True
    else:
        client._npc.failed = True
        client._npc.deny_origin = barrier
    sent = tuple(client.wire.sent)
    assert client.shop_actions(state, ()) == ()
    assert tuple(client.wire.sent) == sent
    assert client._npc.view is not None


def test_expired_holder_rejoins_only_after_received_off_lane_parking_and_cooldown():
    client, now = _client(at=(172, 129))
    now[0] += 181
    state = client.build_native_state(Goal.GRIND)
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    target = (actions[0].x, actions[0].y)
    assert max(abs(target[0] - 172), abs(target[1] - 130)) > 4
    now[0] += 300
    # Elapsed time alone cannot release the lease before the body actually leaves.
    assert client.shop_actions(client.build_native_state(Goal.GRIND), ()) == actions
    client.wire.add(_received_arrival(*target))
    state = client.build_native_state(Goal.GRIND)
    assert client.shop_actions(state, ()) == ()
    now[0] += 29
    assert client.shop_actions(client.build_native_state(Goal.GRIND), ()) == ()
    now[0] += 1
    assert client.shop_actions(client.build_native_state(Goal.GRIND), ()) is None


def test_new_received_epoch_does_not_inherit_expired_counter_lease():
    client, now = _client(at=(172, 129))
    now[0] += 181
    state = client.build_native_state(Goal.GRIND)
    assert client.shop_actions(state, ())
    assert state.native_epoch is not None
    changed = replace(state, native_epoch=state.native_epoch + 1)
    assert client.shop_actions(changed, ()) is None


def test_expired_unanswered_click_releases_deferred_talk_latch():
    client, now = _client(at=(172, 129))
    state = client.build_native_state(Goal.GRIND)
    assert _step(client, state) == (TalkToNpc(DEALER),)
    client._rest_seq = 1
    client._talk_npc(state, DEALER)
    assert client._npc.view is None
    deferred = client._retry_talk
    assert deferred == DEALER
    now[0] += 181
    state = client.build_native_state(Goal.GRIND)
    assert client.shop_actions(state, ())
    assert client._retry_talk is None
    assert scripts._merchant_engage(state, (172, 130)).actions == (TalkToNpc(DEALER),)
