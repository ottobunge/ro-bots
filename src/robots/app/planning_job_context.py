"""Host-owned advisory investigation capture; never admission authority."""

import json
from copy import deepcopy
from dataclasses import fields, is_dataclass
from typing import Any

from robots.app.planning_context import InvestigationReader, ObservationSnapshot
from robots.domain.planning import PlanningIdentity
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.society.memory import MemoryLog, StubSummarizer


def _schema_value(value: object) -> object:
    """Encode typed report data without normalizing model arguments."""
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    if isinstance(value, frozenset) and len(value) <= 32768:
        return sorted(value)
    message = "invalid job capture schema"
    raise TypeError(message)


def _fits_job(payload: object) -> bool:
    encoder = json.JSONEncoder(
        ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=_schema_value
    )
    remaining = 32768
    try:
        for part in encoder.iterencode(payload):
            if len(part) > remaining:
                return False
            remaining -= len(part.encode("utf-8"))
            if remaining < 0:
                return False
    except TypeError, ValueError, UnicodeEncodeError:
        return False
    return True


class CapturedInvestigationReader(InvestigationReader):
    """A job-local reader, including explicit unavailable private coverage."""

    def __init__(
        self,
        identity: PlanningIdentity,
        snapshot: ObservationSnapshot,
        public: PublicSkillKnowledge,
        memory: MemoryLog,
        *,
        memory_known: bool,
    ) -> None:
        super().__init__(identity, lambda: snapshot, public, memory)
        self._memory_known = memory_known

    def read(
        self,
        identity: PlanningIdentity,
        topic: str,
        *,
        skill_id: int | None = None,
        rule_topic: str = "",
        cursor: int = 0,
        query: str = "",
        note_id: int = 0,
        offset: int = 0,
        max_utf8_bytes: int = 4096,
    ) -> dict[str, Any]:
        unknown = not self._memory_known and topic in ("memory_search", "memory_read")
        result = super().read(
            identity,
            "unknown_memory" if unknown else topic,
            skill_id=skill_id,
            rule_topic=rule_topic,
            cursor=cursor,
            query=query,
            note_id=note_id,
            offset=offset,
            max_utf8_bytes=max_utf8_bytes,
        )
        if unknown and identity == self.identity:
            result.update(status="UNKNOWN", source="stored experience text", data={})
        return deepcopy(result)


def _owner_bound(identity: PlanningIdentity, snapshot: ObservationSnapshot) -> bool:
    state = snapshot.state
    return snapshot.identity == identity and (
        state is None or state.native_epoch in (None, identity.session_epoch)
    )


def capture_job_context(
    identity: PlanningIdentity,
    snapshot: ObservationSnapshot,
    public: PublicSkillKnowledge,
    memory: MemoryLog,
) -> InvestigationReader | None:
    """Own independent observations and private raw experience for one job."""
    if not _owner_bound(identity, snapshot):
        return None
    payload = {"identity": identity, "snapshot": snapshot, "public": public, "notes": None}
    if not _fits_job(payload):
        return None
    notes = memory.capture_raw_notes()
    if notes is not None and any(type(note.ts) not in (int, float) for note in notes):
        return None
    payload["notes"] = notes
    if not _fits_job(payload):
        return None
    owned_snapshot = deepcopy(snapshot)
    owned_memory = MemoryLog(StubSummarizer())
    for note in notes or ():
        owned_memory.append(note)
    return CapturedInvestigationReader(
        identity, owned_snapshot, deepcopy(public), owned_memory, memory_known=notes is not None
    )
