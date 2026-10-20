"""Encounter stream windows exercised through actual PlayingClient requests (offline)."""

import struct

import pytest

from robots.adapters.native_encounter_context import HitHistory, ObservedHitFact
from robots.adapters.native_gameplay import MAX_EVENTS
from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.decisions import build_decision_request
from robots.domain.model import Goal
from tests.test_native_encounter_request import hit
from tests.test_playing_runtime import Wire, map_frame, monster


def encounters(client: PlayingClient):
    return build_decision_request(client.build_native_state(Goal.GRIND))["state"].get(
        "recent_encounters", []
    )


def appearance(species: int) -> bytes:
    raw = bytearray(monster())
    struct.pack_into("<h", raw, 23, species)
    return bytes(raw)


@pytest.mark.parametrize(("species", "kind"), [(-1, 5), (1002, 0), (1002, 6)])
def test_non_species_appearance_invalidates_old_join(species, kind):
    wire = Wire()
    wire.add(hit())
    client = PlayingClient(wire)
    original = encounters(client)[0]
    raw = bytearray(appearance(species))
    raw[4] = kind
    wire.add(bytes(raw), hit())
    facts = encounters(client)
    assert facts[0] == original
    assert facts[-1]["species_id"] is None
    assert facts[-1]["species_sequence"] is None


def test_vanish_requires_fresh_species_for_equal_actor_id():
    wire = Wire()
    wire.add(hit())
    client = PlayingClient(wire)
    original = encounters(client)[0]
    wire.add(struct.pack("<HIB", 0x0080, 123, 0), hit(), appearance(1007), hit())
    facts = encounters(client)
    assert [f["species_id"] for f in facts] == [1002, None, 1007]
    assert [f["species_sequence"] for f in facts] == [3, None, 7]
    assert facts[0] == original
    assert not wire.sent


def test_map_change_clears_joins_not_immutable_experience():
    wire = Wire()
    wire.add(hit())
    client = PlayingClient(wire)
    original = encounters(client)[0]
    wire.add(map_frame(), hit(), appearance(1007), hit())
    facts = encounters(client)
    assert [f["species_id"] for f in facts] == [1002, None, 1007]
    assert facts[0] == original
    assert not wire.sent


@pytest.mark.parametrize("fault", ["gap", "malformed", "stopped_reader"])
def test_native_safety_denies_request_and_invalidates_stream(fault):
    wire = Wire()
    wire.add(hit())
    client = PlayingClient(wire)
    assert encounters(client)
    if fault == "gap":
        wire.frames.append((6, 6.0, 0x08C8, hit()))
    elif fault == "malformed":
        wire.add(b"\xc8\x08")
    else:
        wire.rx_thread.is_alive = lambda: False
    with pytest.raises(NativeTelemetryUnavailable):
        encounters(client)
    assert client._encounters is None
    with pytest.raises(NativeTelemetryUnavailable):
        encounters(client)
    assert not wire.sent
    assert not wire.moves


def test_close_reconnect_discards_history_even_with_reused_epoch(monkeypatch):
    wire = Wire()
    monkeypatch.setattr(wire, "close", lambda: None, raising=False)
    monkeypatch.setattr(wire, "connect", lambda: None, raising=False)
    wire.add(hit())
    client = PlayingClient(wire)
    assert encounters(client)
    client.close()
    assert client._encounters is None
    with pytest.raises(NativeTelemetryUnavailable):
        encounters(client)
    wire.frames = []
    wire.add(map_frame(), appearance(1007), hit())
    wire.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 12, 10, 0, 0)
    client.connect()
    facts = encounters(client)
    assert len(facts) == 1
    assert (facts[0]["species_id"], facts[0]["self_level_then"]) == (1007, 12)
    assert not wire.sent


