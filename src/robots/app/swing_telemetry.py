"""Cached conversion observations; no wire reads, logging, or gameplay decisions."""

from collections import deque
from dataclasses import asdict
from typing import Any
from uuid import uuid4

from robots.adapters.native_gameplay import NativeGameplayView


class SwingTelemetry:
    def __init__(self) -> None:
        self._rows: deque[dict[str, Any]] = deque(maxlen=4096)
        self._xp: dict[int, int] = {}
        self._dropped = 0
        self._epoch: int | None = None
        self._session = uuid4().hex

    def note(self, event: str, **fields: Any) -> None:
        if len(self._rows) == self._rows.maxlen:
            self._dropped += 1
        self._rows.append(
            {"event": event, "epoch": self._epoch, "session": self._session, **fields}
        )

    def drain(self) -> tuple[dict[str, Any], ...]:
        rows = tuple(self._rows)
        if self._dropped:
            rows += ({"event": "telemetry_gap", "epoch": self._epoch, "dropped": self._dropped},)
            self._dropped = 0
        self._rows.clear()
        return rows

    def receive(
        self,
        frame: tuple[int, float, int, bytes],
        view: NativeGameplayView,
        *,
        epoch: int,
        own_id: int,
        species: dict[int, str],
    ) -> None:
        if epoch != self._epoch:
            self._xp.clear()
            self._epoch = epoch
            self.note("session")
        seq, at, pid, raw = frame
        context = {"sequence": seq, "at": at, "own_id": own_id}
        if pid == 0x08C8:
            for hit in view.damage:
                if hit.seq == seq and hit.damage_type not in (2, 3):
                    fields = asdict(hit)
                    fields.pop("seq")
                    self.note(
                        "damage",
                        **(context | fields),
                        species=str(species.get(hit.target_id, "unknown")),
                    )
        elif pid == 0x0080 and raw[6] == 1:
            self.note("death", **context, target_id=int.from_bytes(raw[2:6], "little"))
        elif pid in (0x00B0, 0x00B1, 0x0ACB):
            self._exp(raw, context)

    def _exp(self, raw: bytes, context: dict[str, Any]) -> None:
        parameter = int.from_bytes(raw[2:4], "little")
        if parameter not in (1, 2):
            return
        value = int.from_bytes(raw[4:], "little", signed=True)
        previous = self._xp.get(parameter)
        self._xp[parameter] = value
        self.note(
            "exp",
            **context,
            parameter=parameter,
            value=value,
            delta=None if previous is None else value - previous,
        )
