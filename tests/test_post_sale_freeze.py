"""Leg-77 freezes replayed with synthetic wire receipts, without a world."""

import struct
import threading
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, NpcClose, NpcShopSell, NpcShopSellOpen
from robots.domain.model import Goal
from tests.test_dealer_approach_cell import _crowd, _dealer, _state
from tests.test_npc_retry import _deny, _runtime
from tests.test_playing_runtime import Wire
from tests.test_sell_drive_rearm import _s00_brain
from tests.test_shop_sell_loop import DEALER, _c4, _c7, _cb, _client_with, _inv, _weight
from tests.test_shop_sell_loop import _dealer as wire_dealer


def _sale_client() -> PlayingClient:
    client = _client_with(wire_dealer((43, 37)), _inv(((6, 909, 1),)), _weight())
    client.cache = MapCache((WalkMap("prt_in", 100, 100, bytes(10000)),))
    client.wire.map_name = "prt_in.gat"
    client.wire.add(struct.pack("<H16sHH", 0x91, b"prt_in.gat", 42, 37))
    client.wire.add(wire_dealer((43, 37)), _inv(((6, 909, 1),)), _weight())
    state = client.build_native_state(Goal.SOCIAL)
    client._npc.begin(DEALER, 1, state.map_name, client._metadata_cursor, client._now())
    client.wire.add(_c4(DEALER), _c7(((6, 12, 12),)))
    state = client.build_native_state(Goal.SOCIAL)
    (action,) = client.mechanical_actions(state, ())
    assert isinstance(action, NpcShopSell)
    assert action.map_name == "prt_in.gat"
    client.perform_native(action)
    return client


@pytest.mark.parametrize("expired", [False, True])
def test_live_map_spelling_sale_receipt_releases_dialogue_and_social_return(expired):
    client = _sale_client()
    if expired:
        client._npc._expire(client._now() + 30)
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight(), _cb(0))
    state = client.build_native_state(Goal.SOCIAL)
    assert state.npc_dialogue is None
    assert not client._npc.actuation_blocked
    brain = _s00_brain()
    brain.start(state)
    assert brain.step_script(state).actions == (MoveTo(168, 124),)
    assert sum(f[:2] == b"\xc9\x00" for f in client.wire.sent) == 1
    assert not any(isinstance(a, NpcShopSell) for a in client.mechanical_actions(state, ()))


@pytest.mark.parametrize("path", ["dispatch", "tick"])
def test_timeout_budget_rearms_after_five_minutes_without_burst(path):
    now = [300.0]
    client = _runtime(now)
    for attempt in range(3):
        _deny(client)
        now[0] = 300.0 + attempt * 20
        if path == "dispatch":
            assert client._retry_blocked_dialogue()
        else:
            client._retry_blocked_dialogue_on_tick(now[0])
    assert len(client.wire.sent) == 3
    _deny(client)
    now[0] = 599.9
    client._retry_blocked_dialogue_on_tick(now[0])
    assert len(client.wire.sent) == 3
    now[0] = 600.0
    if path == "dispatch":
        assert client._retry_blocked_dialogue()
    else:
        client._retry_blocked_dialogue_on_tick(now[0])
    assert len(client.wire.sent) == 4
    client._npc._expire(610.0)
    now[0] = 601.0
    client._retry_blocked_dialogue_on_tick(now[0])
    assert len(client.wire.sent) == 4


def _blocked_client(*, admitted: bool = False) -> tuple[PlayingClient, list[float]]:
    now = [100.0]
    client = _client_with(wire_dealer((43, 37)), _inv(((6, 909, 1),)), _weight())
    client._now = lambda: now[0]
    client.cache = MapCache((WalkMap("prt_in", 200, 200, bytes(40000)),))
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 10000.0
    client._zeny_seed = 80 if admitted else 0
    client.wire.map_name = "prt_in"
    client.wire.add(
        struct.pack("<H16sHH", 0x91, b"prt_in", 173, 129),
        wire_dealer((172, 130)),
    )
    client.build_native_state(Goal.GRIND)
    client._npc_names[DEALER] = "Weapon Dealer#prt"
    client._npc.begin(DEALER, 1, "prt_in", client._metadata_cursor, now[0])
    now[0] = 130.0
    client.build_native_state(Goal.GRIND)
    client._npc_retries = 0
    return client, now


def test_authored_timeout_close_reaches_wire_before_retry_and_releases():
    client, _now = _blocked_client()
    client.perform_native(NpcClose(DEALER))
    assert client.wire.sent == [struct.pack("<HI", 0x146, DEALER)]
    assert not client._npc.actuation_blocked
    client.perform_native(MoveTo(173, 128))
    assert client.wire.moves


