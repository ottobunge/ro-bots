"""Pure NPC string input for pinned e985006171d2 MAIN/pre-re20180704.

A prompt is received metadata, NOT actor ownership or interaction authority.
The caller must bind the exact selected-character name and valid string intent.
UTF-8 is this project's binding policy, not a universal client/server charset.
"""

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class NpcStringPrompt:
    """Opaque unsigned NPC ID bits from an already-framed string prompt."""

    npc_id: int

    def __post_init__(self) -> None:
        if type(self.npc_id) is not int:
            msg = "NPC ID must be a plain int"
            raise TypeError(msg)
        if not 1 <= self.npc_id <= 0xFFFFFFFF:
            msg = "NPC ID must be nonzero unsigned 32-bit bits"
            raise ValueError(msg)


def decode_string_prompt(raw: bytes) -> NpcStringPrompt:
    """Decode only the packed six-byte ZC_OPEN_EDITDLGSTR (0x01D4)."""
    if type(raw) is not bytes:
        msg = "String prompt must be bytes"
        raise TypeError(msg)
    if len(raw) != 6:
        msg = "String prompt must be exactly six bytes"
        raise ValueError(msg)
    header, npc_id = struct.unpack("<HI", raw)
    if header != 0x01D4:
        msg = "Not a supported string prompt"
        raise ValueError(msg)
    return NpcStringPrompt(npc_id)


def encode_selected_name(prompt: NpcStringPrompt, name: str) -> bytes:
    """Encode exact UTF-8 bytes, without a wire NUL, for the active handler.

    packets.hpp1844-1850 defines the eight-byte prefix. clif.cpp13385-13394
    adds one to payload length; safestrncpy reserves that extra destination
    byte for NUL. Store unsigned ID bits unchanged despite the signed GID field.
    This is representation only, not a server-side valid-NPC or name oracle.
    """
    if type(prompt) is not NpcStringPrompt:
        msg = "Expected a validated string prompt"
        raise TypeError(msg)
    if type(name) is not str:
        msg = "Selected name must be a string"
        raise TypeError(msg)
    try:
        value = name.encode("utf-8")
    except UnicodeEncodeError as exc:
        msg = "Selected name must be valid UTF-8"
        raise ValueError(msg) from exc
    if not 1 <= len(value) <= 23 or b"\0" in value:
        msg = "Selected name must contain 1..23 UTF-8 bytes without NUL"
        raise ValueError(msg)
    return struct.pack("<HHI", 0x01D5, 8 + len(value), prompt.npc_id) + value
