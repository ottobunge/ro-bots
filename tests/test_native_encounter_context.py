"""Synthetic source-shaped receipts, never live gameplay acceptance."""

import importlib
import json
import runpy
import struct
from dataclasses import replace
from pathlib import Path
from types import ModuleType

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker, ObservedDamage
from tests.test_native_gameplay import actor


def context() -> ModuleType:
    try:
        module = importlib.import_module("robots.adapters.native_encounter_context")
    except ModuleNotFoundError:
        module = None
    assert module is not None, "native encounter component is missing"
    return module


def species_frame(pid: int = 0x09FD, aid: int = 123, kind: int = 5, job: int = 1002) -> bytes:
    raw = bytearray(actor(pid, aid, kind))
    struct.pack_into("<h", raw, 23, job)
    return bytes(raw)


def test_species_from_observed_job_not_actor_id() -> None:
    observation = context().decode_actor_species(
        species_frame(), epoch=1, sequence=2, own_actor_id=999
    )
    assert observation is not None
    assert (
        observation.epoch,
        observation.sequence,
        observation.actor_id,
        observation.species_id,
    ) == (1, 2, 123, 1002)


def received_damage(sequence: int = 3, damage: int = 18, damage2: int = 4) -> ObservedDamage:
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, 999, 123)
    struct.pack_into("<i", raw, 22, damage)
    struct.pack_into("<i", raw, 30, damage2)
    tracker = NativeGameplayTracker(999)
    tracker.ingest(sequence, float(sequence), 0x08C8, bytes(raw))
    return tracker.view.damage[-1]


def test_hit_captures_received_species_and_level_at_receipt() -> None:
    module = context()
    assert hasattr(module, "build_hit_fact"), "typed hit builder missing"
    species = module.decode_actor_species(species_frame(), epoch=1, sequence=2, own_actor_id=999)
    level = module.ReceivedSelfLevel(1, 1, 7, "native_level11", "MAIN-pre-re-20180704/e985")
    fact = module.build_hit_fact(
        received_damage(), epoch=1, own_actor_id=999, window_start=0, species=species, level=level
    )
    assert fact is not None
    assert (fact.species_id, fact.self_level_then, fact.damage, fact.damage2) == (1002, 7, 18, 4)
    assert fact.level_sequence == 1
    assert fact.species_sequence == 2
    assert fact.level_source == "native_level11"
    assert fact.as_dict()["self_level_then"] == 7


def test_cross_boundary_and_future_joins_stay_unknown() -> None:
    m = context()
    for observation in [
        m.ObservedActorSpecies(1, 2, 123, True),
        m.ObservedActorSpecies(True, 2, 123, 1002),
        m.ObservedActorSpecies(2, 2, 123, 1002),
        m.ObservedActorSpecies(1, 4, 123, 1002),
        m.ObservedActorSpecies(1, 2, 456, 1002),
        m.ObservedActorSpecies(1, 1, 123, 1002),
    ]:
        fact = m.build_hit_fact(
            received_damage(),
            epoch=1,
            own_actor_id=999,
            window_start=1,
            species=observation,
            level=m.ReceivedSelfLevel(2, 1, 7, "native_level11", "profile"),
        )
        assert fact.species_id is None
        assert fact.self_level_then is None


def test_non_hp_or_non_self_damage_is_not_a_hit() -> None:
    m = context()
    hit = received_damage()
    for invalid in [
        replace(hit, damage_type=True),
        replace(hit, target_id=-1),
        replace(hit, source_id=123),
        replace(hit, is_sp_damage=True),
        replace(hit, damage_type=2),
        replace(hit, damage_type=3),
        replace(hit, damage=0, damage2=0),
        replace(hit, damage=True),
        replace(hit, damage=-1),
        replace(hit, target_id=999),
    ]:
        assert m.build_hit_fact(invalid, epoch=1, own_actor_id=999, window_start=0) is None
    assert (
        m.build_hit_fact(received_damage(damage=0), epoch=1, own_actor_id=999, window_start=0)
        is not None
    )


