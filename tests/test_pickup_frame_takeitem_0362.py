"""The REAL CZ_ITEM_PICKUP on the pinned 20180704 image is 0x0362, fixed 6.

Leg 64 proved the served image's 0x07E4 row is clif_parse_ItemListWindowSelected
(var-len): every dispatched pickup parsed harmlessly as a window selection and
no inventory ever moved. The REAL TakeItem registration for the compiled
profile (PACKETVER=20180704 -DPRERE, rathena/config.log:749) is the FINAL row
for 0x0362 in the packet DB -- packetdb_readdb (clif.cpp:25845-25847) memsets
the table and then includes clif_packetdb.hpp and clif_shuffle.hpp IN ORDER,
and packetdb_addpacket (clif.cpp:25808-25834) is a plain last-write-wins
assignment, so the last active row per id is what the served binary executes.

The final rows come from clif_shuffle.hpp's ``#elif PACKETVER > 20180307``
block (20180704 has no exact-date block and lands here -- "Clients after
2018-03-07bRagexeRE do not have shuffled packets anymore"), verbatim::

    parseable_packet(0x0362,6,clif_parse_TakeItem,2);
    parseable_packet(0x07E4,-1,clif_parse_ItemListWindowSelected,2,4,8,12);

Confirmed by preprocessing both headers with the exact compiled flags: the
last active rows in the translation unit are
``packetdb_addpacket(0x0362,6,clif_parse_TakeItem,2,0)`` and
``packetdb_addpacket(0x07E4,-1,clif_parse_ItemListWindowSelected,2,4,8,12,0)``.

The plain-table history (the 20120418 clif_packetdb.hpp block naming 0x0362
DropItem, and its own 0x07E4 TakeItem row) is OVERRIDDEN by the shuffle's
final block -- the leg-61 rewrite to 0x07E4 read the plain table and landed
on the window-selection hop. The client side now emits the REAL id with the
SERVED fixed-row shape: type.W + AID.L, exactly 6 bytes, NO len.W (fixed-size
C->S rows carry no length word; a length word would desync the payload).
0x07E4 stays registered var-len as the window-selection row leg 64 proved
parses safely.
"""

import importlib.util
import struct
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO / "spikes/003-clientless-limbs")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters import native_gameplay as gameplay  # noqa: E402
from robots.adapters.native_navigation import MapCache, WalkMap  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.domain.actions import Loot  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import Wire, entry_at, map_frame_at  # noqa: E402
from tests.test_zc_item_entry_floor import zc_item_entry  # noqa: E402


def _packetdb() -> Any:
    spec = importlib.util.spec_from_file_location(
        "takeitem0362_packetdb", REPO / "spikes/003-clientless-limbs/packetdb.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Golden bytes: CZ_ITEM_PICKUP 0x0362 for floor item AID 321 -- type.W + AID.L,
# the fixed 6-byte shape the served shuffle row declares (no len.W).
REAL_PICKUP_321 = bytes.fromhex("620341010000")

# The leg-63/64 dead hop: the 0x07E4 window-selection row the var-len era
# targeted. The builder must never emit it again.
DEAD_HOP_321 = bytes.fromhex("e407080041010000")

CLOCK = struct.pack("<HI", 0x007F, 123)


def test_pickup_builder_emits_the_real_takeitem_0362_frame() -> None:
    """Golden byte test: the builder emits 0x0362 with the fixed 6-byte shape."""
    frame = gameplay.pickup(321)
    assert frame == REAL_PICKUP_321
    assert len(frame) == 6
    assert struct.unpack_from("<H", frame, 0)[0] == 0x0362
    assert struct.unpack_from("<I", frame, 2)[0] == 321


def test_builder_boundaries_and_validation_unchanged() -> None:
    """The AID stays a validated uint32; both 32-bit extremes round-trip."""
    assert gameplay.pickup(0) == struct.pack("<HI", 0x0362, 0)
    assert gameplay.pickup(0xFFFFFFFF) == struct.pack("<HI", 0x0362, 0xFFFFFFFF)
    with pytest.raises(ValueError, match="uint32"):
        gameplay.pickup(-1)
    with pytest.raises(ValueError, match="uint32"):
        gameplay.pickup(2**32)


def test_builder_matches_the_framer_fixed_pack_shape() -> None:
    """The framer's fixed-row pack (type only, no len.W) emits the same bytes."""
    packetdb = _packetdb()
    assert not packetdb.is_variable(0x0362)
    assert packetdb.PACKET_DB[0x0362] == 6
    assert packetdb.pack(0x0362, struct.pack("<I", 321)) == gameplay.pickup(321)


def test_07e4_row_stays_the_window_selection() -> None:
    """Leg 64's proof stands: 0x07E4 remains registered var-len (the
    ItemListWindowSelected row that parses harmlessly), and the pickup
    builder never targets that dead hop again."""
    packetdb = _packetdb()
    assert packetdb.PACKET_DB[0x07E4] == packetdb.VAR
    assert packetdb.is_variable(0x07E4)
    assert gameplay.pickup(321) != DEAD_HOP_321
    assert struct.unpack_from("<H", gameplay.pickup(321), 0)[0] != 0x07E4


def test_served_fixed_row_consumes_exactly_six_bytes() -> None:
    """The served fixed-row gate (registered size 6, no length word) consumes
    exactly the frame and the following frame stays aligned -- desync-free at
    the packetdb's own parse table."""
    packetdb = _packetdb()
    frame = gameplay.pickup(321)
    packets, rest = packetdb.parse_stream(frame + CLOCK)
    assert packets == [(0x0362, frame), (0x007F, CLOCK)]
    assert rest == b""


@pytest.mark.parametrize("split", range(len(REAL_PICKUP_321 + CLOCK) + 1))
def test_fixed_frame_reassembles_at_every_fragment_boundary(split: int) -> None:
    """No desync at any split: the fixed 6-byte row reassembles the pickup
    and the trailing frame intact."""
    packetdb = _packetdb()
    stream = REAL_PICKUP_321 + CLOCK
    packets, pending = packetdb.parse_stream(stream[:split])
    second, rest = packetdb.parse_stream(pending + stream[split:])
    assert packets + second == [(0x0362, REAL_PICKUP_321), (0x007F, CLOCK)]
    assert rest == b""


def test_pickup_dispatch_uses_the_real_id() -> None:
    """The runtime's shared pickup dispatch sends the 0x0362 frame: the
    mechanical loot path performs the Loot action and the CZ_ITEM_PICKUP
    bytes on the wire are the builder's golden output (leg 64's four
    survived-but-inert sends shipped the window-selection id instead)."""
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), zc_item_entry(aid=321, item=909, x=43, y=38))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = runtime.PlayingClient(wire, cache=cache)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [gameplay.pickup(321)]
    assert client.wire.sent == [REAL_PICKUP_321]
