"""Source-shaped offline frames through the real client and Clef builder, not live evidence."""

import json
import struct

from robots.app.playing_runtime import PlayingClient
from robots.domain.decisions import build_decision_request
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire


def hit(source: int = 999, target: int = 123, amount: int = 5) -> bytes:
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, source, target)
    struct.pack_into("<i", raw, 22, amount)
    return bytes(raw)


def test_received_encounter_reaches_real_clef_request():
    wire = Wire()
    wire.add(hit())
    client = PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    request = build_decision_request(state, ["private memory"])
    assert request["state"].get("recent_encounters") == [
        {
            "epoch": 1,
            "sequence": 4,
            "actor_id": 123,
            "damage": 5,
            "damage2": 0,
            "species_id": 1002,
            "species_sequence": 3,
            "self_level_then": 10,
            "level_sequence": 0,
            "level_source": "selection",
            "level_binding": "e985006/MAIN/preRE20180704/CHARACTER_INFO",
        }
    ]
    assert request["model"] == "clef"
    assert request["state"]["memory_view"] == "private memory"
    assert request["state"]["inventory"] == "unknown"
    assert not wire.sent
    assert not wire.moves


def test_coalesced_future_level_never_rewrites_earlier_hit():
    wire = Wire()
    wire.add(hit(), struct.pack("<HHi", 0x00B0, 11, 11), hit(amount=7))
    wire.status_params[11] = 11  # Native client has dispatched the whole batch.
    state = PlayingClient(wire).build_native_state(Goal.GRIND)
    facts = build_decision_request(state)["state"]["recent_encounters"]
    assert state.base_level == 11
    assert [(f["sequence"], f["self_level_then"], f["level_sequence"]) for f in facts] == [
        (4, 10, 0),
        (6, 11, 5),
    ]
    assert facts[0]["level_source"] == "selection"
    assert facts[1]["level_source"] == "native_level11"
    assert facts[1]["level_binding"] == "e985006/MAIN/preRE20180704/0x00B0/11"
    assert not wire.sent


def test_empty_legacy_schema_questions_vitals_and_memory_are_unchanged():
    wire = Wire()
    wire.status_params = {5: 73, 6: 100, 7: 0, 8: 20}
    client = PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    before = build_decision_request(state, ["private memory"])
    assert state.recent_encounters == ()
    assert "recent_encounters" not in before["state"]
    wire.add(hit())
    after = build_decision_request(client.build_native_state(Goal.GRIND), ["private memory"])
    assert after["state"].pop("recent_encounters")
    assert before == after
    bot = after["state"]["bot"]
    assert (bot["hp"], bot["max_hp"], bot["sp"], bot["max_sp"]) == (73, 100, 0, 20)
    assert (bot["hp_ratio"], bot["sp_ratio"]) == (0.73, 0.0)
    assert not wire.sent


def test_replayed_getters_detach_scalar_payloads_and_isolate_bots():
    first_wire, second_wire = Wire(), Wire()
    first_wire.add(hit())
    first, second = PlayingClient(first_wire), PlayingClient(second_wire)
    state = first.build_native_state(Goal.GRIND)
    request = build_decision_request(state)
    original = json.dumps(request, sort_keys=True)
    assert (
        json.dumps(build_decision_request(first.build_native_state(Goal.GRIND)), sort_keys=True)
        == original
    )
    state.recent_encounters[0]["species_id"] = 999999
    assert json.dumps(request, sort_keys=True) == original
    request["state"]["recent_encounters"][0]["damage"] = 999999
    again = first.build_native_state(Goal.GRIND)
    assert again.recent_encounters[0]["species_id"] == 1002
    assert again.recent_encounters[0]["damage"] == 5
    assert (
        "recent_encounters"
        not in build_decision_request(second.build_native_state(Goal.GRIND))["state"]
    )
    assert not first_wire.sent
    assert not second_wire.sent


def test_forwarded_native_history_obeys_approved_record_and_utf8_budget():
    wire = Wire()
    wire.add(*(hit(amount=amount) for amount in range(1, 21)))
    state = PlayingClient(wire).build_native_state(Goal.GRIND)
    facts = build_decision_request(state)["state"]["recent_encounters"]
    assert 1 <= len(facts) <= 8
    encoded = json.dumps(facts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(encoded) <= 2048
    assert [f["sequence"] for f in facts] == list(range(24 - len(facts), 24))
    assert facts[-1]["damage"] == 20
    assert tuple(facts) == state.recent_encounters
    assert all(f["level_binding"] for f in facts)
    assert not wire.sent