@pytest.mark.parametrize("goal", [Goal.GRIND, Goal.FARM_ITEM, Goal.SOCIAL])
def test_refused_trade_timeout_releases_on_pump_even_without_authored_close(goal):
    client, _now = _blocked_client()
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight())
    client.drain_native_events()
    state = client.build_native_state(goal)
    assert client.wire.sent == [struct.pack("<HI", 0x146, DEALER)]
    assert state.npc_dialogue is None
    brain = _s00_brain()
    brain.start(state)
    assert brain.step_script(state).actions == (MoveTo(168, 124),)
    client.drain_native_events()
    assert len(client.wire.sent) == 1


@pytest.mark.parametrize("origin", ["poison", "send_failure"])
def test_poison_cannot_age_into_timeout_or_release_on_either_path(origin):
    client, now = _blocked_client()
    client._npc._deny(origin)
    now[0] = 3600.0
    client.build_native_state(Goal.GRIND)
    assert client._npc.deny_origin == origin
    client.perform_native(NpcClose(DEALER))
    client._retry_blocked_dialogue_on_tick(now[0])
    client.drain_native_events()
    assert client._npc.failed
    assert client.wire.sent == []


def test_failed_timeout_close_poison_survives_later_pumps(monkeypatch):
    client, now = _blocked_client()
    error = OSError("offline close failure")

    def fail(raw):
        raise error

    monkeypatch.setattr(client.wire, "_send", fail)
    with pytest.raises(OSError, match="offline close failure") as caught:
        client.perform_native(NpcClose(DEALER))
    assert caught.value is error
    monkeypatch.setattr(client.wire, "_send", client.wire.sent.append)
    now[0] = 3600.0
    client.build_native_state(Goal.GRIND)
    client.perform_native(NpcClose(DEALER))
    assert client._npc.deny_origin != "timeout"
    assert client._npc.actuation_blocked
    assert client.wire.sent == []


def test_released_seller_vacates_ring_and_queued_seller_reaches_talk():
    scripts.reset_merchant_talk()
    try:
        queued = _state(nearby=(_dealer(), *_crowd()))
        hold = scripts._merchant_step(queued)
        assert hold is not None
        assert hold.actions == ()
        client, _now = _blocked_client()
        client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight())
        client.drain_native_events()
        home = scripts.merchant_return_cell(client.build_native_state(Goal.SOCIAL))
        assert home == (168, 124)
        # Only a received vacancy admits the queue advance, never local release alone.
        hold = scripts._merchant_step(queued)
        assert hold is not None
        assert hold.actions == ()
        vacancy = replace(queued, nearby=(_dealer(), *_crowd(except_cell=(173, 129))))
        advance = scripts._merchant_step(vacancy)
        assert advance is not None
        assert advance.actions == (MoveTo(173, 129),)
        arrived = replace(vacancy, x=173, y=129)
        talk = scripts._merchant_step(arrived)
        assert talk is not None
        assert type(talk.actions[0]).__name__ == "TalkToNpc"
        # Complete that queued seller's actual click/C4/C5/C7/C9/CB path
        # from the newly received arrival, rather than equating Talk with a sale.
        queued_client = _client_with()
        queued_client.cache = MapCache((WalkMap("prt_in", 200, 200, bytes(40000)),))
        queued_client.wire.map_name = "prt_in.gat"
        queued_client.wire.add(
            struct.pack("<H16sHH", 0x91, b"prt_in.gat", arrived.x, arrived.y),
            wire_dealer((172, 130), 110001762),
            _inv(((6, 909, 1),)),
            _weight(),
        )
        queued_client.perform_native(talk.actions[0])
        queued_client.wire.add(_c4(110001762))
        state = queued_client.build_native_state(Goal.FARM_ITEM)
        (open_sell,) = queued_client.mechanical_actions(state, ())
        assert isinstance(open_sell, NpcShopSellOpen)
        queued_client.perform_native(open_sell)
        queued_client.wire.add(_c7(((6, 12, 12),)))
        state = queued_client.build_native_state(Goal.FARM_ITEM)
        (sale,) = queued_client.mechanical_actions(state, ())
        assert isinstance(sale, NpcShopSell)
        queued_client.perform_native(sale)
        queued_client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight(), _cb(0))
        state = queued_client.build_native_state(Goal.FARM_ITEM)
        assert state.npc_dialogue is None
        assert not queued_client._npc.actuation_blocked
        assert sum(f[:2] == b"\xc9\x00" for f in queued_client.wire.sent) == 1
    finally:
        scripts.reset_merchant_talk()


