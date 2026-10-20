"""Synthetic source-shaped frames, not native observations or combat evidence."""

import struct
from dataclasses import FrozenInstanceError

import pytest

from robots.adapters import native_actor_presentation as native


class BytesSubtype(bytes):
    """The decoder contract accepts only exact built-in bytes."""


def test_bytes_subtype_rejected():
    with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
        native.parse_actor_presentation(BytesSubtype(frame()))


@pytest.mark.parametrize(("packet_id", "size"), [(0x09FD, 110), (0x09FE, 103), (0x09FF, 104)])
def test_every_truncation_and_coalesced_frame_rejected(packet_id, size):
    raw = frame(packet_id, size)
    for end in range(size):
        with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
            native.parse_actor_presentation(raw[:end])
    with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
        native.parse_actor_presentation(raw + raw)


class IntSubtype(int):
    """Reject non-built-in integers at the pure classifier boundary."""


@pytest.mark.parametrize("value", [True, False, 0.0, 5.0, IntSubtype(0), -1, 256, None, "5"])
def test_invalid_classifier_input(value):
    assert native.presentation_kind(value) is None


def frame(
    packet_id: int = 0x09FE,
    size: int = 103,
    objecttype: int = 5,
    actor_id: int = 101,
    character_id: int = 202,
) -> bytes:
    return struct.pack("<HHBII", packet_id, size, objecttype, actor_id, character_id) + bytes(
        size - 13
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        bytes(3),
        bytes(103),
        frame(packet_id=0),
        frame(packet_id=0x1234),
        frame()[:-1],
        frame() + b"x",
        frame(size=110),
        struct.pack("<HH", 0x09FE, 102) + frame()[4:],
        bytearray(frame()),
        memoryview(frame()),
        None,
        "opaque",
    ],
)
def test_invalid_whole_frame_is_opaque(raw):
    with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
        native.parse_actor_presentation(raw)


@pytest.mark.parametrize(("packet_id", "size"), [(0x09FD, 110), (0x09FF, 104)])
def test_other_compiled_actor_layouts(packet_id, size):
    result = native.parse_actor_presentation(frame(packet_id, size))
    assert result.packet_id == packet_id
    assert result.actor_id == 101
    assert result.character_id == 202


@pytest.mark.parametrize(("packet_id", "size"), [(0x09FD, 110), (0x09FE, 103), (0x09FF, 104)])
@pytest.mark.parametrize("objecttype", range(256))
def test_all_u8_presentations_all_layouts(packet_id, size, objecttype):
    result = native.parse_actor_presentation(frame(packet_id, size, objecttype, 0xFFFFFFFF, 0))
    expected = {
        0: native.ActorPresentationKind.PLAYER_PRESENTATION,
        5: native.ActorPresentationKind.MONSTER_PRESENTATION,
        6: native.ActorPresentationKind.NPC_PRESENTATION,
        12: native.ActorPresentationKind.NPC_PRESENTATION,
    }.get(objecttype)
    assert result.objecttype == objecttype
    assert result.presentation_kind is expected
    assert result.actor_id == 0xFFFFFFFF
    assert result.character_id == 0


def test_zero_wire_id_and_max_character_id_are_not_heuristics():
    result = native.parse_actor_presentation(frame(actor_id=0, character_id=0xFFFFFFFF))
    assert result.actor_id == 0
    assert result.character_id == 0xFFFFFFFF
    assert result.presentation_kind is native.ActorPresentationKind.MONSTER_PRESENTATION


def test_metadata_is_frozen_and_has_only_header_fields():
    result = native.parse_actor_presentation(frame())
    field_name = "actor_id"
    with pytest.raises(FrozenInstanceError):
        setattr(result, field_name, 999)
    assert set(result.__dataclass_fields__) == {
        "packet_id",
        "actor_id",
        "character_id",
        "objecttype",
        "presentation_kind",
    }
    assert not isinstance(result.presentation_kind, str)


def test_zero_is_player_presentation():
    kind = native.presentation_kind(0)
    assert kind is not None
    assert kind.value == "player_presentation"


def test_npc_presentations_are_not_monsters():
    for value in (6, 12):
        kind = native.presentation_kind(value)
        assert kind is not None
        assert kind.value == "npc_presentation"


@pytest.mark.parametrize("value", [1, 2, 3, 4, 7, 8, 9, 10, 11, 13, 14, 255])
def test_unsupported_has_no_default(value):
    assert native.presentation_kind(value) is None


def test_source_shaped_spawn_preserves_distinct_ids():
    # Compiled frontier spawn fixture: zero pose, sanitized OfflineObject name.
    raw = bytearray.fromhex(
        "fe09670005650000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000004f66666c696e654f626a65637400000000"
        "00000000000000"
    )
    assert len(raw) == 103
    struct.pack_into("<I", raw, 9, 202)
    result = native.parse_actor_presentation(bytes(raw))
    assert result.packet_id == 0x09FE
    assert result.actor_id == 101
    assert result.character_id == 202
    assert result.objecttype == 5
    assert result.presentation_kind is native.ActorPresentationKind.MONSTER_PRESENTATION
