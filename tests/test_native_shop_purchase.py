"""Offline actual-client purchase exchange; all loaded shop facts are synthetic."""

import struct
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_npc_dialogue import NativeNpcDialogue
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.domain.model import Goal
from robots.domain.shop import QualifiedShopItem
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import ready_shop
from tests.test_playing_runtime import map_frame


def acquisition(index: int = 10, item: int = 1201, amount: int = 1) -> bytes:
    raw = bytearray(59)
    struct.pack_into("<HHhH", raw, 0, 0xA37, index, amount, item)
    raw[25] = 4
    return bytes(raw)


def offered(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, Any, list[bytes]]:
    wire, client, receive, sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    receive(
        struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201),
        struct.pack("<HHi", 0xB1, 20, 1000),
        struct.pack("<HHi", 0xB0, 24, 400),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    assert bind(client, proof_for(wire))
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    assert state.inventory_known
    assert state.inventory_slots == 100
    assert state.zeny == 1000
    assert state.weight == 400
    return wire, client, receive, sent


def known_facts(wire: Any, **overrides: Any) -> Any:
    values = {
        "source_id": "explicitly-trusted-offline-synthetic-loaded-facts",
        "account_id": wire.aid,
        "character_id": wire.gid,
        "epoch": wire.native_epoch,
        "npc_id": 123,
        "map_name": "prontera",
        "actual_item_id": 1201,
        "client_item_id": 1201,
        "loaded_weight": 400,
        "ordinary_shop": True,
        "nonstackable": True,
        "stable_price": 73,
        "stable_discount_price": 61,
        "valid_until": 105.0,
    }
    values.update(overrides)
    return QualifiedShopItem(**values)


def test_actual_quantity_one_acquired_and_replay_refused(monkeypatch):
    wire, client, receive, sent = offered(monkeypatch)
    assert callable(getattr(client, "npc_shop_purchase", None)), "missing owner purchase mint"
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    assert sent[-1] == bytes.fromhex("c80008000100b104")
    assert client.shop_purchase_progress().status == "issued"
    receive(
        struct.pack("<HHi", 0xB1, 20, 939),
        acquisition(),
        struct.pack("<HHi", 0xB0, 24, 800),
        struct.pack("<HB", 0xCA, 0),
    )
    progress = client.shop_purchase_progress()
    assert progress.status == "acquired"
    assert progress.inventory_index == 10
    assert progress.ca_result == 0
    assert client.build_native_state(Goal.GRIND).inventory == {"1201": 2}
    client.perform_native(action)
    assert client.npc_shop_purchase() is None
    assert len(sent) == 4


def test_receipts_during_successful_send_count(monkeypatch):
    wire, client, receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None

    def send(raw):
        sent.append(raw)
        receive(acquisition(), struct.pack("<HB", 0xCA, 0))

    monkeypatch.setattr(wire, "_send", send)
    client.perform_native(action)
    assert client.shop_purchase_progress().status == "acquired"
    assert len(sent) == 4


@pytest.mark.parametrize("origin", [OSError("uncertain send"), KeyboardInterrupt(), SystemExit()])
def test_failed_send_keeps_origin_unresolved_and_cannot_promote_receipts(monkeypatch, origin):
    wire, client, receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    attempts = []

    def send(raw):
        attempts.append(raw)
        receive(acquisition(), struct.pack("<HB", 0xCA, 0))
        raise origin

    monkeypatch.setattr(wire, "_send", send)
    with pytest.raises(type(origin)) as caught:
        client.perform_native(action)
    assert caught.value is origin
    progress = client.shop_purchase_progress()
    assert progress.status == "incomplete"
    assert progress.reason == "send outcome uncertain"
    assert progress.inventory_index is None
    assert progress.ca_result is None
    client.perform_native(action)
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert len(attempts) == 1
    assert len(sent) == 3


