"""Leg-112: received shop completion and counter release with no decisions."""

import struct
import threading

import pytest

from robots.app import scripts
from robots.app.playing_runtime import NPC_RETRY_BUDGET, PlayingClient
from robots.domain.actions import NpcShopBuySelection, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_ring import _client
from tests.test_shop_sell_loop import DEALER, _c4, _c7, _cb, _inv


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _blocked_offer(name: str = "seller") -> tuple[PlayingClient, list[float]]:
    client, now = _client(name, at=(172, 129))
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 1.0
    client.wire.keepalive = lambda: None
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    client._zeny_seed = 80
    state = client.build_native_state(Goal.GRIND)
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    (selection,) = client.mechanical_actions(state, ())
    assert isinstance(selection, NpcShopBuySelection)
    client.perform_native(selection)
    client.wire.add(struct.pack("<HHIIBH", 0xC6, 15, 1250, 1250, 4, 1204))
    seq, _, pid, raw = client.wire.frames[-1]
    client.wire.frames[-1] = (seq, now[0], pid, raw)
    client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None
    client.wire.add(_inv(((6, 909, 1), (7, 1201, 1))))
    now[0] += 30
    client.build_native_state(Goal.GRIND)
    assert client._npc.view is not None
    assert client._npc.view.stage == "blocked"
    assert client._npc.deny_origin == "timeout"
    return client, now


def _pump(client: PlayingClient, now: list[float]) -> None:
    now[0] += 2
    client.drain_native_events()


def _answer_sale(client: PlayingClient, *, respond: bool = True) -> None:
    """Only primitive send is replaced; responses enter the real frame tracker."""

    def send(raw: bytes) -> None:
        client.wire.sent.append(raw)
        if not respond:
            return
        pid = int.from_bytes(raw[:2], "little")
        if pid == 0x90:
            client.wire.add(_c4(DEALER))
        elif pid == 0xC5:
            assert raw == struct.pack("<HIB", 0xC5, DEALER, 1)
            client.wire.add(_c7(((6, 12, 12),)))
        elif pid == 0xC9:
            client.wire.add(
                struct.pack("<HHH", 0xAF, 6, 1),
                struct.pack("<HHi", 0xB0, 20, 92),
                _cb(0),
            )

    client.wire._send = send


def test_bound_offer_timeout_completes_sell_on_pump_without_decides():
    client, now = _blocked_offer()
    client._npc_retries = 1
    before = len(client.wire.sent)
    _answer_sale(client)
    for _ in range(4):
        _pump(client, now)
    frames = [f for f in client.wire.sent[before:] if f[:2] != b"\x98\x09"]
    assert [int.from_bytes(f[:2], "little") for f in frames] == [0x146, 0x90, 0xC5, 0xC9]
    state = client.build_native_state(Goal.GRIND)
    assert state.zeny == 92
    assert "909" not in state.inventory
    assert client._npc.view is None
    assert not client._npc.actuation_blocked
    assert client._npc_retries == NPC_RETRY_BUDGET


def test_unanswered_sell_retries_release_and_yield_when_budget_exhausted():
    client, now = _blocked_offer()
    before = len(client.wire.sent)
    _answer_sale(client, respond=False)
    for _ in range(30):
        _pump(client, now)
    frames = [f for f in client.wire.sent[before:] if f[:2] != b"\x98\x09"]
    assert sum(f[:2] == b"\x90\x00" for f in frames) == NPC_RETRY_BUDGET
    assert frames[-1] == struct.pack("<HI", 0x146, DEALER)
    assert client._npc_retries == 0
    assert client._npc.view is None
    assert client._shop_context.offer is None
    assert not client._npc.actuation_blocked
    assert client.wire.moves, "release must drive the existing runtime counter-yield path"
    assert client.build_native_state(Goal.GRIND).zeny == 80


@pytest.mark.parametrize("barrier", ["poison", "send_failure", "cancel"])
def test_bound_timeout_recovery_preserves_nonretryable_barriers(barrier):
    client, now = _blocked_offer()
    if barrier == "cancel":
        client._npc.cancel_uncertain = True
    else:
        client._npc._deny(barrier)
    before = len(client.wire.sent)
    now[0] += 600
    for _ in range(4):
        _pump(client, now)
    assert client.wire.sent[before:] == []
    assert client.wire.moves == []
    assert client._npc.actuation_blocked


def test_blocked_buyer_yields_counter_on_pump_without_decides():
    client, now = _blocked_offer()
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    now[0] = 281
    _pump(client, now)
    assert client._npc.view is None
    assert client._shop_context.offer is None
    assert struct.pack("<HI", 0x146, DEALER) in client.wire.sent
    assert client.wire.moves


