"""Offline actual consumers; synthetic frames and helper proof, no live authority."""

from dataclasses import replace
from typing import Any

import pytest

from robots.app.planning_context import (
    InvestigationReader,
    ObservationSnapshot,
    serialized_response,
)
from robots.app.planning_job_context import capture_job_context
from robots.domain.decisions import build_decision_request
from robots.domain.model import BotState, Goal
from robots.domain.planning import Capabilities, PlanningIdentity
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.society.memory import MemoryLog, StubSummarizer
from tests.test_native_capacity_context import capacity_frames
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import actual_clients


def reader_for(state: BotState) -> InvestigationReader:
    assert state.native_epoch is not None
    identity = PlanningIdentity("agent", "world", state.name, state.native_epoch, "pre-re")
    snapshot = ObservationSnapshot(
        identity, state, Capabilities(frozenset(), frozenset(), frozenset())
    )
    return InvestigationReader(
        identity,
        lambda: snapshot,
        PublicSkillKnowledge("pre-re", ()),
        MemoryLog(StubSummarizer()),
    )


def model_facts(state: BotState, consumer: str) -> dict[str, Any]:
    facts: dict[str, Any]
    if consumer == "clef_request":
        facts = build_decision_request(state)["state"]["inventory_capacity"]
    else:
        reader = reader_for(state)
        result = reader.read(reader.identity, "character", max_utf8_bytes=8192)
        assert result["status"] == "OK"
        facts = result["data"]["inventory_capacity"]
    return facts


@pytest.mark.parametrize("consumer", ["clef_request", "llm_character"])
def test_actual_consumers_distinguish_received_capacity_from_offline_slots(
    monkeypatch: Any, consumer: str
) -> None:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    assert bind(client, proof_for(wire))
    state = client.build_native_state(Goal.GRIND)
    facts = model_facts(state, consumer)
    assert (facts["weight"], facts["max_weight"], facts["inventory_slots"]) == (210, 20000, 100)
    assert facts["purchase_authorized"] is False
    native = facts["native_capacity"]
    assert native["status"] == "RECEIVED"
    assert native["source"] == "selected-self-b0-24-25"
    assert native["units"] == "raw_engine_counts"
    assert native["clock"] == "monotonic"
    assert (native["epoch"], native["character"], native["account_id"], native["character_id"]) == (
        1,
        state.name,
        999,
        77,
    )
    assert (native["selection_epoch"], native["map_epoch"], native["sampled_at"]) == (1, 1, 100.0)
    assert native["complete"] is True
    assert native["nonnegative"] is True
    assert native["inventory_changed_sequence"] is None
    assert native["weight"]["value"] == 210
    assert native["max_weight"]["value"] == 20000
    assert native["weight"]["receipt_sequence"] < native["max_weight"]["receipt_sequence"]
    assert native["weight"]["observed_at"] == native["max_weight"]["observed_at"] == 100.0
    offline = facts["server_self_slots"]
    assert offline["status"] == "OFFLINE_SERVER_METADATA"
    assert offline["clock"] == "unix"
    assert offline["source_id"] == "offline-read-1"
    assert offline["observed_at_unix"] == 1700000000.0
    assert offline["provenance"] == "operator/server-verified offline DB snapshot"
    assert (
        offline["account_id"],
        offline["char_id"],
        offline["name"],
        offline["session_epoch"],
    ) == (999, 77, state.name, 1)
    assert offline["scope"] == "SELF"
    assert offline["native_packet"] is False
    assert offline["atomic_online_state"] is False
    assert offline["purchase_authorized"] is False
    assert len(sent) == 2


@pytest.mark.parametrize("consumer", ["clef_request", "llm_character"])
@pytest.mark.parametrize("receipts", [False, True])
def test_raw_state_numbers_cannot_replace_received_or_server_verified_facts(
    monkeypatch: Any, consumer: str, receipts: bool
) -> None:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames(0, 100))
    proof = proof_for(wire)
    proof["selected_owner_metadata"]["inventory_slots"] = 0
    assert bind(client, proof)
    current = client.build_native_state(Goal.GRIND)
    altered = replace(current, weight=999, max_weight=888, inventory_slots=100)
    if not receipts:
        altered = replace(altered, capacity_receipt=None, server_self_slots=None)
    facts = model_facts(altered, consumer)
    expected = (0, 100, 0) if receipts else (None, None, None)
    assert (facts["weight"], facts["max_weight"], facts["inventory_slots"]) == expected
    if not receipts:
        assert facts["native_capacity"] == {"status": "UNKNOWN"}
        assert facts["server_self_slots"] == {"status": "UNKNOWN"}
    assert facts["purchase_authorized"] is False
    assert len(sent) == 2


