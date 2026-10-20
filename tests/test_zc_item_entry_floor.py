"""The tracker must ingest this pinned server's floor-item frame.

Window-22 blocker: the production tracker ingests floor items only on
0x0ADD (newer clients), but the pinned rAthena (e985006171d2, MAIN
20180704 pre-re) broadcasts ZC_ITEM_ENTRY 0x009D - 17 bytes per the pinned
packets_struct.hpp (uint16 itemId branch, since MAIN_NUM 20180704 <
20181121):

    int16 packetType; uint32 AID; uint16 itemId; uint8 identify;
    uint16 x; uint16 y; uint16 amount; uint8 subX; uint8 subY;

Without the 0x009D branch tracker.view.floor_items stays empty live and the
loot leg can never dispatch 0x0362 (window-22: floor_items 0 across 900 s
despite mob contact).
"""

import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters import native_gameplay as gameplay  # noqa: E402


def zc_item_entry(
    aid: int = 510001, item: int = 909, x: int = 174, y: int = 366, amount: int = 1
) -> bytes:
    raw = struct.pack("<HIHBHHHBB", 0x009D, aid, item, 1, x, y, amount, 3, 5)
    assert len(raw) == 17, len(raw)
    return raw


_zc_item_entry = zc_item_entry  # backwards-compatible alias


def test_zc_item_entry_ingests_floor_item() -> None:
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x009D, _zc_item_entry())
    view = tracker.view
    assert len(view.floor_items) == 1
    entry = view.floor_items[0]
    assert entry.floor_item_id == 510001
    assert entry.item_id == 909
    assert entry.amount == 1
    assert (entry.position.x, entry.position.y) == (174, 366)


def test_zero_filler_entry_is_ignored_not_stored() -> None:
    """Audited-framing contract: all-zero payloads are authority-neutral."""
    tracker = gameplay.NativeGameplayTracker(999)
    raw = bytearray(_zc_item_entry(amount=0))
    struct.pack_into("<H", raw, 13, 0)
    tracker.ingest(2, 2.0, 0x009D, bytes(raw))
    assert not tracker.view.floor_items
