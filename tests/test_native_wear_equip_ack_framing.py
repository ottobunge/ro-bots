"""The wear-equip ack must be framable: leg 35 froze every agent on it.

Leg 35 (2026-10-28, 21:30-23:00 UTC) put a Knife (1201) in every population
char's right hand for the first time. The runtime's equip progression then
sent CZ_REQ_WEAR_EQUIP (0x0998) and the pinned server answered with
ZC_ACK_WEAR_EQUIP_V5 (0x0999, 11B) - which the client's framer did not know.
parse_stream raised "unknown packet 0x0999", the rx thread died, the transport
went unavailable, and every agent's tick silently early-returned forever
(NativeTelemetryUnavailable -> _planning_context_lost). Seven of seven.

Pinned source: map/packets_struct.hpp:1269-1276 (PACKET_ZC_REQ_WEAR_EQUIP_ACK,
int16 PacketType + uint16 index + uint32 wearLocation + uint16 wItemSpriteNumber
+ uint8 result = 11B, header 0x0999 for PACKETVER_MAIN_NUM >= 20121205) and
map/clif.cpp:4302-4328 (clif_equipitemack sends it).
"""

import hashlib
import importlib.util
import struct
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKETDB = ROOT / "spikes/003-clientless-limbs/packetdb.py"


def packet_module() -> Any:
    spec = importlib.util.spec_from_file_location("wear_ack_packetdb", PACKETDB)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ack(index: int = 3, wear: int = 0, sprite: int = 0, result: int = 2) -> bytes:
    """ZC_ACK_WEAR_EQUIP_V5: <index>.W <wear location>.L <view id>.W <result>.B."""
    return struct.pack("<HHIHB", 0x0999, index, wear, sprite, result)


WEAR_ACK_BLOCK = (
    b"# Leg 35 (2026-10-28): the wear-equip ack. A Knife in the right hand\n"
    b"# makes the runtime's equip progression send CZ_REQ_WEAR_EQUIP (0x0998);\n"
    b"# the pinned server answers with ZC_ACK_WEAR_EQUIP_V5 0x0999\n"
    b"# (<index>.W <wear location>.L <view id>.W <result>.B = 11B,\n"
    b"# packets_struct.hpp:1269-1276, clif.cpp:4302-4328). The framer did not\n"
    b'# know it: parse_stream raised "unknown packet 0x0999", the rx thread\n'
    b"# died and all seven leg-35 agents froze on a silent transport loss.\n"
    b"PACKET_DB.update({0x0999: 11})\n"
)
CHARSTAT_BLOCK = (
    b"# The guild member login notice, the next frame in the same path:\n"
    b"# ZC_UPDATE_CHARSTAT 0x01f2 (<account id>.L <char id>.L <status>.L\n"
    b"# <gender>.W <hair style>.W <hair color>.W = 20B, map/packets.hpp:876-885;\n"
    b"# compiled sizeof=20). The server sends it to a guild's other members when\n"
    b"# one logs in (map/guild.cpp:1439 -> clif_guild_memberlogin_notice), so it\n"
    b"# arrives at any char that shares a guild - the same silent transport loss.\n"
    b"PACKET_DB.update({0x01F2: 20})\n"
)


def test_wear_equip_ack_is_a_known_fixed_frame() -> None:
    module = packet_module()
    assert 0x0999 in module.PACKET_DB, "the wear-equip ack must be framable"
    assert module.PACKET_DB[0x0999] == 11
    assert module.length_of(0x0999) == 11


def test_wear_equip_ack_frames_out_of_the_stream() -> None:
    raw = ack()
    assert len(raw) == 11
    assert packet_module().parse_stream(raw) == ([(0x0999, raw)], b"")


def test_wear_equip_ack_does_not_desync_the_following_frame() -> None:
    """The live failure: the unknown frame killed the rx thread mid-stream."""
    following = struct.pack("<HHi", 0x00B0, 5, 42)
    packets, rest = packet_module().parse_stream(ack() + following)
    assert [pid for pid, _ in packets] == [0x0999, 0x00B0]
    assert rest == b""


def test_wear_equip_ack_is_not_variable_length() -> None:
    """A length-prefixed reading would swallow the following frame."""
    assert not packet_module().is_variable(0x0999)


def test_packethash_stays_pinned_to_the_equipped_item_block() -> None:
    """The byte-exact evidence blocks are pinned; keep the additions auditable."""
    raw = PACKETDB.read_bytes()
    assert raw.count(WEAR_ACK_BLOCK) == 1
    assert raw.count(CHARSTAT_BLOCK) == 1
    # The pinned blocks are the ONLY change to the packet table's evidence
    # bytes: the file minus both hashes to the pre-leg-35 table.
    stripped = raw.replace(WEAR_ACK_BLOCK, b"", 1).replace(CHARSTAT_BLOCK, b"", 1)
    assert hashlib.sha256(stripped).hexdigest() == (
        "13fbacab7a78c4fb6b3f1f4fa63dd311b7699a4dc0c86e8d66d4c627915c575b"
    )