def test_level_unknowns_and_baseline_provenance() -> None:
    m = context()
    for level in [
        None,
        m.ReceivedSelfLevel(True, 1, 7, "native_level11", "profile"),
        m.ReceivedSelfLevel(1, 0, 7, "native_level11", "profile"),
        m.ReceivedSelfLevel(1, 4, 8, "native_level11", "profile"),
        m.ReceivedSelfLevel(1, 1, 0, "native_level11", "profile"),
        m.ReceivedSelfLevel(1, 1, True, "native_level11", "profile"),
        m.ReceivedSelfLevel(1, 1, 7, "persona", "profile"),
        m.ReceivedSelfLevel(1, 1, 7, "native_level11", ""),
    ]:
        fact = m.build_hit_fact(
            received_damage(), epoch=1, own_actor_id=999, window_start=0, level=level
        )
        assert fact.self_level_then is None
        assert fact.level_source is None
    baseline = m.ReceivedSelfLevel(1, 0, 7, "selection", "MAIN-pre-re-20180704/e985")
    fact = m.build_hit_fact(
        received_damage(), epoch=1, own_actor_id=999, window_start=0, level=baseline
    )
    assert fact.self_level_then == 7
    assert fact.level_sequence == 0


def test_bounded_history_never_rewrites_or_joins_instances() -> None:
    m = context()
    assert hasattr(m, "HitHistory"), "per-agent bounded history missing"
    history = m.HitHistory(epoch=1)
    other = m.HitHistory(epoch=1)
    first = m.build_hit_fact(received_damage(), epoch=1, own_actor_id=999, window_start=0)
    assert (history.record(first), history.record(first)) == (True, False)
    for seq in range(4, 30):
        fact = m.build_hit_fact(
            received_damage(seq),
            epoch=1,
            own_actor_id=999,
            window_start=0,
            level=m.ReceivedSelfLevel(1, 1, 7, "native_level11", "é" * 100),
        )
        assert history.record(fact)
    assert len(history.records) in range(1, 9)
    payload = json.dumps(
        [fact.as_dict() for fact in history.records], ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert len(payload) <= 2048
    assert (first.self_level_then, history.record(first), other.records) == (None, False, ())
    history.reset(epoch=2)
    assert (history.records, history.record(first)) == ((), False)


def test_exact_receipt_metadata_required() -> None:
    m = context()
    for epoch, seq, own in [(True, 2, 999), (1, True, 999), (1, 0, 999), (1, 2, True)]:
        with pytest.raises(ValueError, match="Invalid"):
            m.decode_actor_species(species_frame(), epoch=epoch, sequence=seq, own_actor_id=own)
    with pytest.raises(ValueError, match="Invalid"):
        m.build_hit_fact(received_damage(), epoch=True, own_actor_id=999, window_start=0)


def test_only_complete_eligible_presentations_expose_species() -> None:
    m = context()
    for kind in [0, 6, 12, 255]:
        assert (
            m.decode_actor_species(species_frame(kind=kind), epoch=1, sequence=2, own_actor_id=999)
            is None
        )
    for aid in [999, (-999) & 0xFFFFFFFF]:
        assert (
            m.decode_actor_species(species_frame(aid=aid), epoch=1, sequence=2, own_actor_id=999)
            is None
        )
    for job in [0, -1, -32768]:
        assert (
            m.decode_actor_species(species_frame(job=job), epoch=1, sequence=2, own_actor_id=999)
            is None
        )
    raw = species_frame()
    for malformed in [raw[:32], raw + b"x", b"\x00\x00" + raw[2:], raw[:2] + b"\x20\x00" + raw[4:]]:
        with pytest.raises(ValueError, match="Invalid"):
            m.decode_actor_species(malformed, epoch=1, sequence=2, own_actor_id=999)


def test_all_actor_families_use_unchanged_physical_stream_framing() -> None:
    packetdb = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "spikes/003-clientless-limbs/packetdb.py")
    )
    parse = packetdb["parse_stream"]
    frames = [species_frame(pid) for pid in [0x09FD, 0x09FE, 0x09FF]]
    expected = [(int.from_bytes(raw[:2], "little"), raw) for raw in frames]
    for pid, raw in expected:
        assert packetdb["length_of"](pid) == -1
        assert parse(raw) == ([(pid, raw)], b"")
        assert (
            context().decode_actor_species(raw, epoch=1, sequence=2, own_actor_id=999).species_id
            == 1002
        )
    assert parse(b"".join(frames)) == (expected, b"")
    buffer = b""
    actual = []
    for byte in b"".join(frames):
        rows, buffer = parse(buffer + bytes([byte]))
        actual.extend(rows)
    assert (actual, buffer) == (expected, b"")


