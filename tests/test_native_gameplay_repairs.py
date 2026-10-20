"""Concrete failed-review repairs; offline wire facts, never native acceptance."""

import struct

import pytest

from robots.adapters import native_gameplay as g


def fixed(pid: int, size: int) -> bytes:
    return struct.pack("<H", pid) + bytes(size - 2)


def initial() -> tuple[tuple[int, float, int, bytes], ...]:
    row = bytearray(28)
    struct.pack_into("<HHHH", row, 0, 0x0991, 28, 2, 501)
    struct.pack_into("<h", row, 9, 3)
    return ((1, 1.0, 0x02EB, fixed(0x02EB, 13)), (2, 2.0, 0x0991, bytes(row)))


@pytest.mark.parametrize(("pid", "size"), [(0x00AF, 6), (0x07FA, 8)])
def test_delete_before_weight_never_rearms_stale_inventory(pid: int, size: int) -> None:
    tracker = g.NativeGameplayTracker(999)
    frames = (
        *initial(),
        (3, 3.0, pid, fixed(pid, size)),
        (4, 4.0, 0x00B0, struct.pack("<HHi", 0x00B0, 24, 0)),
    )
    assert tracker.consume_snapshot(1, 0, frames)
    view = tracker.view
    assert view.inventory_counts is None
    assert not view.inventory_known
    assert view.observed_inventory_counts == ((501, 3),)
    assert tracker.consume_snapshot(1, 0, frames)
    assert tracker.view == view
    tracker.ingest(5, 5.0, 0x00B0, struct.pack("<HHi", 0x00B0, 24, 0))
    assert tracker.view.inventory_counts is None


def test_empty_party_message_denies_before_encoding() -> None:
    with pytest.raises(ValueError, match="Invalid UTF8 party chat"):
        g.party_chat("", speaker_name="Novice")


@pytest.mark.parametrize("text", [" ", "\n", "é", "x" * 254])
def test_nonempty_chat_preserves_exact_bytes(text: str) -> None:
    body = ("ExactName : " + text).encode()
    assert (
        g.party_chat(text, speaker_name="ExactName")
        == struct.pack("<HH", 0x0108, len(body) + 4) + body
    )


@pytest.mark.parametrize(
    ("pid", "size", "field"),
    [(0x08C8, 34, "damage"), (0x0080, 7, "deaths"), (0x0ACB, 12, "xp"), (0x0A37, 59, "pickups")],
)
def test_event_retention_keeps_wire_sequence_and_replay_safety(
    monkeypatch: pytest.MonkeyPatch, pid: int, size: int, field: str
) -> None:
    monkeypatch.setattr(g, "MAX_EVENTS", 2, raising=False)
    tracker = g.NativeGameplayTracker(999)
    frames = []
    for seq in range(1, 6):
        raw = bytearray(fixed(pid, size))
        if pid == 0x0080:
            struct.pack_into("<IB", raw, 2, 999, 1)
        elif pid == 0x0ACB:
            struct.pack_into("<Hq", raw, 2, 1, seq)
        elif pid == 0x0A37:
            struct.pack_into("<HHH", raw, 2, 2, 1, 501)
        frames.append((seq, float(seq), pid, bytes(raw)))
    assert tracker.consume_snapshot(1, 0, tuple(frames))
    view = tracker.view
    assert [event.seq for event in getattr(view, field)] == [4, 5]
    assert tracker.consume_snapshot(1, 3, tuple(frames[3:]))
    assert tracker.view == view
    if pid == 0x0A37:
        assert view.acquired_counts == ((501, 5),)


def floor_item(aid: int) -> bytes:
    return struct.pack("<HIHHBhhBBhb h", 0x0ADD, aid, 501, 0, 1, 42, 37, 0, 0, 1, 0, 0)


def test_floor_overflow_poisoned_until_new_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g, "MAX_FLOOR_ITEMS", 2, raising=False)
    tracker = g.NativeGameplayTracker(999)
    assert tracker.consume_snapshot(1, 0, initial()[:1])
    frames = tuple((i + 1, float(i), 0x0ADD, floor_item(i)) for i in range(1, 4))
    assert not tracker.consume_snapshot(1, 0, frames)
    assert not tracker.view.perception_ready
    assert not tracker.view.floor_items
    assert not tracker.consume_snapshot(1, 0, initial()[:1])
    tracker.ingest(5, 5.0, 0x02EB, fixed(0x02EB, 13))
    assert not tracker.view.perception_ready
    assert tracker.consume_snapshot(2, 0, initial()[:1])
    assert tracker.view.perception_ready


def test_floor_disappearance_releases_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g, "MAX_FLOOR_ITEMS", 1, raising=False)
    tracker = g.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0ADD, floor_item(1))
    tracker.ingest(2, 2.0, 0x0ADD, floor_item(1))
    tracker.ingest(3, 3.0, 0x00A1, struct.pack("<HI", 0x00A1, 1))
    tracker.ingest(4, 4.0, 0x0ADD, floor_item(2))
    assert tuple(item.floor_item_id for item in tracker.view.floor_items) == (2,)


def test_acquired_item_types_overflow_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g, "MAX_ITEM_TYPES", 1, raising=False)
    tracker = g.NativeGameplayTracker(999)
    for seq, item in enumerate((501, 502), 1):
        raw = bytearray(fixed(0x0A37, 59))
        struct.pack_into("<HHH", raw, 2, seq, 1, item)
        if seq == 1:
            tracker.ingest(seq, float(seq), 0x0A37, bytes(raw))
        else:
            with pytest.raises(ValueError, match="capacity"):
                tracker.ingest(seq, float(seq), 0x0A37, bytes(raw))
    assert tracker.view.inventory_counts is None
    assert not tracker.view.acquired_counts


def test_inventory_slots_overflow_cannot_publish_partial_stock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(g, "MAX_INVENTORY_SLOTS", 1, raising=False)
    tracker = g.NativeGameplayTracker(999)
    assert tracker.consume_snapshot(1, 0, initial())
    raw = bytearray(initial()[1][3])
    struct.pack_into("<H", raw, 4, 3)
    frames = ((3, 3.0, 0x0991, bytes(raw)), (4, 4.0, 0x00B0, struct.pack("<HHi", 0x00B0, 24, 0)))
    assert not tracker.consume_snapshot(1, 0, frames)
    assert tracker.view.inventory_counts is None
    assert not tracker.view.inventory_known
