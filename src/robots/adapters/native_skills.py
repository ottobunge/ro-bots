"""Pinned MAIN/pre-re 20180704 read-only receipt decoder and bounded retention.

Layouts measured from unchanged configured full headers (GCC and Clang).
No transport, inference, database or actuation dependencies.
"""

import math
import struct
from dataclasses import dataclass, replace

from robots.domain.skills import (
    MAX_RETAINED_SKILLS,
    EffectiveSkill,
    ReceivedSkillContextReadOnly,
)

SKILL_PACKETS = frozenset((0x010F, 0x0111, 0x010E, 0x07E1))


@dataclass(frozen=True, slots=True)
class SkillReceipt:
    """Raw legacy names are opaque bytes, not canonical labels."""

    skill: EffectiveSkill
    name: bytes | None


def _full_row(raw: bytes) -> SkillReceipt:
    skill_id, inf, level, sp, reach, name, flag = struct.unpack("<HiHHH24sB", raw)
    return SkillReceipt(EffectiveSkill(skill_id, level, sp, reach, flag, inf), name)


def decode_skills(pid: int, raw: bytes) -> tuple[SkillReceipt, ...]:
    """Validate one already-framed supported packet, rejecting ambiguity."""
    _require_receipt(pid, raw)
    if pid == 0x010F:
        rows = _list_rows(raw)
    elif pid == 0x0111:
        if len(raw) != 39:
            message = "malformed skill add"
            raise ValueError(message)
        rows = (_full_row(raw[2:]),)
    else:
        rows = (_update_row(pid, raw),)
    if len({row.skill.id for row in rows}) != len(rows):
        message = "ambiguous duplicate skill id"
        raise ValueError(message)
    return rows


def _require_receipt(pid: int, raw: bytes) -> None:
    if type(pid) is not int or type(raw) is not bytes or len(raw) < 2:
        message = "malformed skill receipt"
        raise ValueError(message)
    if pid not in SKILL_PACKETS or int.from_bytes(raw[:2], "little") != pid:
        message = "unsupported skill receipt"
        raise ValueError(message)


def _list_rows(raw: bytes) -> tuple[SkillReceipt, ...]:
    if len(raw) < 4 or len(raw) > 8192 or (len(raw) - 4) % 37:
        message = "malformed skill list"
        raise ValueError(message)
    if struct.unpack_from("<h", raw, 2)[0] != len(raw):
        message = "mismatched skill list length"
        raise ValueError(message)
    return tuple(_full_row(raw[i : i + 37]) for i in range(4, len(raw), 37))


def _update_row(pid: int, raw: bytes) -> SkillReceipt:
    layout = struct.Struct("<HHHHHB" if pid == 0x010E else "<HHiHHHB")
    if len(raw) != layout.size:
        message = "malformed skill update"
        raise ValueError(message)
    values = layout.unpack(raw)
    inf = None if pid == 0x010E else values[2]
    level, sp, reach, flag = values[-4:]
    return SkillReceipt(EffectiveSkill(values[1], level, sp, reach, flag, inf), None)


class NativeSkillContext:
    """One session collector, consumed only after the runtime's continuity guard."""

    def __init__(self, epoch: int, base: int) -> None:
        self.context = ReceivedSkillContextReadOnly(epoch=epoch, sequence=base)
        self._cursor = base
        self._blocked = False
        self._rows: dict[int, SkillReceipt] = {}

    def invalidate(self, *, blocked: bool = True) -> None:
        self._rows.clear()
        self._blocked = blocked
        self.context = ReceivedSkillContextReadOnly(epoch=self.context.epoch, sequence=self._cursor)

    def consume(self, frame: tuple[int, float, int, bytes]) -> None:
        seq, at, pid, raw = frame
        if (
            type(seq) is not int
            or type(pid) is not int
            or seq != self._cursor + 1
            or type(at) not in (int, float)
            or not math.isfinite(at)
        ):
            self.invalidate()
            return
        self._cursor = seq
        if pid in (0x0091, 0x0092, 0x0AC7):
            self.invalidate(blocked=False)
        elif pid == 0x0441:
            self.invalidate()
        elif pid in SKILL_PACKETS and not self._blocked:
            self._receive(pid, raw)

    def _receive(self, pid: int, raw: bytes) -> None:
        try:
            rows = decode_skills(pid, raw)
        except ValueError:
            self.invalidate()
            return
        retained = {} if pid == 0x010F else dict(self._rows)
        for row in rows:
            old = retained.get(row.skill.id)
            current = row
            if old is not None and pid in (0x010E, 0x07E1):
                current = SkillReceipt(
                    replace(row.skill, inf=old.skill.inf) if pid == 0x010E else row.skill,
                    old.name,
                )
            retained[row.skill.id] = current
        if len(retained) > MAX_RETAINED_SKILLS:
            self.invalidate()
            return
        self._rows = retained
        self.context = ReceivedSkillContextReadOnly(
            tuple(row.skill for _, row in sorted(retained.items())),
            self.context.epoch,
            self._cursor,
        )