@pytest.mark.parametrize("consumer", ["clef_request", "llm_character"])
@pytest.mark.parametrize(
    ("weight", "maximum", "slots"),
    [
        (0, 0, 0),
        (210, 100, 100),
        (-1, 100, None),
        (1, -1, 0),
        (0, None, None),
        (None, 20000, 100),
        (None, None, None),
    ],
)
def test_historical_zero_negative_overweight_partial_and_unknown_controls(
    monkeypatch: Any, consumer: str, weight: int | None, maximum: int | None, slots: int | None
) -> None:
    wire, client, receive, sent = actual_clients(monkeypatch)
    wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
    client.build_native_state(Goal.GRIND)  # Clear the initial historical weight10.
    frames = capacity_frames(weight or 0, maximum or 0)
    if weight is not None:
        receive(frames[0])
    if maximum is not None:
        receive(frames[1])
    if slots is not None:
        proof = proof_for(wire)
        proof["selected_owner_metadata"]["inventory_slots"] = slots
        assert bind(client, proof)
    facts = model_facts(client.build_native_state(Goal.GRIND), consumer)
    assert (facts["weight"], facts["max_weight"], facts["inventory_slots"]) == (
        weight,
        maximum,
        slots,
    )
    native = facts["native_capacity"]
    if weight is None and maximum is None:
        assert native == {"status": "UNKNOWN"}
    else:
        complete = weight is not None and maximum is not None
        assert native["status"] == ("RECEIVED" if complete else "PARTIAL")
        assert native["complete"] == complete
        assert native["nonnegative"] == all(v is None or v >= 0 for v in (weight, maximum))
        assert (native["weight"] is None) == (weight is None)
        assert (native["max_weight"] is None) == (maximum is None)
    if slots is None:
        assert facts["server_self_slots"] == {"status": "UNKNOWN"}
    assert facts["purchase_authorized"] is False
    assert len(sent) == 2


@pytest.mark.parametrize("boundary", ["socket", "selection", "session"])
def test_actual_reader_current_owner_unknown_but_capture_keeps_detached_history(
    monkeypatch: Any, boundary: str
) -> None:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    assert bind(client, proof_for(wire))
    original = client.build_native_state(Goal.GRIND)
    reader = reader_for(original)
    identity = reader.identity
    caps = Capabilities(frozenset(), frozenset(), frozenset())
    snapshot = ObservationSnapshot(identity, original, caps)
    captured = capture_job_context(identity, snapshot, reader.public, reader.memory)
    assert captured is not None
    reader.provider = lambda: ObservationSnapshot(
        identity, client.build_native_state(Goal.GRIND), caps
    )
    before = reader.read(identity, "character")["data"]["inventory_capacity"]
    request = build_decision_request(original)
    before["native_capacity"]["weight"]["value"] = 999
    before["server_self_slots"]["source_id"] = "mutated-output"
    request["state"]["inventory_capacity"]["max_weight"] = 1
    assert model_facts(original, "clef_request")["max_weight"] == 20000
    assert reader.read(identity, "character")["data"]["inventory_capacity"]["weight"] == 210
    captured_fact = captured.read(identity, "character")["data"]["inventory_capacity"]
    captured_fact["native_capacity"]["weight"]["value"] = 777
    assert captured.read(identity, "character")["data"]["inventory_capacity"]["weight"] == 210
    if boundary == "socket":
        wire.sock = object()
    elif boundary == "selection":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
    else:
        client._planning_session = object()
    now = reader.read(identity, "character")
    assert now["status"] == "OK"
    unknown = now["data"]["inventory_capacity"]
    assert (unknown["weight"], unknown["max_weight"], unknown["inventory_slots"]) == (
        None,
        None,
        None,
    )
    assert unknown["native_capacity"] == unknown["server_self_slots"] == {"status": "UNKNOWN"}
    retained = captured.read(identity, "character")["data"]["inventory_capacity"]
    assert retained == model_facts(original, "clef_request")
    assert retained["purchase_authorized"] is False
    assert captured.read(replace(identity, agent="other"), "character")["status"] == "DENIED"
    receive(*capacity_frames(0, 0))
    fresh = reader.read(identity, "character")["data"]["inventory_capacity"]
    assert (fresh["weight"], fresh["max_weight"], fresh["inventory_slots"]) == (0, 0, None)
    assert len(sent) == 2


@pytest.mark.parametrize("source_length", [1, 128, 129])
def test_actual_bound_source_and_existing_character_response_budget_controls(
    monkeypatch: Any, source_length: int
) -> None:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    source_id = "a" * source_length
    assert bind(client, proof_for(wire), source_id=source_id) == (source_length <= 128)
    state = client.build_native_state(Goal.GRIND)
    reader = reader_for(state)
    normal = reader.read(reader.identity, "character")
    assert normal["status"] == "OK"
    assert len(serialized_response(normal)) <= 4096
    offline = normal["data"]["inventory_capacity"]["server_self_slots"]
    if source_length <= 128:
        assert offline["source_id"] == source_id
        assert offline["provenance"] == "operator/server-verified offline DB snapshot"
        assert "login_ip" not in offline
        assert "login_port" not in offline
    else:
        assert offline == {"status": "UNKNOWN"}
    bounded = reader.read(reader.identity, "character", max_utf8_bytes=256)
    assert bounded["status"] == "UNAVAILABLE"
    assert bounded["truncated"] is True
    assert bounded["data"]["reason"] == "response budget"
    assert "inventory_capacity" not in bounded["data"]
    assert len(serialized_response(bounded)) <= 256
    assert len(sent) == 2
