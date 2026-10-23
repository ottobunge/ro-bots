"""Per-agent history over the population-live JSONL traces (read-only).

The trace writer (robots.app.trace_log) appends one self-contained JSON
object per line to ``<traces_dir>/<persona_id>.jsonl``. This module reads
those files read-only: it never writes, truncates or locks them. Every read
streams line-by-line with bounded memory (the files grow unboundedly), and
malformed lines are skipped — one bad line never blanks the history.

The persona<->character mapping comes from the host manifest
(``host-manifest.json`` ``accounts[]``: persona_id + char_name); dashboard
agent ids are char ids or char names, so resolution falls back to a
char-name lookup provided by the agent source.
"""

from __future__ import annotations

import json
import re
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_TRACES_DIR = ".work/runtime/population-live/traces"
DEFAULT_HOST_MANIFEST = ".work/runtime/population-live/host-manifest.json"

HISTORY_KINDS_DEFAULT: tuple[str, ...] = (
    "action_executed",
    "world_event",
    "chat_sent",
    "chat_heard",
    "goal_review",
    "plan_authored",
    "decide_response",
)
HISTORY_KINDS_KNOWN: frozenset[str] = frozenset(
    {
        *HISTORY_KINDS_DEFAULT,
        "decide_request",
        "llm_request",
        "llm_response",
        "state_tick",
    }
)
HISTORY_LIMIT_DEFAULT = 200
HISTORY_LIMIT_CAP = 2000
COMBAT_KINDS: frozenset[str] = frozenset({"world_event", "action_executed"})
PLAN_KINDS: frozenset[str] = frozenset({"goal_review", "plan_authored"})
# A monster unseen for this long starts a fresh encounter on its next contact.
ENCOUNTER_GAP_S = 300.0


class InvalidHistoryQuery(ValueError):
    """A history query parameter is malformed (kinds, before cursor)."""


def clamp_limit(limit: int | str, default: int = HISTORY_LIMIT_DEFAULT) -> int:
    """Clamp a query-string limit into ``[1, CAP]``."""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, HISTORY_LIMIT_CAP))


def parse_kinds(raw: str | None) -> tuple[str, ...]:
    """Parse a comma-separated kind list; empty/None means the default set."""
    if raw is None or not raw.strip():
        return HISTORY_KINDS_DEFAULT
    kinds = tuple(k.strip() for k in raw.split(",") if k.strip())
    unknown = [k for k in kinds if k not in HISTORY_KINDS_KNOWN]
    if unknown:
        raise InvalidHistoryQuery(f"unknown trace kind(s): {', '.join(unknown)}")
    return kinds or HISTORY_KINDS_DEFAULT


def parse_before(raw: str | None) -> datetime | None:
    """Parse the ``before`` cursor (ISO-8601); naive values are taken as UTC.

    ``+`` in a timestamp arrives as a space through unencoded query strings
    (curl, hand-built URLs), so a space before a trailing ``HH:MM`` offset is
    retried as ``+`` before the cursor is rejected.
    """
    if raw is None or not raw.strip():
        return None
    candidates = (raw.strip(), re.sub(r" (\d{2}:\d{2}(?::\d+)?)$", r"+\1", raw.strip()))
    for candidate in candidates:
        try:
            moment = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            continue
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return moment
    raise InvalidHistoryQuery(f"invalid before cursor: {raw.strip()}")


