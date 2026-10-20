"""Immutable effective skill observations, never ownership or casting authority."""

from dataclasses import dataclass
from typing import Any

SKILL_BINDING = "e985006171d2/MAIN/pre-re/20180704/received-skills"
MAX_RETAINED_SKILLS = 256


def _integer(value: int, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        message = "invalid received skill integer"
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class EffectiveSkill:
    """Numeric wire fields; absent information stays unknown."""

    id: int
    level: int
    sp: int
    range: int
    up_flag_raw: int
    inf: int | None = None

    def __post_init__(self) -> None:
        _integer(self.id, 1, 65535)
        for value in (self.level, self.sp, self.range):
            _integer(value, 0, 65535)
        _integer(self.up_flag_raw, 0, 255)
        if self.inf is not None:
            _integer(self.inf, -(2**31), 2**31 - 1)

    def fact(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "sp": self.sp,
            "range": self.range,
            "inf": self.inf,
            "up_flag_raw": self.up_flag_raw,
        }


def _require_provenance(epoch: int | None, sequence: int | None) -> None:
    if epoch is None or sequence is None:
        message = "invalid received skill provenance"
        raise ValueError(message)


def _require_rows(rows: tuple[EffectiveSkill, ...]) -> None:
    if (
        type(rows) is not tuple
        or len(rows) > MAX_RETAINED_SKILLS
        or any(type(row) is not EffectiveSkill for row in rows)
        or len({row.id for row in rows}) != len(rows)
    ):
        message = "invalid received skill rows"
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ReceivedSkillContextReadOnly:
    """None means unreceived/invalidated; even a LIST is globally incomplete."""

    rows: tuple[EffectiveSkill, ...] | None = None
    epoch: int | None = None
    sequence: int | None = None

    def __post_init__(self) -> None:
        if self.epoch is not None:
            _integer(self.epoch, 1, 2**63 - 1)
        if self.sequence is not None:
            _integer(self.sequence, 0, 2**63 - 1)
        if self.rows is not None:
            _require_provenance(self.epoch, self.sequence)
            _require_rows(self.rows)

    def decision_facts(self) -> dict[str, Any]:
        rows = self.rows or ()
        return {
            "status": "UNKNOWN" if self.rows is None else "PARTIAL",
            "complete": "UNKNOWN",
            "ownership": "UNKNOWN",
            "casting_legality": "UNKNOWN",
            "binding": SKILL_BINDING,
            "epoch": self.epoch,
            "sequence": self.sequence,
            "observed_count": None if self.rows is None else len(rows),
            "displayed_subset": len(rows) > 8,
            "truncated": len(rows) > 8,
            "rows": [row.fact() for row in rows[:8]],
        }