def test_future_appearance_does_not_retrojoin_unknown_species():
    wire = Wire()
    wire.frames = []
    wire.add(map_frame(), hit(), appearance(1007), hit())
    facts = encounters(PlayingClient(wire))
    assert [(f["actor_id"], f["species_id"], f["species_sequence"]) for f in facts] == [
        (123, None, None),
        (123, 1007, 3),
    ]


def test_invalid_received_level_invalidates_capture_without_baseline_fallback():
    wire = Wire()
    wire.add(struct.pack("<HHi", 0x00B0, 11, 0), hit())
    wire.status_params[11] = 0
    client = PlayingClient(wire)
    with pytest.raises(NativeTelemetryUnavailable):
        encounters(client)
    wire.add(struct.pack("<HHi", 0x00B0, 11, 9), hit())
    wire.status_params[11] = 9  # Decreases are actual updates, not persona guesses.
    facts = encounters(client)
    assert [(f["self_level_then"], f["level_sequence"], f["level_source"]) for f in facts] == [
        (None, None, None),
        (9, 6, "native_level11"),
    ]
    assert facts[0]["level_binding"] is None
    assert not wire.sent


def test_unmatched_selection_never_fills_prior_hit_level():
    wire = Wire()
    wire.selection_epoch = 2
    wire.add(hit())
    client = PlayingClient(wire)
    with pytest.raises(NativeTelemetryUnavailable):
        encounters(client)
    wire.selection_epoch = 1
    wire.add(struct.pack("<HHi", 0x00B0, 11, 11), hit())
    wire.status_params[11] = 11
    facts = encounters(client)
    assert facts[0]["self_level_then"] is None
    assert facts[0]["level_source"] is None
    assert facts[1]["self_level_then"] == 11
    assert facts[1]["level_sequence"] == 5


def test_epoch_reset_clears_all_experience_and_recaptures_selection():
    wire = Wire()
    wire.add(struct.pack("<HHi", 0x00B0, 11, 11), hit())
    wire.status_params[11] = 11
    client = PlayingClient(wire)
    assert encounters(client)[0]["self_level_then"] == 11
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.frames = []
    wire.status_params.pop(11)
    wire.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 12, 10, 0, 0)
    wire.add(map_frame(), hit())
    facts = encounters(client)
    assert len(facts) == 1
    assert (facts[0]["epoch"], facts[0]["sequence"]) == (2, 2)
    assert facts[0]["species_id"] is None
    assert (facts[0]["self_level_then"], facts[0]["level_source"]) == (12, "selection")
    assert not wire.sent


@pytest.mark.parametrize("receipt", ["peer", "npc", "heal", "sp", "sit", "stand"])
def test_non_self_hp_hit_receipts_do_not_become_experience(receipt):
    wire = Wire()
    raw = bytearray(hit())
    if receipt in ("peer", "npc"):
        struct.pack_into("<I", raw, 2, 123 if receipt == "peer" else 777)
    elif receipt == "heal":
        struct.pack_into("<i", raw, 22, -5)
    elif receipt == "sp":
        raw[26] = 1
    else:
        raw[29] = 2 if receipt == "sit" else 3
    wire.add(bytes(raw))
    assert encounters(PlayingClient(wire)) == []
    assert not wire.sent


def test_damage_evicted_by_tracker_is_not_reparsed_or_invented(monkeypatch):
    seen: list[int] = []
    original_record = HitHistory.record

    def record(history: HitHistory, fact: ObservedHitFact) -> bool:
        seen.append(fact.sequence)
        return original_record(history, fact)

    monkeypatch.setattr(HitHistory, "record", record)
    wire = Wire()
    wire.add(*(hit() for _ in range(MAX_EVENTS + 1)))
    client = PlayingClient(wire)
    facts = encounters(client)
    assert seen == list(range(5, MAX_EVENTS + 5))
    assert facts[-1]["sequence"] == MAX_EVENTS + 4
    assert encounters(client) == facts
    assert len(seen) == MAX_EVENTS
    assert not wire.sent
