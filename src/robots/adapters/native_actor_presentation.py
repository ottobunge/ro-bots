"""Presentation-only actor metadata for MAIN/pre-renewal PACKETVER 20180704.

Wire presentation is non-injective: it does not prove native identity, pose,
range, freshness, or permission to attack. Names are received presentation only.

Authority: native-actor-classification-frontier.json; pinned rAthena e985006171d2,
packets_struct.hpp:687-904 compiled sizeof/offsetof oracle and clif.cpp:344-385.
MAIN shield guard >=20181121 is inactive for this bounded profile. Type 0 can
represent PC-sprite mobs/pets/walking NPCs; type 5 can represent disguised SELF.
"""

import struct
from dataclasses import dataclass
from enum import Enum


class ActorPresentationKind(Enum):
    """Labels deliberately distinct from domain actor kinds."""

    PLAYER_PRESENTATION = "player_presentation"
    MONSTER_PRESENTATION = "monster_presentation"
    NPC_PRESENTATION = "npc_presentation"


@dataclass(frozen=True)
class NativeActorPresentation:
    """Wire actor ID and character ID are separate unsigned header fields."""

    packet_id: int
    actor_id: int
    character_id: int
    objecttype: int
    presentation_kind: ActorPresentationKind | None


def presentation_kind(value: object) -> ActorPresentationKind | None:
    """Classify presentation only; never establish true native identity."""
    if type(value) is not int or not 0 <= value <= 255:
        return None
    if value in (6, 12):
        return ActorPresentationKind.NPC_PRESENTATION
    if value == 0:
        return ActorPresentationKind.PLAYER_PRESENTATION
    if value == 5:
        return ActorPresentationKind.MONSTER_PRESENTATION
    return None


def parse_actor_presentation(raw: bytes) -> NativeActorPresentation:
    """Decode the actor presentation header without decoding pose or name."""
    error = "Invalid native actor presentation frame"
    if type(raw) is not bytes or len(raw) < 4:
        raise ValueError(error)
    packet_id = int.from_bytes(raw[:2], "little")
    declared_length = int.from_bytes(raw[2:4], "little")
    expected_length = {0x09FD: 110, 0x09FE: 103, 0x09FF: 104}.get(packet_id)
    if expected_length is None or len(raw) != expected_length or declared_length != expected_length:
        raise ValueError(error)
    packet_id, _, objecttype, actor_id, character_id = struct.unpack_from("<HHBII", raw)
    return NativeActorPresentation(
        packet_id, actor_id, character_id, objecttype, presentation_kind(objecttype)
    )


def actor_entry_npc_name(raw: bytes) -> str | None:
    """Received NPC presentation name, not identity or interaction authority.

    Qualified packets_struct.hpp:754/828/900 ends each packed entry with
    name[NAME_LENGTH]; common/mmo.hpp:154 defines NAME_LENGTH as 23 + 1.
    Exact profile lengths are validated by the existing header decoder.
    Match 0ADF's strict UTF-8/nonempty, first-NUL name policy.
    """
    presentation = parse_actor_presentation(raw)
    if presentation.presentation_kind is not ActorPresentationKind.NPC_PRESENTATION:
        return None
    try:
        name = raw[-24:].split(b"\0", 1)[0].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return name or None