def _parse_t(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment


def _compact(value: Any, max_len: int = 120) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def summarize(line: dict[str, Any]) -> dict[str, Any]:
    """Project one trace line to the compact timeline row (summary text)."""
    kind = line.get("kind")
    row: dict[str, Any] = {
        "t": line.get("t"),
        "kind": kind,
        "map": line.get("map"),
        "x": line.get("x"),
        "y": line.get("y"),
        "summary": "",
    }
    if kind == "action_executed":
        row["summary"] = _summarize_action(line)
        row["action"] = line.get("action")
    elif kind == "chat_sent":
        row["summary"] = f"[{line.get('channel', '?')}] {line.get('message', '')}"
        row["channel"] = line.get("channel")
    elif kind == "chat_heard":
        row["summary"] = f"{line.get('speaker', '?')}: {line.get('message', '')}"
        row["channel"] = line.get("channel")
    elif kind == "world_event":
        row["summary"] = _summarize_world_event(line)
        row["event"] = line.get("event")
    elif kind == "goal_review":
        goal, previous = line.get("goal"), line.get("previous_goal")
        arrow = "→" if previous != goal else "="
        row["summary"] = f"{previous} {arrow} {goal} ({line.get('trigger', 'review')})"
        row["goal"] = goal
    elif kind == "plan_authored":
        targets = ", ".join(line.get("targets") or []) or "no targets"
        row["summary"] = (
            f"{line.get('goal', '?')} on {line.get('map', '?')} → {targets} "
            f"({_compact(line.get('duration_s'))}s, {line.get('trigger', 'plan')})"
        )
        row["goal"] = line.get("goal")
        row["targets"] = line.get("targets")
    elif kind == "decide_response":
        row["summary"] = _summarize_decide_response(line)
    else:
        row["summary"] = _compact({k: v for k, v in line.items() if k != "kind"})
    return row


def _summarize_action(line: dict[str, Any]) -> str:
    action = line.get("action", "?")
    params = line.get("params") or {}
    if action == "Attack" and "target_id" in params:
        return f"Attack target {params['target_id']}"
    if action == "MoveTo" and "x" in params:
        return f"MoveTo {line.get('map', '?')} {params.get('x')},{params.get('y')}"
    if action in ("Say", "PartyChat", "WhisperTo"):
        return f"{action}: {_compact(params.get('text', line.get('message', '')))}"
    if action == "InviteToParty" and "player" in params:
        return f"InviteToParty {params['player']}"
    if action == "TalkToNpc" and "npc_id" in params:
        return f"TalkToNpc #{params['npc_id']}"
    return f"{action} {_compact(params)}" if params else action


def _summarize_world_event(line: dict[str, Any]) -> str:
    event = line.get("event", "?")
    if event == "MonsterSpotted":
        return (
            f"spotted {line.get('monster', '?')} (#{line.get('monster_id')}) "
            f"at {line.get('monster_x')},{line.get('monster_y')}"
        )
    if event == "DamageTaken":
        return f"took {line.get('amount', '?')} damage from #{line.get('from_id')}"
    if event == "ChatHeard":
        return _compact(line.get("message", event))
    payload = {
        k: v
        for k, v in line.items()
        if k not in ("t", "persona", "kind", "map", "x", "y", "adjacent_monsters")
    }
    return _compact(payload)


def _summarize_decide_response(line: dict[str, Any]) -> str:
    answers = line.get("answers") or {}
    picks = []
    for name, answer in answers.items():
        choice = answer.get("choice") if isinstance(answer, dict) else answer
        picks.append(f"{name}={choice}")
    text = " ".join(picks) if picks else "no answers"
    duration = line.get("duration_s")
    return f"{text} ({duration}s)" if duration is not None else text


class TraceHistory:
    """Read-only access to one directory of per-agent JSONL traces."""

    def __init__(self, traces_dir: Path | str, manifest_path: Path | str) -> None:
        self.traces_dir = Path(traces_dir)
        self.manifest_path = Path(manifest_path)

    def configured(self) -> bool:
        return self.traces_dir.is_dir()

    def _manifest_names(self) -> dict[str, str]:
        """char_name -> persona_id (best-effort; a missing manifest is empty)."""
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        mapping: dict[str, str] = {}
        for account in manifest.get("accounts") or []:
            persona, char = account.get("persona_id"), account.get("char_name")
            if isinstance(persona, str) and isinstance(char, str):
                mapping[char] = persona
        return mapping

    def trace_path(self, persona: str) -> Path:
        return self.traces_dir / f"{persona}.jsonl"

    def resolve_persona(self, agent_ref: str, char_lookup: Any = None) -> str | None:
        """Map a dashboard agent id (char id, char name or persona id)."""
        names = self._manifest_names()
        for name, persona in names.items():
            if agent_ref in (persona, name):
                return persona
        if self.trace_path(agent_ref).is_file():  # manifest-less direct persona
            return agent_ref
        if char_lookup is not None:
            try:
                char_name = char_lookup(agent_ref)
            except Exception:
                char_name = None
            if char_name is not None:
                persona = names.get(char_name)
                if persona is not None:
                    return persona
        return None

    def _stream(self, persona: str) -> Any:
        """Yield parsed trace lines in file (chronological) order."""
        path = self.trace_path(persona)
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError:
            return
        with handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    line = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(line, dict):
                    yield line

    def history(
        self,
        persona: str,
        kinds: tuple[str, ...] = HISTORY_KINDS_DEFAULT,
        limit: int = HISTORY_LIMIT_DEFAULT,
        before: datetime | None = None,
    ) -> dict[str, Any]:
        """The newest-first bounded timeline (``before`` pages strictly older)."""
        wanted = frozenset(kinds)
        cap = clamp_limit(limit)
        window: deque[dict[str, Any]] = deque(maxlen=cap)
        for line in self._stream(persona):
            if line.get("kind") not in wanted:
                continue
            moment = _parse_t(line.get("t"))
            if before is not None and (moment is None or moment >= before):
                continue
            window.append(summarize(line))
        events = list(window)
        events.reverse()  # file is chronological -> deque tail is the newest
        next_before = events[-1]["t"] if events else None
        return {"events": events, "count": len(events), "limit": cap, "next_before": next_before}

    def combat(self, persona: str) -> dict[str, Any]:
        """Per-monster aggregation: encounters, attacks, damage, first/last seen."""
        buckets: dict[int, dict[str, Any]] = {}

        def bucket(monster_id: int) -> dict[str, Any]:
            record = buckets.get(monster_id)
            if record is None:
                record = {
                    "monster_id": monster_id,
                    "name": None,
                    "encounters": 0,
                    "attacks": 0,
                    "damage_taken": 0,
                    "damage_dealt": 0,
                    "first_seen": None,
                    "last_seen": None,
                    "_last_contact": None,
                }
                buckets[monster_id] = record
            return record

        def contact(record: dict[str, Any], moment: datetime | None) -> None:
            last = record["_last_contact"]
            if last is None or moment is None or (moment - last).total_seconds() > ENCOUNTER_GAP_S:
                record["encounters"] += 1
            record["_last_contact"] = moment
            if moment is not None:
                stamp = moment.isoformat()
                if record["first_seen"] is None or stamp < record["first_seen"]:
                    record["first_seen"] = stamp
                if record["last_seen"] is None or stamp > record["last_seen"]:
                    record["last_seen"] = stamp

        for line in self._stream(persona):
            if line.get("kind") not in COMBAT_KINDS:
                continue
            kind, moment = line.get("kind"), _parse_t(line.get("t"))
            if kind == "world_event":
                event = line.get("event")
                if event == "MonsterSpotted":
                    record = bucket(line.get("monster_id"))
                    record["name"] = line.get("monster") or record["name"]
                    contact(record, moment)
                elif event == "DamageTaken":
                    record = bucket(line.get("from_id"))
                    record["damage_taken"] += int(line.get("amount") or 0)
                    contact(record, moment)
                elif event in ("DamageDealt", "KillCommitted"):
                    target = line.get("to_id") or line.get("monster_id")
                    if target is not None:
                        record = bucket(target)
                        record["damage_dealt"] += int(line.get("amount") or 0)
                        contact(record, moment)
            elif kind == "action_executed" and line.get("action") == "Attack":
                record = bucket(line.get("params", {}).get("target_id"))
                record["attacks"] += 1
                contact(record, moment)

        monsters = []
        for record in buckets.values():
            record.pop("_last_contact", None)
            if record["monster_id"] is None:
                continue
            record["name"] = record["name"] or f"unknown #{record['monster_id']}"
            monsters.append(record)
        monsters.sort(key=lambda m: (-m["encounters"], -m["damage_taken"], m["name"]))
        return {
            "monsters": monsters,
            "engagements": len(monsters),
            "attacks_total": sum(m["attacks"] for m in monsters),
            "damage_taken_total": sum(m["damage_taken"] for m in monsters),
        }

    def plans(self, persona: str, limit: int = HISTORY_LIMIT_DEFAULT) -> dict[str, Any]:
        """The goal_review/plan_authored timeline, newest first."""
        cap = clamp_limit(limit)
        window: deque[dict[str, Any]] = deque(maxlen=cap)
        for line in self._stream(persona):
            if line.get("kind") not in PLAN_KINDS:
                continue
            row = summarize(line)
            row["previous_goal"] = line.get("previous_goal")
            row["trigger"] = line.get("trigger")
            window.append(row)
        plans = list(window)
        plans.reverse()
        return {"plans": plans, "count": len(plans), "limit": cap}