# The guild member login notice: the frame that follows 0x0999 on the same
# path. ZC_UPDATE_CHARSTAT 0x01f2 (<account id>.L <char id>.L <status>.L
# <gender>.W <hair style>.W <hair color>.W = 20B, map/packets.hpp:876-885).
# A guild's other members receive it when one logs in (map/guild.cpp:1439).
def charstat(aid: int = 2000101, cid: int = 150101, status: int = 1) -> bytes:
    return struct.pack("<HII I HHH".replace(" ", ""), 0x01F2, aid, cid, status, 1, 0, 0)


def test_guild_login_notice_is_a_known_fixed_frame() -> None:
    module = packet_module()
    assert 0x01F2 in module.PACKET_DB, "the guild login notice must be framable"
    assert module.PACKET_DB[0x01F2] == 20
    assert module.length_of(0x01F2) == 20
    assert not module.is_variable(0x01F2)


def test_guild_login_notice_frames_out_of_the_stream() -> None:
    raw = charstat()
    assert len(raw) == 20
    assert packet_module().parse_stream(raw) == ([(0x01F2, raw)], b"")


def test_guild_login_notice_does_not_desync_the_following_frame() -> None:
    following = struct.pack("<HHi", 0x00B0, 5, 42)
    packets, rest = packet_module().parse_stream(charstat() + following)
    assert [pid for pid, _ in packets] == [0x01F2, 0x00B0]
    assert rest == b""


def test_charstat_block_stays_pinned_to_the_equipped_item_block() -> None:
    raw = PACKETDB.read_bytes()
    assert raw.count(CHARSTAT_BLOCK) == 1
    stripped = raw.replace(WEAR_ACK_BLOCK, b"", 1).replace(CHARSTAT_BLOCK, b"", 1)
    assert hashlib.sha256(stripped).hexdigest() == (
        "13fbacab7a78c4fb6b3f1f4fa63dd311b7699a4dc0c86e8d66d4c627915c575b"
    )


# The guild member position notice: the THIRD frame in the same path, and
# the one that killed the rx thread after 0x0999 and 0x01f2 were framed.
# ZC_NOTIFY_POSITION_TO_GUILDM 0x01eb (<account id>.L <x>.W <y>.W = 10B,
# map/packets.hpp:859-865; compiled sizeof=10). The server sends it to a
# guild's members when one of them moves (map/clif.cpp:3316-3335).
GUILDM_BLOCK = (
    b"# The guild member position notice - the THIRD frame in the same path, and\n"
    b"# the one that killed the rx thread after 0x0999 and 0x01f2 were framed.\n"
    b"# ZC_NOTIFY_POSITION_TO_GUILDM 0x01eb (<account id>.L <x>.W <y>.W = 10B,\n"
    b"# map/packets.hpp:859-865; compiled sizeof=10). The server sends it to a\n"
    b"# guild's members when one of them moves (map/clif.cpp:3316-3335), so it\n"
    b"# reaches every char that shares a guild - the same silent transport loss.\n"
    b"PACKET_DB.update({0x01EB: 10})\n"
)


def guildm(aid: int = 2000101, x: int = 148, y: int = 91) -> bytes:
    return struct.pack("<HIhh", 0x01EB, aid, x, y)


def test_guild_member_position_notice_is_a_known_fixed_frame() -> None:
    module = packet_module()
    assert 0x01EB in module.PACKET_DB, "the guild position notice must be framable"
    assert module.PACKET_DB[0x01EB] == 10
    assert module.length_of(0x01EB) == 10
    assert not module.is_variable(0x01EB)


def test_guild_member_position_notice_frames_out_of_the_stream() -> None:
    raw = guildm()
    assert len(raw) == 10
    assert packet_module().parse_stream(raw) == ([(0x01EB, raw)], b"")


def test_guild_member_position_notice_does_not_desync_the_following_frame() -> None:
    following = struct.pack("<HHi", 0x00B0, 5, 42)
    packets, rest = packet_module().parse_stream(guildm() + following)
    assert [pid for pid, _ in packets] == [0x01EB, 0x00B0]
    assert rest == b""


def test_the_three_guild_frames_are_all_pinned_together() -> None:
    """The three frames of the guild/equip path share ONE pinned digest."""
    raw = PACKETDB.read_bytes()
    assert raw.count(GUILDM_BLOCK) == 1
    stripped = (
        raw.replace(WEAR_ACK_BLOCK, b"", 1)
        .replace(CHARSTAT_BLOCK, b"", 1)
        .replace(GUILDM_BLOCK, b"", 1)
    )
    assert hashlib.sha256(stripped).hexdigest() == (
        "c2e5816690ab68ac9f8674f1c31290e6644e494e74911e29dccd19732c693f42"
    )


@pytest.mark.parametrize(
    ("index", "wear", "sprite", "result"), [(3, 0, 0, 2), (1, 2, 0, 1), (0, 0, 0, 0)]
)
def test_wear_equip_ack_layout_is_unchanged(
    index: int, wear: int, sprite: int, result: int
) -> None:
    """The frame is opaque bytes to the framer: it never decodes the fields."""
    raw = ack(index, wear, sprite, result)
    packets, _ = packet_module().parse_stream(raw)
    assert packets == [(0x0999, raw)]
