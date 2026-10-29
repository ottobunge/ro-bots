"""Synthetic UNIT frames only: real framer, no clients or native observations."""

import importlib.util
import json
import struct
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def packet_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "emotion_packetdb", ROOT / "spikes/003-clientless-limbs/packetdb.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("gid", [0, 0x12345678, 0x80000000, 0xFFFFFFFF])
@pytest.mark.parametrize("emote", [0, 1, 255])
def test_synthetic_emotion_individual(gid: int, emote: int) -> None:
    packetdb = packet_module()
    raw = struct.pack("<HIB", 0x00C0, gid, emote)
    assert packetdb.parse_stream(raw) == ([(0x00C0, raw)], b"")
    assert struct.unpack("<HIB", raw) == (0x00C0, gid, emote)


EMOTION = struct.pack("<HIB", 0x00C0, 0x12345678, 255)
CLOCK = struct.pack("<HI", 0x007F, 123)
STOP = struct.pack("<HIHH", 0x0088, 42, 100, 200)
NAME = struct.pack("<HI", 0x0ADF, 42) + bytes(52)
STREAM = EMOTION + CLOCK + STOP + NAME + EMOTION + EMOTION
EXPECTED = [(0x00C0, EMOTION), (0x007F, CLOCK), (0x0088, STOP), (0x0ADF, NAME)] + [
    (0x00C0, EMOTION)
] * 2


@pytest.mark.parametrize("split", range(len(STREAM) + 1))
def test_synthetic_coalesced_all_fragment_boundaries(split: int) -> None:
    packetdb = packet_module()
    first, pending = packetdb.parse_stream(STREAM[:split])
    second, tail = packetdb.parse_stream(pending + STREAM[split:])
    assert first + second == EXPECTED
    assert tail == b""


@pytest.mark.parametrize("cut", range(len(EMOTION)))
def test_synthetic_truncated_emotion_retains_bytes(cut: int) -> None:
    packetdb = packet_module()
    assert packetdb.parse_stream(EMOTION[:cut]) == ([], EMOTION[:cut])
    assert packetdb.parse_stream(CLOCK + EMOTION[:cut]) == ([(0x007F, CLOCK)], EMOTION[:cut])


def test_synthetic_one_byte_chunks() -> None:
    packetdb = packet_module()
    pending = b""
    frames = []
    for byte in STREAM:
        complete, pending = packetdb.parse_stream(pending + bytes([byte]))
        frames.extend(complete)
    assert frames == EXPECTED
    assert pending == b""


@pytest.mark.parametrize("prefix", [b"", EMOTION, EMOTION + EMOTION, STREAM])
def test_synthetic_unknown_is_not_skipped(prefix: bytes) -> None:
    packetdb = packet_module()
    with pytest.raises(ValueError, match=f"unknown packet 0xfafa at {len(prefix)},"):
        packetdb.parse_stream(prefix + b"\xfa\xfa" + CLOCK)


def test_every_legacy_mapping_is_preserved() -> None:
    """The current table equals the full reconstruction of its reviewed lanes.

    expected (888, the migration baseline) + 0x00C0 (npc-dialogue) +
    0x00B6 (npc-close) + additions (6, npc receive) + presentation (0x01B3)
    + char_page (0x099D) + 0x00BC (criterion-9 stat ack) + 0x00BE
    (stat-change point-cost updates) == PACKET_DB (900).
    """
    packetdb = packet_module()
    baseline = json.loads(
        (ROOT / "run/reviews/native-manifest-migration-baseline.json").read_text()
    )["current_final_PACKET_DB"]
    expected = {int(key, 16): value for key, value in baseline.items()}
    assert len(expected) == 888
    assert 0x00C0 not in expected
    additions = {0x00B4: -1, 0x00B5: 6, 0x00B7: -1, 0x00C4: 6, 0x0142: 6, 0x01D4: 6}
    manifest = json.loads((ROOT / "protocol/main-20180704-pre-re-npc-dialogue.json").read_text())
    assert {
        row["id"]: row["length"] for row in manifest["packets"] if row["id"] in additions
    } == additions
    presentation = {0x01B3: 67}
    char_page = {0x099D: -1}  # charlist-per-page framing (pinned common/packets.hpp:621-626)
    stat_change = {0x00BE: 5}  # ZC_STATUS_CHANGE SP_U* point-cost updates (clif.cpp:3774)
    assert packetdb.PACKET_DB[0x01B3] == 67
    prior_889 = expected | {0x00C0: 7}
    prior_890 = prior_889 | {0x00B6: 6}
    prior_891 = prior_890 | {0x00BC: 6}
    shop_lists = {0x00C7: -1}  # ZC_PC_SELL_ITEMLIST: length-prefixed variable (clif.cpp:2265-2280)
    # Guild-create slice: ZC_RESULT_MAKE_GUILD 0x0167 (3B), the reply the
    # pinned server sent to the live-verified charter request (0x0165).
    guild_reply = {0x0167: 3}
    # Guild invite slice (packets.hpp:1302-1330): the inviter ack + the
    # invitee prompt + the reply echo, all live-verified on the e2e world.
    guild_invite = {0x0168: 14, 0x0169: 3, 0x016A: 30, 0x016B: 10}
    # Leg 35 (2026-10-28): ZC_ACK_WEAR_EQUIP_V5 0x0999 (11B) - the reply to
    # the equip progression's CZ_REQ_WEAR_EQUIP (0x0998). Without it the
    # framer raised "unknown packet 0x0999" and every agent froze.
    wear_ack = {0x0999: 11, 0x01F2: 20, 0x01EB: 10}
    assert (
        prior_891
        | additions
        | presentation
        | char_page
        | stat_change
        | shop_lists
        | guild_reply
        | guild_invite
        | wear_ack
        == packetdb.PACKET_DB
    )
    assert len(packetdb.PACKET_DB) == 909