def test_no_dialogue_self_death_gets_paced_respawn_but_no_optimistic_life():
    now = [100.0]
    wire = Wire()
    client = PlayingClient(
        wire,
        cache=MapCache((WalkMap("prontera", 100, 100, bytes(10000)),)),
        monotonic=lambda: now[0],
    )
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 10000.0
    wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    client.drain_native_events()
    assert client._npc.view is None
    assert client._standing is None
    assert wire.sent == [struct.pack("<HB", 0xB2, 0)]
    assert client.build_native_state(Goal.GRIND).alive is False
    for _ in range(20):
        client.drain_native_events()
    assert len(wire.sent) == 1
    now[0] += 30
    client.drain_native_events()
    assert sum(f[:2] == b"\xb2\x00" for f in wire.sent) == 2
    wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37))
    assert client.build_native_state(Goal.GRIND).alive is True
    client.perform_native(MoveTo(43, 37))
    assert wire.sent[-1] == "stand"
    assert not wire.moves
    pose = bytearray(34)
    struct.pack_into("<HI", pose, 0, 0x08C8, wire.aid)
    pose[29] = 3
    wire.add(bytes(pose))
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]


@pytest.mark.parametrize("shape", ["alive", "unknown", "peer_death", "poison"])
def test_respawn_cannot_be_authorized_by_hp_or_another_body(shape):
    wire = Wire()
    client = PlayingClient(wire, monotonic=lambda: 100.0)
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 10000.0
    if shape == "unknown":
        wire.frames = []
        wire.add(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37))
    elif shape == "peer_death":
        wire.add(struct.pack("<HIB", 0x80, 123, 1))
    elif shape == "poison":
        client.build_native_state(Goal.GRIND)
        client._npc.begin(321, 1, "prontera", client._metadata_cursor, 100.0)
        client._npc._deny("poison")
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    client.drain_native_events()
    assert not wire.sent


@pytest.mark.parametrize("shape", ["offer", "cancel", "dead", "sitting", "walk", "foreign"])
def test_timeout_close_keeps_every_other_barrier(shape, monkeypatch):
    client, _now = _blocked_client()
    state = client.build_native_state(Goal.GRIND)
    action = NpcClose(DEALER)
    if shape == "offer":
        monkeypatch.setattr(client._shop_context, "offer", object())
    elif shape == "cancel":
        client._npc.cancel_uncertain = True
    elif shape == "dead":
        state = replace(state, alive=False)
    elif shape == "sitting":
        client._standing = False
    elif shape == "walk":
        client._pending = ((173, 128), 1, 100.0, 0)
    else:
        action = NpcClose(DEALER + 1)
    assert not client._close_timeout_dialogue(state, action)
    assert client._npc.actuation_blocked
    assert client.wire.sent == []


@pytest.mark.parametrize("shape", ["admitted", "planner", "other_npc", "unseen_dealer"])
def test_pump_only_closes_the_refused_received_dealer(shape):
    client, _now = _blocked_client()
    if shape != "admitted":
        client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight())
    if shape == "planner":
        client.npc_recovery_hold = True
    elif shape == "other_npc":
        client._npc_names[DEALER] = "Quest Guide"
    elif shape == "unseen_dealer":
        client.wire.add(struct.pack("<HIB", 0x80, DEALER, 0))
    client.drain_native_events()
    assert client.wire.sent == []
    assert client._npc.failed


def test_sale_release_does_not_veto_new_admitted_stock_and_expires_on_field():
    client = _sale_client()
    # CB does not claim the bag is empty. Without an inventory deletion, its
    # received stock still owns admission even after the UI has completed.
    client.wire.add(_cb(0))
    state = client.build_native_state(Goal.SOCIAL)
    assert not client._npc.actuation_blocked
    assert state.merchant_returning
    assert scripts.merchant_admission_refusal(state) is None
    assert scripts.merchant_return_cell(state) is None
    assert client._merchant_departure("prt_fild08") is False
    assert client._merchant_departure("prt_in") is False


def test_dead_respawn_send_failure_is_permanent_until_session_replacement(monkeypatch):
    now = [100.0]
    wire = Wire()
    client = PlayingClient(wire, monotonic=lambda: now[0])
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 10000.0
    wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    error = OSError("offline respawn failure")

    def fail(raw):
        raise error

    monkeypatch.setattr(wire, "_send", fail)
    with pytest.raises(OSError, match="offline respawn failure") as caught:
        client.drain_native_events()
    assert caught.value is error
    monkeypatch.setattr(wire, "_send", wire.sent.append)
    now[0] = 1000.0
    client.drain_native_events()
    assert client._npc.failed
    assert client._npc.deny_origin == "send_failure"
    assert wire.sent == []
