"""Agent-bound, read-only investigation. All returned text is untrusted data.

Construct one reader per owner. The caller adapts telemetry-unavailable failures
into a current-identity snapshot with state=None, or identity=None if the binding
is unknown. Other exceptions propagate. No native, model, or persistence effects.
"""

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from robots.domain.inventory_context import inventory_capacity_facts
from robots.domain.model import BotState
from robots.domain.planning import Capabilities, PlanningIdentity
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.domain.skills import ReceivedSkillContextReadOnly
from robots.society.memory import ExperienceNote, MemoryLog


def _invalid() -> ValueError:
    return ValueError("invalid investigation cursor, encoding or response budget")


def _validate_skill_id(skill_id: int | None) -> None:
    if skill_id is not None and (type(skill_id) is not int or not 1 <= skill_id <= 65535):
        raise _invalid()


def _validate_options(cursor: int, note_id: int, offset: int, budget: int, query: str) -> None:
    if any(type(v) is not int or v < 0 for v in (cursor, note_id, offset, budget)):
        raise _invalid()
    if not 256 <= budget <= 8192 or not isinstance(query, str):
        raise _invalid()
    try:
        if len(query.encode("utf-8")) > 256:
            raise _invalid()
    except UnicodeEncodeError as error:
        raise _invalid() from error


def _bounded(result: dict[str, Any], budget: int) -> dict[str, Any]:
    if len(serialized_response(result)) <= budget:
        return result
    result.update(
        status="UNAVAILABLE",
        truncated=True,
        data={
            "reason": "response budget",
            "coverage": "omitted; use paginated section topics or larger budget",
        },
    )
    if len(serialized_response(result)) > budget:
        result["data"] = {"reason": "response budget"}
    if len(serialized_response(result)) > budget:
        raise _invalid()
    return result


def _fit_text(
    result: dict[str, Any], target: dict[str, Any], key: str, text: str, offset: int, *, budget: int
) -> int:
    low, high = 0, min(len(text) - offset, budget)
    while low < high:
        size = (low + high + 1) // 2
        target[key] = text[offset : offset + size]
        target["next_offset"] = offset + size
        target["has_more"] = offset + size < len(text)
        result["truncated"] = target["has_more"]
        if len(serialized_response(result)) <= budget:
            low = size
        else:
            high = size - 1
    target[key] = text[offset : offset + low]
    target["next_offset"] = offset + low
    target["has_more"] = offset + low < len(text)
    result["truncated"] = target["has_more"]
    if len(serialized_response(result)) > budget or (low == 0 and offset < len(text)):
        raise _invalid()
    return low


def _read_note(
    result: dict[str, Any],
    notes: tuple[ExperienceNote, ...],
    note_id: int,
    offset: int,
    budget: int,
) -> dict[str, Any]:
    if note_id >= len(notes):
        raise _invalid()
    note = notes[note_id]
    if offset > len(note.text):
        raise _invalid()
    data = {
        "note_id": note_id,
        "kind": note.kind,
        "ts": note.ts,
        "offset": offset,
        "text": "",
        "next_offset": offset,
        "has_more": False,
    }
    result["data"] = data
    _fit_text(result, data, "text", note.text, offset, budget=budget)
    return result


def _append_search_row(
    result: dict[str, Any],
    rows: list[dict[str, Any]],
    note: ExperienceNote,
    index: int,
    budget: int,
) -> bool:
    row = {
        "note_id": index,
        "kind": note.kind,
        "ts": note.ts,
        "snippet": note.text[:80],
        "snippet_truncated": len(note.text) > 80,
    }
    rows.append(row)
    if len(serialized_response(result)) > budget:
        row.update(snippet="", snippet_truncated=bool(note.text))
    if len(serialized_response(result)) > budget:
        rows.pop()
        return False
    return True


