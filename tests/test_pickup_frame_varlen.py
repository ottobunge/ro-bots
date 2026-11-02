"""The 0x07E4 window-selection registration and the leg-63/64 history.

Leg 63 killed every session that picked up: the served binary
(rathena-playable:20180704-e985006171d2) parses CZ_ITEM_PICKUP 0x07E4 with the
20090818 ItemListWindowSelected row -- ``parseable_packet(0x07e4,-1,
clif_parse_ItemListWindowSelected,2,4,8,12)`` (clif_packetdb.hpp:1268) -- so it
reads the declared length at offset 2. The builder's fixed 6-byte TakeItem
frame put the floor-item AID in that word: the server read "expected packet
length 319, but only 6 bytes remaining" (the AID 321 read as a length) and
disconnected each of the four pickup agents. Leg 64 re-aimed the builder at
the var-len 0x07E4 shape: every send survived, parsed harmlessly as a window
selection, and zero inventory moved -- 0x07E4 is NOT the pickup hop at all.

Leg 65 (tests/test_pickup_frame_takeitem_0362.py) read the REAL TakeItem id
from the compiled packet DB: the clif_shuffle.hpp ``> 20180307`` final block
registers ``0x0362,6,clif_parse_TakeItem,2`` (last-write-wins over the plain
packetdb.hpp rows; 0x07E4 ends as the -1 ItemListWindowSelected row). This
file now pins what survives of the 0x07E4 story: the framer table keeps the
var-len window-selection registration (leg 64 proved it parses safely), the
leg-63 disconnect signature stays named, and the builder never emits the dead
0x07E4 hop again.
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


def _packetdb() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pickup_frame_packetdb", REPO / "spikes/003-clientless-limbs/packetdb.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The 2009-era var-len frame for floor-item AID 321, as the 0x07E4
# ItemListWindowSelected row frames it: type.W(0x07E4) + len.W(8) + AID.L.
# Historical bytes: the leg-64 builder emitted exactly this (pdb.pack's
# var-len shape, the 0xC6/0xC7 precedent) and the send parsed as a window
# selection -- no inventory ever moved.
SERVED_PICKUP_321 = bytes.fromhex("e407080041010000")

# The leg-63 killer (historical): the fixed 6-byte TakeItem frame ON THE
# 0x07E4 ID. The served var-len parser read the AID word at offset 2 as the
# length (321 > 6 bytes remaining) and disconnected the session. The same
# fixed shape is CORRECT on the real 0x0362 row (leg 65).
LEG63_FIXED_FRAME = bytes.fromhex("e40741010000")

CLOCK = struct.pack("<HI", 0x007F, 123)


def served_declared_length(frame: bytes) -> int:
    """The served clif_parse length gate (clif.cpp:25757-25776) for one frame.

    For a -1 packet the server reads the declared length at offset 2, requires
    ``4 <= declared <= 32768``, and disconnects when fewer bytes than declared
    remain in the FIFO (the leg-63 warning). Returns the consumed length.
    """
    if len(frame) < 4:
        return 0  # the server waits for more bytes
    declared: int = struct.unpack_from("<H", frame, 2)[0]
    if not 4 <= declared <= 32768:
        pytest.fail(f"served parser: invalid packet_len {declared}")
    if len(frame) < declared:
        pytest.fail(
            f"served parser: expected packet length {declared}, "
            f"but only {len(frame)} bytes remaining (disconnect)"
        )
    return declared


def test_builder_no_longer_emits_the_dead_window_selection_hop() -> None:
    """Regression guard on the leg-64 finding: 0x07E4 is the served image's
    ItemListWindowSelected row -- the var-len frame parsed harmlessly as a
    window selection and moved no inventory. The pickup builder rides the
    real 0x0362 TakeItem row instead (tests/test_pickup_frame_takeitem_0362.py)."""
    frame = gameplay.pickup(321)
    assert frame != SERVED_PICKUP_321
    assert struct.unpack_from("<H", frame, 0)[0] != 0x07E4


def test_framer_varlen_row_still_packs_the_historical_frame() -> None:
    """The 0x07E4 row is unchanged: pdb.pack still prepends the length word
    for the -1 registration (the 0xC6/0xC7 precedent) -- the historical
    leg-64 frame is reproducible from the table alone."""
    packetdb = _packetdb()
    assert packetdb.pack(0x07E4, struct.pack("<I", 321)) == SERVED_PICKUP_321


def test_framer_table_registers_07e4_variable_length() -> None:
    """The framer's packet table carries the served -1 declaration (leg 64
    proved the row parses safely; it stays)."""
    packetdb = _packetdb()
    assert packetdb.PACKET_DB[0x07E4] == packetdb.VAR
    assert packetdb.is_variable(0x07E4)


def test_07e4_row_frames_the_historical_varlen_frame_desync_free() -> None:
    """History pin: the var-len window-selection row consumes exactly the
    leg-64 frame and keeps the stream aligned."""
    packetdb = _packetdb()
    assert served_declared_length(SERVED_PICKUP_321) == len(SERVED_PICKUP_321) == 8
    packets, rest = packetdb.parse_stream(SERVED_PICKUP_321 + CLOCK)
    assert packets == [(0x07E4, SERVED_PICKUP_321), (0x007F, CLOCK)]
    assert rest == b""


@pytest.mark.parametrize("split", range(len(SERVED_PICKUP_321 + CLOCK) + 1))
def test_coalesced_stream_fragments_reassemble(split: int) -> None:
    """No desync at any fragment boundary: the var-len row reassembles the
    0x07E4 frame and the following frame intact."""
    packetdb = _packetdb()
    stream = SERVED_PICKUP_321 + CLOCK
    assert isinstance(split, int)
    packets, pending = packetdb.parse_stream(stream[:split])
    second, rest = packetdb.parse_stream(pending + stream[split:])
    assert packets + second == [(0x07E4, SERVED_PICKUP_321), (0x007F, CLOCK)]
    assert rest == b""


def test_leg63_fixed_frame_is_the_disconnect_signature() -> None:
    """The historical 6-byte frame WAS the leg-63 session killer on the 0x07E4
    id: the AID word reads as a length nothing can satisfy. Pinned as
    historical bytes so the regression stays named (the same fixed shape is
    the CORRECT frame on the real 0x0362 row)."""
    declared = struct.unpack_from("<H", LEG63_FIXED_FRAME, 2)[0]
    assert declared == 321  # the floor-item AID misread as the length
    with pytest.raises(pytest.fail.Exception, match="disconnect"):
        served_declared_length(LEG63_FIXED_FRAME)


def test_self_test_accounts_for_the_served_override() -> None:
    """The derivation (tree: later TakeItem,6 row wins) and the served
    binary (the 20090818 -1 row) are separate authorities; the shadow
    records the divergence so the packetdb self-test stays true."""
    packetdb = _packetdb()
    shadows: Any = packetdb._NATIVE_REGISTRATION_SHADOWS
    assert shadows[0x07E4] == (6, -1)
    assert packetdb.self_test(verbose=False)
