"""The served 0x07E4 declaration is VARIABLE-LENGTH: client side aligns with it.

Leg 63 killed every session that picked up: the served binary
(rathena-playable:20180704-e985006171d2) parses CZ_ITEM_PICKUP 0x07E4 with the
20090818 ItemListWindowSelected row -- ``parseable_packet(0x07e4,-1,
clif_parse_ItemListWindowSelected,2,4,8,12)`` (clif_packetdb.hpp:1268) -- so it
reads the declared length at offset 2. The builder's fixed 6-byte TakeItem
frame put the floor-item AID in that word: the server read "expected packet
length 319, but only 6 bytes remaining" (the AID 321 read as a length) and
disconnected each of the four pickup agents. The tree's later TakeItem,6 row
(clif_packetdb.hpp:1560) is not what the served image obeys.

The fix aligns the CLIENT side with the SERVED declaration: the builder
prepends the length word (the 0xC6/0xC7 var-len precedent, pdb.pack) and the
framer's table registers 0x07E4 as variable-length (-1).
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


# The served var-len frame for floor-item AID 321: type.W(0x07E4) + len.W(8)
# + AID.L -- exactly pdb.pack's var-len shape (the 0xC6/0xC7 precedent).
SERVED_PICKUP_321 = bytes.fromhex("e407080041010000")

# The leg-63 killer (historical): the fixed 6-byte TakeItem frame. The served
# var-len parser read the AID word at offset 2 as the length (321 > 6 bytes
# remaining) and disconnected the session.
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


def test_pickup_builder_emits_the_served_varlen_frame() -> None:
    """The builder prepends the length word the served db expects."""
    frame = gameplay.pickup(321)
    assert frame == SERVED_PICKUP_321
    declared = struct.unpack_from("<H", frame, 2)[0]
    assert declared == len(frame)
    assert declared == 8
    assert struct.unpack_from("<I", frame, 4)[0] == 321


def test_builder_matches_the_framer_varlen_pack_shape() -> None:
    """The 0xC6/0xC7 precedent: pdb.pack prepends the total length for a -1
    row; the production builder emits the identical bytes."""
    packetdb = _packetdb()
    assert packetdb.pack(0x07E4, struct.pack("<I", 321)) == gameplay.pickup(321)
    assert gameplay.pickup(0) == struct.pack("<HHI", 0x07E4, 8, 0)
    assert gameplay.pickup(0xFFFFFFFF) == struct.pack("<HHI", 0x07E4, 8, 0xFFFFFFFF)
    with pytest.raises(ValueError, match="uint32"):
        gameplay.pickup(-1)
    with pytest.raises(ValueError, match="uint32"):
        gameplay.pickup(2**32)


def test_framer_table_registers_07e4_variable_length() -> None:
    """The framer's packet table carries the served -1 declaration."""
    packetdb = _packetdb()
    assert packetdb.PACKET_DB[0x07E4] == packetdb.VAR
    assert packetdb.is_variable(0x07E4)


def test_served_parser_accepts_the_new_frame_desync_free() -> None:
    """Golden byte test: the served length gate passes and both framers
    (client framer and the served dispatcher) consume exactly the frame."""
    packetdb = _packetdb()
    frame = gameplay.pickup(321)
    assert served_declared_length(frame) == len(frame) == 8
    packets, rest = packetdb.parse_stream(frame + CLOCK)
    assert packets == [(0x07E4, frame), (0x007F, CLOCK)]
    assert rest == b""


@pytest.mark.parametrize("split", range(len(SERVED_PICKUP_321 + CLOCK) + 1))
def test_coalesced_stream_fragments_reassemble(split: int) -> None:
    """No desync at any fragment boundary: the var-len row reassembles the
    pickup and the following frame intact."""
    packetdb = _packetdb()
    stream = SERVED_PICKUP_321 + CLOCK
    assert isinstance(split, int)
    packets, pending = packetdb.parse_stream(stream[:split])
    second, rest = packetdb.parse_stream(pending + stream[split:])
    assert packets + second == [(0x07E4, SERVED_PICKUP_321), (0x007F, CLOCK)]
    assert rest == b""


def test_leg63_fixed_frame_is_the_disconnect_signature() -> None:
    """The historical 6-byte frame IS the leg-63 session killer under the
    served declaration: the AID word reads as a length nothing can satisfy.
    Pinned as historical bytes so the regression stays named."""
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