def _search_notes(
    result: dict[str, Any], notes: tuple[ExperienceNote, ...], query: str, cursor: int, budget: int
) -> dict[str, Any]:
    """Case-sensitive plain substring; IDs are instance-local append ordinals."""
    if cursor > len(notes):
        raise _invalid()
    rows: list[dict[str, Any]] = []
    data = {
        "rows": rows,
        "source_count": len(notes),
        "scanned": 0,
        "next_cursor": cursor,
        "has_more": cursor < len(notes),
    }
    result["data"] = data
    end = min(cursor + 64, len(notes))
    for index in range(cursor, end):
        if len(rows) == 8:
            break
        note = notes[index]
        if query in note.text and not _append_search_row(result, rows, note, index, budget):
            break
        data.update(
            scanned=index - cursor + 1, next_cursor=index + 1, has_more=index + 1 < len(notes)
        )
    result["truncated"] = data["has_more"] or any(r["snippet_truncated"] for r in rows)
    if data["next_cursor"] == cursor and cursor < len(notes):
        raise _invalid()
    return _bounded(result, budget)


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    """Caller observations, not mechanically verified action permissions."""

    identity: PlanningIdentity | None
    state: BotState | None
    capabilities: Capabilities
    free_skill_points: int | None = None
    free_stat_points: int | None = None


def serialized_response(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )


def _page(rows: list[Any], cursor: int) -> dict[str, Any]:
    if cursor > len(rows):
        raise _invalid()
    end = min(cursor + 8, len(rows))
    return {
        "rows": rows[cursor:end],
        "source_count": len(rows),
        "next_cursor": end,
        "has_more": end < len(rows),
    }


def _skills(state: BotState) -> dict[str, Any]:
    context = state.received_skills or ReceivedSkillContextReadOnly()
    return context.decision_facts()


def _character(snapshot: ObservationSnapshot) -> dict[str, Any]:
    state = snapshot.state
    if state is None:
        return {}
    fields = (
        "name",
        "job",
        "base_level",
        "hp",
        "max_hp",
        "sp",
        "max_sp",
        "map_name",
        "x",
        "y",
        "goal",
        "native_epoch",
        "inventory_known",
        "alive_known",
        "alive",
    )
    result = {field: getattr(state, field) for field in fields}
    result.update(
        dict.fromkeys(
            ("stats", "equipment", "bonuses", "quest_progress", "schedules", "relationships"),
            "UNKNOWN",
        )
    )
    result.update(
        {
            "free_skill_points": snapshot.free_skill_points,
            "free_stat_points": snapshot.free_stat_points,
            "received_effective_skills": _skills(state),
            "inventory": _inventory(state, 0),
            "inventory_capacity": inventory_capacity_facts(state),
            "recent_encounters": _page([dict(r) for r in state.recent_encounters], 0),
            "npc": {
                "available": state.npc_dialogue is not None,
                "read_topic": "npc",
                "instructions_received": state.npc_instructions_received,
            },
        }
    )
    return result


def _inventory(state: BotState, cursor: int) -> dict[str, Any]:
    return _page(
        [
            {"item": k, "quantity": v if state.inventory_known else None}
            for k, v in state.inventory.items()
        ],
        cursor,
    )


def _state_data(state: BotState, topic: str, skill_id: int | None, cursor: int) -> dict[str, Any]:
    if topic == "map":
        return {
            "name": state.map_name,
            "position": [state.x, state.y],
            "perceived_entities": _page([asdict(a) for a in state.nearby], cursor),
            "geometry": "UNKNOWN",
            "other_maps": "UNKNOWN",
            "history": "UNKNOWN",
        }
    if topic == "inventory":
        return {"known": state.inventory_known, **_inventory(state, cursor)}
    if topic == "encounters":
        return _page([dict(r) for r in state.recent_encounters], cursor)
    if topic == "npc":
        return {
            "dialogue": asdict(state.npc_dialogue) if state.npc_dialogue else None,
            "coverage": "received UI only; quest progress UNKNOWN",
        }
    return _received_data(state, topic, skill_id, cursor)


