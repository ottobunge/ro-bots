"""Pure received encounter facts for e985 MAIN/pre-re20180704 only.

No transport, actuation, world population or current-instance stat authority.
Callers must supply reviewed, contiguous received snapshots and clear joins on
vanish/map/gap/session boundaries. Provenance is preserved, not authenticated.
Actor job is signed int16@23, not uint16: fresh unchanged full-header GCC/Clang
oracles are recorded in playing-mvp-native-encounter-context-fix.json.
"""

import json
import struct
from dataclasses import asdict, dataclass
from typing import Literal

from robots.adapters.native_actor_presentation import parse_actor_presentation
from robots.adapters.native_gameplay import ObservedDamage


@dataclass(frozen=True)
class ObservedActorSpecies:
    epoch: int
    sequence: int
    actor_id: int
    species_id: int


def decode_actor_species(
    raw: bytes, *, epoch: int, sequence: int, own_actor_id: int
) -> ObservedActorSpecies | None:
    """Complete accepted actor family, type5, never SELF or its disguise alias."""
    _require_uint(epoch, 0x7FFFFFFFFFFFFFFF, positive=True)
    _require_uint(sequence, 0x7FFFFFFFFFFFFFFF, positive=True)
    _require_uint(own_actor_id, 0xFFFFFFFF, positive=True)
    presentation = parse_actor_presentation(raw)
    species_id = struct.unpack_from("<h", raw, 23)[0]
    if (
        presentation.objecttype != 5
        or presentation.actor_id in (own_actor_id, (-own_actor_id) & 0xFFFFFFFF)
        or species_id <= 0
    ):
        return None
    return ObservedActorSpecies(epoch, sequence, presentation.actor_id, species_id)


@dataclass(frozen=True)
class ReceivedSelfLevel:
    """Caller-captured received level; binding names the reviewed source/profile.

    selection means epoch-bound selected-character baseline (sequence zero), not
    persona or SQL. native_level11 means the actual SELF B0 parameter11 receipt.
    """

    epoch: int
    sequence: int
    level: int
    source: Literal["native_level11", "selection"]
    binding: str


@dataclass(frozen=True)
class ObservedHitFact:
    epoch: int
    sequence: int
    actor_id: int
    damage: int
    damage2: int
    species_id: int | None
    species_sequence: int | None
    self_level_then: int | None
    level_sequence: int | None
    level_source: str | None
    level_binding: str | None

    def as_dict(self) -> dict[str, int | str | None]:
        """Stable scalar order; null is uncaptured, never guessed current state."""
        return asdict(self)


def build_hit_fact(
    damage: ObservedDamage,
    *,
    epoch: int,
    own_actor_id: int,
    window_start: int,
    species: ObservedActorSpecies | None = None,
    level: ReceivedSelfLevel | None = None,
) -> ObservedHitFact | None:
    """Capture at damage receipt, not by replay-joining latest observations.

    window_start is the last actor/gap/vanish boundary sequence. Caller owns
    received provenance and transport health; this function does not prove them.
    """
    _require_uint(epoch, 0x7FFFFFFFFFFFFFFF, positive=True)
    _require_uint(own_actor_id, 0xFFFFFFFF, positive=True)
    _require_uint(window_start, 0x7FFFFFFFFFFFFFFF)
    _require_uint(damage.seq, 0x7FFFFFFFFFFFFFFF, positive=True)
    if not _eligible_damage(damage, own_actor_id) or not window_start < damage.seq:
        return None
    if species is not None and not _species_at_hit(species, epoch, damage, window_start):
        species = None
    if level is not None and not _level_at_hit(level, epoch, damage.seq):
        level = None
    return _capture_fact(epoch, damage, species, level)


def _capture_fact(
    epoch: int,
    damage: ObservedDamage,
    species: ObservedActorSpecies | None,
    level: ReceivedSelfLevel | None,
) -> ObservedHitFact:
    return ObservedHitFact(
        epoch,
        damage.seq,
        damage.target_id,
        damage.damage,
        damage.damage2,
        species.species_id if species else None,
        species.sequence if species else None,
        level.level if level else None,
        level.sequence if level else None,
        level.source if level else None,
        level.binding if level else None,
    )


def _require_uint(value: int, maximum: int, *, positive: bool = False) -> None:
    if type(value) is not int or not int(positive) <= value <= maximum:
        message = "Invalid exact received cursor or identity"
        raise ValueError(message)


def _eligible_damage(damage: ObservedDamage, own_actor_id: int) -> bool:
    amounts = (damage.damage, damage.damage2)
    return all(
        (
            all(type(value) is int and 0 <= value <= 0x7FFFFFFF for value in amounts),
            max(amounts) > 0,
            type(damage.source_id) is int and damage.source_id == own_actor_id,
            type(damage.target_id) is int and 0 < damage.target_id <= 0xFFFFFFFF,
            damage.target_id not in (own_actor_id, (-own_actor_id) & 0xFFFFFFFF),
            damage.is_sp_damage is False,
            type(damage.damage_type) is int and 0 <= damage.damage_type <= 255,
            damage.damage_type not in (2, 3),
        )
    )


def _species_at_hit(
    species: ObservedActorSpecies, epoch: int, damage: ObservedDamage, window_start: int
) -> bool:
    scalars = (species.epoch, species.sequence, species.actor_id, species.species_id)
    return (
        all(type(value) is int for value in scalars)
        and species.epoch == epoch
        and species.actor_id == damage.target_id
        and window_start < species.sequence <= damage.seq
        and 0 < species.species_id <= 32767
    )


def _level_at_hit(level: ReceivedSelfLevel, epoch: int, sequence: int) -> bool:
    return (
        type(level.epoch) is int
        and level.epoch == epoch
        and type(level.sequence) is int
        and 0 <= level.sequence <= sequence
        and type(level.level) is int
        and 0 < level.level <= 0x7FFFFFFF
        and _level_source_valid(level)
    )


def _level_source_valid(level: ReceivedSelfLevel) -> bool:
    return (
        level.source in ("native_level11", "selection")
        and type(level.binding) is str
        and bool(level.binding)
        and (level.source == "selection" or level.sequence > 0)
    )


class HitHistory:
    """Last received hits, not current actor associations or an instance cache.

    No equal-ID joins are performed. Vanish invalidates the caller's species
    window, not immutable experience. Reset clears the entire epoch history.
    Budget includes all scalar provenance in the compact UTF8 JSON rendering.
    """

    def __init__(self, *, epoch: int) -> None:
        self.reset(epoch=epoch)

    def reset(self, *, epoch: int) -> None:
        _require_uint(epoch, 0x7FFFFFFFFFFFFFFF, positive=True)
        self._epoch = epoch
        self._cursor = 0
        self._records: tuple[ObservedHitFact, ...] = ()

    @property
    def records(self) -> tuple[ObservedHitFact, ...]:
        return self._records

    def record(self, fact: ObservedHitFact) -> bool:
        """Return whether retained; ignore duplicate, old or foreign receipts.

        A valid newer same-epoch receipt consumes its cursor after successful
        byte evaluation, even if oversized. Dropping it preserves prior records.
        """
        if fact.epoch != self._epoch or fact.sequence <= self._cursor:
            return False
        pending = (*self._records, fact)[-8:]
        while pending and _history_bytes(pending) > 2048:
            pending = pending[1:]
        self._cursor = fact.sequence
        if not pending:
            return False
        self._records = pending
        return True


def _history_bytes(records: tuple[ObservedHitFact, ...]) -> int:
    return len(
        json.dumps(
            [record.as_dict() for record in records],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