def test_server_rejection_is_terminal_not_acquisition(monkeypatch):
    wire, client, receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    receive(struct.pack("<HB", 0xCA, 2))
    progress = client.shop_purchase_progress()
    assert progress.status == "rejected"
    assert progress.ca_result == 2
    receive(acquisition(), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress() == progress
    client.perform_native(action)
    assert len(sent) == 4


def test_debit_and_ca0_without_acquisition_is_terminal_incomplete(monkeypatch):
    wire, client, receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    receive(struct.pack("<HHi", 0xB1, 20, 939), struct.pack("<HB", 0xCA, 0))
    progress = client.shop_purchase_progress()
    assert progress.status == "incomplete"
    assert progress.ca_result == 0
    assert progress.inventory_index is None
    assert client.build_native_state(Goal.GRIND).zeny == 939
    receive(acquisition(), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress() == progress
    client.perform_native(action)
    assert len(sent) == 4


def test_unknown_loaded_weight_never_uses_nominal_disk400(monkeypatch):
    wire, client, _receive, sent = offered(monkeypatch)
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert client.bind_shop_purchase_facts(known_facts(wire, loaded_weight=None))
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert len(sent) == 3


def test_foreign_owner_equal_dto_cannot_send(monkeypatch):
    wire, client, _receive, sent = offered(monkeypatch)
    other_wire, other, _other_receive, other_sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    assert other.bind_shop_purchase_facts(known_facts(other_wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    other_action = other.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    assert other_action == action
    other.perform_native(action)
    assert len(other_sent) == 3
    client.perform_native(action)
    assert len(sent) == 4


def test_offer_expiry_before_dispatch_never_renews_or_retries(monkeypatch):
    wire, client, _receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client._now = lambda: 105.0
    client.perform_native(action)
    assert client.shop_purchase_progress().status == "incomplete"
    client._now = lambda: 100.0
    client.perform_native(action)
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert len(sent) == 3


def test_foreign_failed_add_cannot_be_followed_by_purchase_success(monkeypatch):
    wire, client, receive, _sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    foreign = bytearray(acquisition(item=501))
    foreign[24] = 1
    receive(bytes(foreign), acquisition(), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress().status == "incomplete"


def test_unexpected_debit_cannot_report_acquired(monkeypatch):
    wire, client, receive, _sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    receive(struct.pack("<HHi", 0xB1, 20, 900), acquisition(), struct.pack("<HB", 0xCA, 0))
    progress = client.shop_purchase_progress()
    assert progress.status == "incomplete"
    assert progress.ca_result == 0


def test_purchase_consumes_controller_request_and_terminal_offer(monkeypatch):
    wire, client, receive, _sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    assert client._npc.requests == 3
    receive(struct.pack("<HB", 0xCA, 2))
    assert client.shop_purchase_progress().status == "rejected"
    assert client.build_native_state(Goal.GRIND).shop_offer is None


@pytest.mark.parametrize(
    "replacement", ["session", "wire", "sock", "reader", "selection", "controller"]
)
def test_purchase_owner_replacement_denies(monkeypatch, replacement):
    wire, client, _receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    if replacement == "session":
        client._planning_session = object()
    elif replacement == "wire":
        other_wire, _other, _other_receive, _other_sent = offered(monkeypatch)
        client.wire = other_wire
    elif replacement == "sock":
        wire.sock = object()
    elif replacement == "reader":
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    elif replacement == "selection":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
    else:
        client._npc = NativeNpcDialogue()
    client.perform_native(action)
    assert len(sent) == 3
    assert client.shop_purchase_progress().status == "incomplete"


@pytest.mark.parametrize("boundary", ["vanish", "map", "gap", "epoch", "deletion", "timeout"])
def test_issued_continuity_loss_never_acquires_or_retries(monkeypatch, boundary):
    wire, client, receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    if boundary == "vanish":
        receive(struct.pack("<HIB", 0x80, 123, 0))
    elif boundary == "map":
        receive(map_frame())
    elif boundary == "gap":
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "deletion":
        receive(struct.pack("<HHh", 0xAF, 9, 1))
    else:
        client._now = lambda: 105.0
    before = len(sent)
    receive(acquisition(), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress().status == "incomplete"
    client.perform_native(action)
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert len(sent) == before


@pytest.mark.parametrize("field", ["quantity", "item_id", "maximum_zeny", "epoch"])
def test_malformed_mutated_minted_intent_never_sends(monkeypatch, field):
    wire, client, _receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    object.__setattr__(action, field, True)
    client.perform_native(action)
    assert len(sent) == 3
    assert client.shop_purchase_progress().status == "incomplete"


@pytest.mark.parametrize(
    "case", ["budget", "zeny", "weight", "slots", "price", "canonical", "ordinary"]
)
def test_resource_or_qualification_unknown_denies_mint(monkeypatch, case):
    wire, client, receive, sent = offered(monkeypatch)
    changes = {}
    if case == "zeny":
        receive(struct.pack("<HHi", 0xB1, 20, 60))
    elif case == "weight":
        receive(struct.pack("<HHi", 0xB0, 25, 799))
    elif case == "slots":
        client._invalidate_self_slots()
    elif case == "price":
        changes["stable_discount_price"] = 60
    elif case == "canonical":
        changes["actual_item_id"] = 501
    elif case == "ordinary":
        changes["ordinary_shop"] = False
    client.bind_shop_purchase_facts(known_facts(wire, **changes))
    assert client.npc_shop_purchase(maximum_zeny=60 if case == "budget" else 61) is None
    assert len(sent) == 3


def test_common_health_loss_cannot_revive_pending_purchase(monkeypatch):
    wire, client, receive, _sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    wire.running = False
    with pytest.raises(NativeTelemetryUnavailable):
        client.planning_rest_observation()
    wire.running = True
    receive(acquisition(), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress().status == "incomplete"


@pytest.mark.parametrize("fault", ["type", "outside_allowance", "quantity", "occupied", "reserved"])
def test_malformed_or_disallowed_acquisition_never_acquires(monkeypatch, fault):
    wire, client, receive, _sent = offered(monkeypatch)
    proof = proof_for(wire)
    proof["selected_owner_metadata"]["inventory_slots"] = 10
    assert bind(client, proof)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    raw = bytearray(acquisition())
    if fault == "type":
        raw[25] = 0
    elif fault == "outside_allowance":
        struct.pack_into("<H", raw, 2, 12)
    elif fault == "quantity":
        struct.pack_into("<h", raw, 4, 2)
    else:
        struct.pack_into("<H", raw, 2, 9 if fault == "occupied" else 1)
    receive(bytes(raw), struct.pack("<HB", 0xCA, 0))
    assert client.shop_purchase_progress().status == "incomplete"