def _received_data(
    state: BotState, topic: str, skill_id: int | None, cursor: int
) -> dict[str, Any]:
    context = state.received_skills or ReceivedSkillContextReadOnly()
    rows = context.rows or ()
    if topic == "received_skills":
        return {**_skills(state), **_page([r.fact() for r in rows], cursor)}
    found = next((r for r in rows if r.id == skill_id), None)
    return {
        "row": found.fact() if found else None,
        "ownership": "UNKNOWN",
        "complete": "UNKNOWN",
        "casting_legality": "UNKNOWN",
        "epoch": context.epoch,
        "sequence": context.sequence,
    }


class InvestigationReader:
    """Instance-local owner binding; not a security boundary against a malicious UID."""

    def __init__(
        self,
        identity: PlanningIdentity,
        provider: Callable[[], ObservationSnapshot],
        public: PublicSkillKnowledge,
        memory: MemoryLog,
    ) -> None:
        self.identity = identity
        self.provider = provider
        self.public = public
        self.memory = memory

    def _snapshot(self, identity: PlanningIdentity) -> ObservationSnapshot | None:
        if identity != self.identity:
            return None
        snapshot = self.provider()
        if snapshot.identity != self.identity:
            return None
        state = snapshot.state
        if (
            state is not None
            and state.native_epoch is not None
            and state.native_epoch != identity.session_epoch
        ):
            return None
        return snapshot

    def observed_capabilities(self, identity: PlanningIdentity) -> Capabilities:
        snapshot = self._snapshot(identity)
        return (
            snapshot.capabilities
            if snapshot
            else Capabilities(frozenset(), frozenset(), frozenset())
        )

    def _rule(self, topic: str) -> dict[str, Any]:
        card = next(
            (
                c
                for c in self.public.cards
                if c.ruleset == self.identity.ruleset
                and self.public.ruleset == self.identity.ruleset
                and topic == f"skill:{c.id}"
            ),
            None,
        )
        return {
            "card": asdict(card) if card else None,
            "ownership": "UNKNOWN",
            "casting_legality": "UNKNOWN",
        }

    def public_rule(self, identity: PlanningIdentity, topic: str) -> str | None:
        result = self.read(identity, "public_rule", rule_topic=topic)
        return (
            serialized_response(result).decode("utf-8")
            if result.get("data", {}).get("card")
            else None
        )

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
        _validate_options(cursor, note_id, offset, max_utf8_bytes, query)
        _validate_skill_id(skill_id)
        snapshot = self._snapshot(identity)
        result: dict[str, Any] = {"status": "DENIED", "data": {}}
        if snapshot is None:
            return result
        result.update(
            {
                "source": "caller_observations",
                "session_epoch": self.identity.session_epoch,
                "ruleset": self.identity.ruleset,
                "untrusted_text": True,
                "truncated": False,
            }
        )
        if topic == "public_rule":
            result.update(status="OK", source="public_advice", data=self._rule(rule_topic))
        elif topic == "character":
            result.update(status="OK" if snapshot.state else "UNKNOWN", data=_character(snapshot))
        elif topic in (
            "map",
            "inventory",
            "encounters",
            "npc",
            "received_skill",
            "received_skills",
        ):
            result.update(
                status="OK" if snapshot.state else "UNKNOWN",
                data=_state_data(snapshot.state, topic, skill_id, cursor) if snapshot.state else {},
            )
        elif topic in ("memory_search", "memory_read"):
            result.update(status="OK", source="stored experience text")
            notes = self.memory.notes()
            if topic == "memory_read":
                return _read_note(result, notes, note_id, offset, max_utf8_bytes)
            return _search_notes(result, notes, query, cursor, max_utf8_bytes)
        return _bounded(result, max_utf8_bytes)
