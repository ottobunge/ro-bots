"""Ordered encounter capture after the existing gameplay snapshot validation.

This adapter never parses damage, sends or guesses missing telemetry. Its parent
owns transport and full-snapshot continuity; records are current-epoch experience.
"""

from robots.adapters.native_encounter_context import (
    HitHistory,
    ObservedActorSpecies,
    ReceivedSelfLevel,
    build_hit_fact,
    decode_actor_species,
)
from robots.adapters.native_gameplay import ObservedDamage

SELECTION_BINDING = "e985006/MAIN/preRE20180704/CHARACTER_INFO"
LEVEL_BINDING = "e985006/MAIN/preRE20180704/0x00B0/11"


class NativeEncounterStream:
    """One bot's detached bounded facts, joined only at received hit sequence."""

    def __init__(
        self, *, epoch: int, own_actor_id: int, base_seq: int, level: ReceivedSelfLevel | None
    ) -> None:
        self._epoch = epoch
        self._own_actor_id = own_actor_id
        self._cursor = base_seq
        self._level = level
        self._species: dict[int, ObservedActorSpecies] = {}
        self._windows: dict[int, int] = {}
        self._window_start = base_seq
        self._history = HitHistory(epoch=epoch)

    @property
    def records(self) -> tuple[dict[str, int | str | None], ...]:
        return tuple(fact.as_dict() for fact in self._history.records)

    def consume(
        self,
        frames: tuple[tuple[int, float, int, bytes], ...],
        damage: tuple[ObservedDamage, ...],
    ) -> None:
        """Only already-validated frames and already-parsed retained damage."""
        hits = {hit.seq: hit for hit in damage}
        for seq, _, pid, raw in frames:
            if seq <= self._cursor:
                continue
            self._observe_frame(seq, pid, raw)
            if seq in hits:
                self._capture(hits[seq])
            self._cursor = seq

    def _observe_frame(self, seq: int, pid: int, raw: bytes) -> None:
        if pid == 0x0091:
            self._species.clear()
            self._windows.clear()
            self._window_start = seq
        elif pid == 0x0080:
            actor_id = int.from_bytes(raw[2:6], "little")
            self._species.pop(actor_id, None)
            self._windows[actor_id] = seq
        elif pid == 0x00B0 and int.from_bytes(raw[2:4], "little") == 11:
            # Invalid counts replace, never restore, a previously valid capture.
            self._level = ReceivedSelfLevel(
                self._epoch,
                seq,
                int.from_bytes(raw[4:8], "little", signed=True),
                "native_level11",
                LEVEL_BINDING,
            )
        elif pid in (0x09FD, 0x09FE, 0x09FF):
            self._receive_species(seq, raw)

    def _receive_species(self, seq: int, raw: bytes) -> None:
        actor_id = int.from_bytes(raw[5:9], "little")
        self._species.pop(actor_id, None)
        self._windows[actor_id] = seq - 1
        species = decode_actor_species(
            raw, epoch=self._epoch, sequence=seq, own_actor_id=self._own_actor_id
        )
        if species is not None:
            self._species[species.actor_id] = species

    def _capture(self, hit: ObservedDamage) -> None:
        fact = build_hit_fact(
            hit,
            epoch=self._epoch,
            own_actor_id=self._own_actor_id,
            window_start=self._windows.get(hit.target_id, self._window_start),
            species=self._species.get(hit.target_id),
            level=self._level,
        )
        if fact is not None:
            self._history.record(fact)
