"""Received NPC UI facts, never quest, reward or equipment authority."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NpcDialogue:
    npc_id: int
    epoch: int
    map_name: str
    opened_sequence: int
    sequence: int
    stage: str
    pages: tuple[str, ...] = ()
    options: tuple[tuple[int, str], ...] = ()
