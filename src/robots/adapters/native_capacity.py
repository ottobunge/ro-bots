"""Owner-local historical SELF capacity from qualified retained receive frames."""

import math
import sys
from dataclasses import replace
from typing import Any

from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.domain.capacity import ReceivedCapacity, ReceivedCapacityValue


def finite_capacity_time(value: float) -> bool:
    return type(value) in (int, float) and 0 <= value <= sys.float_info.max and math.isfinite(value)


def _positive_integer(value: object) -> bool:
    return type(value) is int and 0 < value <= 0x7FFFFFFFFFFFFFFF


def _valid_frame(frame: tuple[int, float, int, bytes]) -> bool:
    seq, at, pid, raw = frame
    if not all(
        (
            _positive_integer(seq),
            finite_capacity_time(at),
            type(pid) is int and 0 <= pid <= 0xFFFF,
            type(raw) is bytes,
        )
    ):
        return False
    return (
        len(raw) >= 2
        and int.from_bytes(raw[:2], "little") == pid
        and (pid != 0xB0 or len(raw) == 8)
    )


class NativeCapacityContext:
    """Separate history from spend freshness; no callbacks or effects in DTOs."""

    def __init__(self) -> None:
        self.receipt: ReceivedCapacity | None = None
        self._binding: tuple[object, ...] | None = None
        self._identity: tuple[Any, ...] | None = None
        self._cursor = 0
        self._blocked = False
        self._sampled_at: float | None = None
        self.owner_replaced = False

    def replaces_owner(self, binding: tuple[object, ...], epoch: object) -> bool:
        """Reference replacement is not scalar selection eligibility loss."""
        return (
            self._binding is not None
            and self._identity is not None
            and self._identity[0] == epoch
            and not all(a is b for a, b in zip(self._binding, binding, strict=True))
        )

    @property
    def weight(self) -> ReceivedCapacityValue | None:
        return self.receipt.weight if self.receipt is not None else None

    @property
    def max_weight(self) -> ReceivedCapacityValue | None:
        return self.receipt.max_weight if self.receipt is not None else None

    @property
    def weight_count(self) -> int | None:
        return self.weight.value if self.weight is not None else None

    @property
    def max_weight_count(self) -> int | None:
        return self.max_weight.value if self.max_weight is not None else None

    def invalidate(self) -> None:
        self.receipt = None
        self._blocked = True

    def _bind(
        self,
        binding: tuple[object, ...],
        identity: tuple[Any, ...],
        base: int,
        tail: int,
    ) -> None:
        changed = self._binding is not None and not all(
            a is b for a, b in zip(self._binding, binding, strict=True)
        )
        if changed or (self._identity is not None and self._identity != identity):
            self.invalidate()
        fresh_epoch = self._identity is None or self._identity[0] != identity[0]
        if fresh_epoch:
            self._cursor = base
        if self._blocked:
            self._cursor = base if fresh_epoch else tail
        self._blocked = False
        self._binding, self._identity = binding, identity

    @staticmethod
    def _selected(binding: tuple[object, ...], identity: tuple[Any, ...]) -> bool:
        epoch, character, aid, gid, selection, map_epoch = identity
        selected = binding[-1]
        if not all(_positive_integer(v) for v in (epoch, aid, gid, selection, map_epoch)):
            return False
        return all(
            (
                epoch == selection == map_epoch,
                type(character) is str and bool(character),
                type(selected) is SelectedCharacterSnapshot
                and type(selected.raw_char_id) is int
                and selected.raw_char_id == gid,
                aid <= 0xFFFFFFFF and gid <= 0xFFFFFFFF,
            )
        )

    def observe(
        self,
        binding: tuple[object, ...],
        identity: tuple[Any, ...],
        base: int,
        frames: tuple[tuple[int, float, int, bytes], ...],
        now: float,
    ) -> bool:
        self.owner_replaced = self.replaces_owner(binding, identity[0])
        if not self._valid_clock(now):
            self.invalidate()
            return True  # Capacity is unknown; retain existing NPC clock-denial policy.
        if not self._valid_snapshot(identity, base, frames):
            self.invalidate()
            return False
        self._bind(binding, identity, base, frames[-1][0] if frames else base)
        if not self._selected(binding, identity):
            self.invalidate()
            return True  # Eligibility loss is not a raw-frame continuity fault.
        if self._cursor < base:
            self.invalidate()
            return False
        for frame in frames:
            sequence = frame[0]
            if sequence > self._cursor:
                if sequence - self._cursor != 1:
                    self.invalidate()
                    return False
                self._consume(frame, identity, now)
                self._cursor = sequence
        self._sampled_at = now
        if self.receipt is not None:
            self.receipt = replace(self.receipt, sampled_at=now)
        return True

    def _valid_clock(self, now: float) -> bool:
        return finite_capacity_time(now) and (self._sampled_at is None or now >= self._sampled_at)

    def _valid_snapshot(
        self,
        identity: tuple[Any, ...],
        base: int,
        frames: tuple[tuple[int, float, int, bytes], ...],
    ) -> bool:
        if not all(
            (
                type(base) is int and 0 <= base <= 0x7FFFFFFFFFFFFFFF,
                _positive_integer(identity[0]),
            )
        ):
            return False
        previous = base
        for frame in frames:
            if not _valid_frame(frame):
                return False
            if frame[0] <= previous and previous > self._cursor:
                return False
            previous = frame[0]
        return True

    def _consume(
        self,
        frame: tuple[int, float, int, bytes],
        identity: tuple[Any, ...],
        now: float,
    ) -> None:
        seq, at, pid, raw = frame
        if pid == 0xB0 and int.from_bytes(raw[2:4], "little") in (24, 25):
            if at > now:
                self.invalidate()
                return
            epoch, character, aid, gid, selection, map_epoch = identity
            receipt = self.receipt or ReceivedCapacity(
                epoch, character, aid, gid, selection, map_epoch, now
            )
            value = ReceivedCapacityValue(int.from_bytes(raw[4:8], "little", signed=True), seq, at)
            self.receipt = (
                replace(receipt, weight=value)
                if int.from_bytes(raw[2:4], "little") == 24
                else replace(receipt, max_weight=value)
            )
        elif pid in (0x0A37, 0x00AF, 0x07FA, 0x0991, 0x0A0D) and self.receipt is not None:
            self.receipt = replace(self.receipt, inventory_changed_sequence=seq)