def test_absent_capture_and_vanished_actor_never_retrojoin() -> None:
    m = context()
    species = m.decode_actor_species(species_frame(), epoch=1, sequence=2, own_actor_id=999)
    old = m.build_hit_fact(received_damage(), epoch=1, own_actor_id=999, window_start=0)
    after_vanish = m.build_hit_fact(
        received_damage(6), epoch=1, own_actor_id=999, window_start=4, species=species
    )
    assert old.species_id is None
    assert old.self_level_then is None
    assert after_vanish.species_id is None


def test_oversized_receipt_consumes_cursor_without_rewriting_history() -> None:
    m = context()
    history = m.HitHistory(epoch=1)
    for sequence, binding, retained, sequences in [
        (3, "profile", True, [3]),
        (10, "界" * 1000, False, [3]),
        (9, "profile", False, [3]),
        (10, "rewritten", False, [3]),
        (11, "profile", True, [3, 11]),
    ]:
        fact = m.build_hit_fact(
            received_damage(sequence),
            epoch=1,
            own_actor_id=999,
            window_start=0,
            level=m.ReceivedSelfLevel(1, 0, 7, "selection", binding),
        )
        assert fact is not None
        assert fact.level_binding == binding
        if len(binding) == 1000:
            payload = json.dumps(
                [fact.as_dict()], ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            assert len(payload) > 2048
        before = history.records
        assert history.record(fact) is retained, f"unexpected retention at sequence {sequence}"
        if not retained:
            assert history.records is before
        assert [record.sequence for record in history.records] == sequences
        payload = json.dumps(
            [record.as_dict() for record in history.records],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        assert len(history.records) <= 8
        assert len(payload) <= 2048


def test_first_oversized_receipt_consumes_cursor_with_empty_history() -> None:
    m = context()
    history = m.HitHistory(epoch=1)
    for sequence, binding, retained in [
        (10, "ก" * 1000, False),
        (9, "profile", False),
        (10, "rewritten", False),
        (11, "profile", True),
    ]:
        fact = m.build_hit_fact(
            received_damage(sequence),
            epoch=1,
            own_actor_id=999,
            window_start=0,
            level=m.ReceivedSelfLevel(1, 0, 7, "selection", binding),
        )
        assert fact is not None
        assert fact.level_binding == binding
        assert history.record(fact) is retained
        assert [record.sequence for record in history.records] == ([11] if retained else [])


def test_foreign_oversized_receipt_does_not_consume_cursor() -> None:
    m = context()
    history = m.HitHistory(epoch=1)
    for epoch, sequence, binding, retained in [
        (1, 3, "profile", True),
        (2, 100, "界" * 1000, False),
        (1, 4, "profile", True),
    ]:
        fact = m.build_hit_fact(
            received_damage(sequence),
            epoch=epoch,
            own_actor_id=999,
            window_start=0,
            level=m.ReceivedSelfLevel(epoch, 0, 7, "selection", binding),
        )
        assert fact is not None
        assert fact.level_binding == binding
        before = history.records
        assert history.record(fact) is retained
        if not retained:
            assert history.records is before
    assert [record.sequence for record in history.records] == [3, 4]


def test_reset_restarts_cursor_after_oversized_receipt() -> None:
    m = context()
    history = m.HitHistory(epoch=1)
    oversized = m.build_hit_fact(
        received_damage(10),
        epoch=1,
        own_actor_id=999,
        window_start=0,
        level=m.ReceivedSelfLevel(1, 0, 7, "selection", "界" * 1000),
    )
    assert oversized is not None
    assert not history.record(oversized)
    history.reset(epoch=2)
    assert history.records == ()
    assert not history.record(oversized)
    fact = m.build_hit_fact(received_damage(1), epoch=2, own_actor_id=999, window_start=0)
    assert fact is not None
    assert history.record(fact)
    assert history.records == (fact,)


def test_failed_utf8_evaluation_preserves_cursor_and_records() -> None:
    m = context()
    history = m.HitHistory(epoch=1)
    first = m.build_hit_fact(received_damage(3), epoch=1, own_actor_id=999, window_start=0)
    assert first is not None
    assert history.record(first)
    before = history.records
    invalid_utf8 = m.build_hit_fact(
        received_damage(10),
        epoch=1,
        own_actor_id=999,
        window_start=0,
        level=m.ReceivedSelfLevel(1, 0, 7, "selection", "\ud800"),
    )
    assert invalid_utf8 is not None
    with pytest.raises(UnicodeEncodeError):
        history.record(invalid_utf8)
    assert history.records is before
    fact = m.build_hit_fact(received_damage(9), epoch=1, own_actor_id=999, window_start=0)
    assert fact is not None
    assert history.record(fact)
    assert history.records == (first, fact)