def test_other_npc_keeps_generic_timeout_retry_without_sell_redrive():
    client, _now = _blocked_offer()
    client._shop_context.invalidate_offer("synthetic non-shop dialogue")
    client._npc_names[DEALER] = "Quest Guide"
    client.build_native_state(Goal.GRIND)
    before = len(client.wire.sent)
    assert client._retry_blocked_dialogue()
    assert client.wire.sent[before:] == [struct.pack("<HIB", 0x90, DEALER, 1)]
    assert not client._npc.failed


@pytest.mark.parametrize("hold", ["planner", "passive"])
def test_sell_recovery_preserves_planner_and_passive_boundaries(hold):
    client, now = _blocked_offer()
    if hold == "planner":
        client.npc_recovery_hold = True
    else:
        client.mechanical_recovery_allowed = False
    before = len(client.wire.sent)
    _pump(client, now)
    assert client._retry_blocked_dialogue()
    assert client.wire.sent[before:] == []
    assert client._shop_context.offer is not None
    assert client._npc.deny_origin == "timeout"


def test_twenty_nine_clients_complete_recovered_sales_without_shared_budget():
    for agent in range(29):
        client, now = _blocked_offer(str(agent))
        _answer_sale(client)
        for _ in range(4):
            _pump(client, now)
        assert client.build_native_state(Goal.GRIND).zeny == 92, agent
        assert sum(f[:2] == b"\xc9\x00" for f in client.wire.sent) == 1


@pytest.mark.parametrize("failed_packet", [0x146, 0x90, 0xC5, 0xC9])
def test_recovery_send_failure_keeps_poison_and_never_walks(failed_packet):
    client, now = _blocked_offer()
    _answer_sale(client)
    send = client.wire._send
    error = OSError("synthetic recovery send failure")

    def fail(raw):
        if int.from_bytes(raw[:2], "little") == failed_packet:
            raise error
        send(raw)

    client.wire._send = fail
    for _ in range({0x146: 0, 0x90: 0, 0xC5: 1, 0xC9: 2}[failed_packet]):
        _pump(client, now)
    with pytest.raises(OSError, match="synthetic recovery send failure") as caught:
        _pump(client, now)
    assert caught.value is error
    before = len(client.wire.sent)
    now[0] += 600
    _pump(client, now)
    assert client._npc.deny_origin == "send_failure"
    assert client._npc.actuation_blocked
    assert len(client.wire.sent) == before
    assert client.wire.moves == []


def test_received_c7_survives_timeout_and_sells_without_reclick():
    client, now = _blocked_offer()
    # A received C7 in this round is already sufficient authority; do not
    # destroy it just because the UI clock has expired.
    client.wire.add(_c7(((6, 12, 12),)))
    before = len(client.wire.sent)
    _answer_sale(client)
    _pump(client, now)
    _pump(client, now)
    assert sum(f[:2] == b"\xc9\x00" for f in client.wire.sent[before:]) == 1
    assert not any(f[:2] == b"\x90\x00" for f in client.wire.sent[before:])
    assert client.build_native_state(Goal.GRIND).zeny == 92


def test_timeout_c7_sale_waits_for_delayed_result_before_restarting():
    client, now = _blocked_offer()
    client.wire.add(_c7(((6, 12, 12),)))
    before = len(client.wire.sent)
    _pump(client, now)
    _pump(client, now)
    _pump(client, now)
    assert [f[:2] for f in client.wire.sent[before:]] == [b"\xc9\x00"]
    client.wire.add(_cb(0))
    _pump(client, now)
    assert client._npc.view is None
    assert client._npc_retries == NPC_RETRY_BUDGET


def test_c4_without_c7_retries_then_releases_instead_of_resending_c5():
    client, now = _blocked_offer()
    before = len(client.wire.sent)

    def no_sell_list(raw):
        client.wire.sent.append(raw)
        if raw[:2] == b"\x90\x00":
            client.wire.add(_c4(DEALER))

    client.wire._send = no_sell_list
    for _ in range(55):
        _pump(client, now)
    frames = client.wire.sent[before:]
    assert sum(f[:2] == b"\x90\x00" for f in frames) == NPC_RETRY_BUDGET
    assert sum(f[:2] == b"\xc5\x00" for f in frames) == NPC_RETRY_BUDGET
    assert not any(f[:2] == b"\xc9\x00" for f in frames)
    assert client._npc.view is None
    assert client.wire.moves
