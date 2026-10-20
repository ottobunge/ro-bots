"""Offline contracts for pinned MAIN/pre-re20180704 string input."""

import struct
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from robots.adapters.native_textinput import (
    NpcStringPrompt,
    decode_string_prompt,
    encode_selected_name,
)


@pytest.mark.parametrize("npc_id", [1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF])
def test_decode_preserves_unsigned_bits(npc_id: int) -> None:
    assert decode_string_prompt(struct.pack("<HI", 0x01D4, npc_id)) == NpcStringPrompt(npc_id)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"abc",
        b"abcde",
        b"abcdefg",
        struct.pack("<HI", 0x0142, 1),
        struct.pack("<HI", 0x9999, 1),
    ],
)
def test_decode_rejects_non_string_frames(raw: bytes) -> None:
    with pytest.raises(ValueError, match=r"String prompt|Not a supported"):
        decode_string_prompt(raw)


@pytest.mark.parametrize("npc_id", [1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF])
@pytest.mark.parametrize(
    "name", ["Otto", "MiXeD Name ", "e\u0301", "é", "A" * 23, "界" * 7 + "ab", "😀" * 5 + "abc"]
)
def test_encode_exact_selected_name(npc_id: int, name: str) -> None:
    packet = encode_selected_name(NpcStringPrompt(npc_id), name)
    header, length, signed_gid = struct.unpack("<HHi", packet[:8])
    value = packet[8:]
    assert header == 0x01D5
    assert length == len(packet) == 8 + len(name.encode("utf-8"))
    assert packet[4:8] == struct.pack("<I", npc_id)
    assert signed_gid == (npc_id if npc_id < 0x80000000 else npc_id - 0x100000000)
    assert value == name.encode("utf-8")
    assert b"\0" not in value  # Modern handler adds the destination NUL itself.
    # Independent offline model of active handler + safestrncpy, not server proof.
    message_len = length - 8
    assert message_len > 0
    capacity = min(message_len + 1, 71)  # PACKETVER >= 20151001; CHATBOX_SIZE=71.
    copied = value[: capacity - 1].split(b"\0", 1)[0] + b"\0"
    assert copied == name.encode("utf-8") + b"\0"


@pytest.mark.parametrize(
    "name",
    [
        "",
        "A" * 24,
        "界" * 8,
        "😀" * 6,
        "bad\0tail",
        pytest.param("\ud800", id="high-surrogate"),
        pytest.param("\udfff", id="low-surrogate"),
    ],
)
def test_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="Selected name"):
        encode_selected_name(NpcStringPrompt(1), name)


@pytest.mark.parametrize("name", [True, b"Otto", bytearray(b"Otto"), 1, None])
def test_rejects_non_string_names(name: object) -> None:
    with pytest.raises(TypeError):
        encode_selected_name(NpcStringPrompt(1), cast("str", name))


@pytest.mark.parametrize("npc_id", [0, -1, 0x100000000, 1 << 100])
def test_rejects_outside_id_domain(npc_id: int) -> None:
    with pytest.raises(ValueError, match="nonzero unsigned 32-bit"):
        NpcStringPrompt(npc_id)


@pytest.mark.parametrize("npc_id", [True, False, 1.0, "1", None])
def test_rejects_non_plain_integer_ids(npc_id: object) -> None:
    with pytest.raises(TypeError):
        NpcStringPrompt(cast("int", npc_id))


@pytest.mark.parametrize("raw", [True, None, "abcdef", bytearray(b"abcdef"), memoryview(b"abcdef")])
def test_rejects_non_bytes_frames(raw: object) -> None:
    with pytest.raises(TypeError):
        decode_string_prompt(cast("bytes", raw))


def test_rejects_zero_wire_id() -> None:
    with pytest.raises(ValueError, match="nonzero unsigned 32-bit"):
        decode_string_prompt(struct.pack("<HI", 0x01D4, 0))


@pytest.mark.parametrize("prompt", [True, None, 1, {"npc_id": 1}])
def test_rejects_non_prompt_argument(prompt: object) -> None:
    with pytest.raises(TypeError):
        encode_selected_name(cast("NpcStringPrompt", prompt), "Otto")


def test_prompt_is_frozen() -> None:
    prompt = NpcStringPrompt(1)
    field_name = "npc_id"
    with pytest.raises(FrozenInstanceError):
        setattr(prompt, field_name, 2)
