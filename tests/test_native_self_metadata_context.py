"""Offline helper metadata through actual client; no DB, model or live transport."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.model import Goal
from tests.test_native_shop_selection import actual_clients


def proof_for(wire: Any) -> dict[str, Any]:
    return {
        "passed": True,
        "read_only": True,
        "native_sessions_opened": 0,
        "inference_calls": 0,
        "native_gameplay_acceptance": False,
        "selected_owner_metadata": {
            "scope": "SELF",
            "account_id": wire.aid,
            "char_id": wire.gid,
            "name": wire.char_name,
            "inventory_slots": 100,
            "provenance": "operator/server-verified offline DB snapshot",
            "atomic_online_state": False,
            "native_packet": False,
            "purchase_authorized": False,
        },
    }


def bind(client: PlayingClient, proof: object, **kwargs: Any) -> bool:
    values = {
        "source_id": "offline-read-1",
        "observed_at_unix": 1700000000.0,
        "login_ip": client.wire.login_ip,
        "login_port": client.wire.login_port,
    }
    values.update(kwargs)
    return client.bind_server_self_slots(proof, **values)


BAD_PROOF_FIELDS = [
    ("passed", False),
    ("passed", 1),
    ("read_only", False),
    ("native_sessions_opened", 1),
    ("native_sessions_opened", False),
    ("inference_calls", 1),
    ("inference_calls", 0.0),
    ("native_gameplay_acceptance", True),
    ("scope", "PEER"),
    ("account_id", True),
    ("account_id", 998),
    ("char_id", 78),
    ("char_id", 77.0),
    ("name", "Other"),
    ("inventory_slots", True),
    ("inventory_slots", -1),
    ("inventory_slots", 101),
    ("inventory_slots", "100"),
    ("inventory_slots", 100.0),
    ("inventory_slots", None),
    ("provenance", "native packet"),
    ("atomic_online_state", True),
    ("native_packet", True),
    ("purchase_authorized", True),
    ("purchase_authorized", 0),
]


@pytest.mark.parametrize(("field", "value"), BAD_PROOF_FIELDS)
def test_invalid_helper_metadata_becomes_unknown(monkeypatch, field, value):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    proof = proof_for(wire)
    assert bind(client, proof)
    prior = client.build_native_state(Goal.GRIND)
    target = proof if field in proof else proof["selected_owner_metadata"]
    target[field] = value
    assert not bind(client, proof)
    current = client.build_native_state(Goal.GRIND)
    assert current.inventory_slots is None
    assert current.server_self_slots is None
    assert prior.inventory_slots == 100
    assert prior.server_self_slots is not None
    assert not prior.server_self_slots.purchase_authorized
    assert len(sent) == 2


@pytest.mark.parametrize(
    "field",
    [
        "passed",
        "read_only",
        "native_sessions_opened",
        "inference_calls",
        "native_gameplay_acceptance",
        "selected_owner_metadata",
    ],
)
def test_missing_envelope_field_denies(monkeypatch, field):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    proof = proof_for(wire)
    del proof[field]
    assert not bind(client, proof)
    state = client.build_native_state(Goal.GRIND)
    assert state.inventory_slots is None
    assert state.server_self_slots is None
    assert len(sent) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", ""),
        ("source_id", "a" * 129),
        ("source_id", "read\n1"),
        ("source_id", None),
        ("observed_at_unix", True),
        ("observed_at_unix", -1),
        ("observed_at_unix", float("nan")),
        ("observed_at_unix", float("inf")),
        ("observed_at_unix", 10**400),
        ("observed_at_unix", "1700000000"),
        ("login_ip", "different.example"),
        ("login_ip", None),
        ("login_port", 1),
        ("login_port", True),
        ("login_port", 6900.0),
    ],
)
def test_bad_source_or_endpoint_denies(monkeypatch, field, value):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert not bind(client, proof_for(wire), **{field: value})
    assert client.build_native_state(Goal.GRIND).inventory_slots is None
    assert len(sent) == 2


@pytest.mark.parametrize("slots", [0, 1, 100])
def test_allowance_is_raw_detached_historical_metadata(monkeypatch, slots):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    before = client.build_native_state(Goal.GRIND)
    assert before.inventory_slots is None
    assert before.server_self_slots is None
    proof = proof_for(wire)
    proof["selected_owner_metadata"]["inventory_slots"] = slots
    assert bind(client, proof)
    current = client.build_native_state(Goal.GRIND)
    receipt = current.server_self_slots
    assert receipt is not None
    assert receipt.inventory_slots == slots == current.inventory_slots
    assert receipt.account_id == wire.aid
    assert receipt.char_id == wire.gid
    assert receipt.name == wire.char_name
    assert receipt.scope == "SELF"
    assert receipt.source_id == "offline-read-1"
    assert receipt.observed_at_unix == 1700000000.0  # Never compared to injected mono=100.
    assert receipt.login_ip == wire.login_ip
    assert receipt.login_port == wire.login_port
    assert receipt.session_epoch == wire.native_epoch
    assert not receipt.native_packet
    assert not receipt.atomic_online_state
    assert not receipt.purchase_authorized
    frozen_field = "inventory_slots"
    with pytest.raises(FrozenInstanceError):
        setattr(receipt, frozen_field, 99)
    proof["selected_owner_metadata"]["inventory_slots"] = 2
    assert deepcopy(current).server_self_slots == receipt
    assert client.build_native_state(Goal.GRIND).inventory_slots == slots
    assert before.inventory == current.inventory
    assert current.inventory_known
    assert before.npc_dialogue == current.npc_dialogue
    assert len(sent) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("class_fresh", False),
        ("selection_epoch", None),
        ("selection_epoch", True),
        ("map_epoch", 2),
        ("selected_character_snapshot", None),
        ("connected_map", False),
        ("running", False),
        ("rx_error", "transport error"),
        ("aid", True),
        ("gid", True),
    ],
)
def test_binding_requires_actual_selected_map_session(monkeypatch, field, value):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    setattr(wire, field, value)
    assert not bind(client, proof_for(wire))
    assert len(sent) == 2


@pytest.mark.parametrize("invalid", ["char_id", "job", "level", "auth", "position"])
def test_binding_requires_valid_selected_snapshot_and_received_auth(monkeypatch, invalid):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    if invalid == "char_id":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot, raw_char_id=78)
    elif invalid == "job":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot, raw_job_id=1)
    elif invalid == "level":
        wire.selected_character_snapshot = replace(
            wire.selected_character_snapshot, snapshot_base_level=0
        )
    elif invalid == "auth":
        client._authenticated_baseline = False
    else:
        assert client._tracker is not None
        client._tracker._position = None
    assert not bind(client, proof_for(wire))
    assert len(sent) == 2


@pytest.mark.parametrize("replacement", ["session", "wire", "socket", "reader", "selection"])
def test_reference_replacement_permanently_discards_publication(monkeypatch, replacement):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert bind(client, proof_for(wire))
    prior = client.build_native_state(Goal.GRIND)
    if replacement == "session":
        target, field, value = client, "_planning_session", object()
    elif replacement == "wire":
        other_wire, _other, _other_receive, _other_sent = actual_clients(monkeypatch)
        target, field, value = client, "wire", other_wire
    elif replacement == "socket":
        target, field, value = wire, "sock", object()
    elif replacement == "reader":
        target, field, value = wire, "rx_thread", SimpleNamespace(is_alive=lambda: True)
    else:
        target, field, value = (
            wire,
            "selected_character_snapshot",
            replace(wire.selected_character_snapshot),
        )
    original = getattr(target, field)
    setattr(target, field, value)
    assert client.build_native_state(Goal.GRIND).server_self_slots is None
    setattr(target, field, original)
    assert client.build_native_state(Goal.GRIND).inventory_slots is None
    assert prior.inventory_slots == 100
    assert prior.server_self_slots is not None
    assert len(sent) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("running", False),
        ("class_fresh", False),
        ("selection_epoch", 2),
        ("map_epoch", 2),
        ("login_ip", "another.example"),
        ("login_port", 6901),
        ("char_name", "Other"),
        ("gid", 78),
        ("aid", 998),
    ],
)
def test_session_eligibility_loss_never_revives_old_metadata(monkeypatch, field, value):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert bind(client, proof_for(wire))
    prior = client.build_native_state(Goal.GRIND)
    original = getattr(wire, field)
    setattr(wire, field, value)
    try:
        state = client.build_native_state(Goal.GRIND)
    except NativeTelemetryUnavailable:
        pass
    else:
        assert state.server_self_slots is None
    setattr(wire, field, original)
    assert client.build_native_state(Goal.GRIND).inventory_slots is None
    assert prior.inventory_slots == 100
    assert len(sent) == 2


@pytest.mark.parametrize("lifecycle", ["connect", "close", "epoch", "gap"])
def test_lifecycle_and_continuity_loss_discard_metadata(monkeypatch, lifecycle):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert bind(client, proof_for(wire))
    prior = client.build_native_state(Goal.GRIND)
    if lifecycle in ("connect", "close"):
        monkeypatch.setattr(wire, lifecycle, lambda: None)
        getattr(client, lifecycle)()
        if lifecycle == "close":
            with pytest.raises(NativeTelemetryUnavailable):
                client.build_native_state(Goal.GRIND)
            monkeypatch.setattr(wire, "connect", lambda: None)
            client.connect()
    elif lifecycle == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    else:
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
        assert not bind(client, proof_for(wire))
        assert client._server_self_slots is None
        assert prior.inventory_slots == 100
        assert len(sent) == 2
        return
    assert client.build_native_state(Goal.GRIND).inventory_slots is None
    assert prior.server_self_slots is not None
    assert prior.inventory_slots == 100
    assert len(sent) == 2


def test_another_wrapper_never_inherits_server_metadata(monkeypatch):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert bind(client, proof_for(wire))
    other = PlayingClient(wire, monotonic=lambda: 100.0)
    assert other.build_native_state(Goal.GRIND).inventory_slots is None
    assert client.build_native_state(Goal.GRIND).inventory_slots == 100
    assert len(sent) == 2


def test_transport_loss_seen_by_existing_rest_reader_cannot_revive_metadata(monkeypatch):
    wire, client, _receive, sent = actual_clients(monkeypatch)
    assert bind(client, proof_for(wire))
    wire.running = False
    with pytest.raises(NativeTelemetryUnavailable):
        client.planning_rest_observation()
    wire.running = True
    assert client.build_native_state(Goal.GRIND).inventory_slots is None
    assert len(sent) == 2


# Revision (criterion-9 live chain): ("dispatch_errors", 1) left the deny
# parametrization — one unparseable frame is a per-frame parse failure, not a
# transport failure; the health gate no longer starves telemetry on it
# (fx0's shop-interior deadlock, windows 43-48).
