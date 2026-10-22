"""Full-trace JSONL logging: one append-only history file per persona.

The trace is the agent's COMPLETE session history — heard and sent chat,
decide requests/responses with duration, LLM escalations, world events,
executed actions and bounded state snapshots — written as one JSON object per
line to ``<trace-dir>/<persona>.jsonl``. Lines are FUTURE DECISION INPUT: each
line is self-contained (map + position + payload, never "same as above") so a
later process can reconstruct what happened to the agent or feed the history
to a summarizer.

Storage mirrors the experience journal's privacy model: the directory is
created owner-only (0o700) and the file 0o600, opened via ``dir_fd`` with
``O_NOFOLLOW`` and verified owner-private before use. Logging FAILS OPEN:
write errors are swallowed and counted (:attr:`TraceLog.dropped`); only the
constructor raises, so the runtime can disable tracing with one warning
instead of crashing the agent.

The decide/LLM wrappers are transparent proxies: arguments, return values and
raised exceptions pass through unchanged, with a ``decide_request`` /
``decide_response`` (resp. ``llm_request`` / ``llm_response``) pair logged
around each call. On a backend error the response line carries an ``error``
field and the exception propagates untouched.
"""

import json
import os
import re
import threading
import time
from contextlib import suppress
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, final

from robots.adapters.memory_journal import _open_private_root, _require_private
from robots.domain.actions import PartyChat, Say, WhisperTo
from robots.domain.events import (
    Arrived,
    ChatHeard,
    DamageTaken,
    Heartbeat,
    InviteReceived,
    ItemSeen,
    MonsterSpotted,
    NpcDialogueReceived,
    PlanExpired,
    ScriptFailed,
    TimerFired,
)

PERSONA_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}")
"""Trace file stems are literal persona ids, same rule as the memory journal."""

STATE_TICK_INTERVAL_S = 60.0
"""The bounded snapshot cadence: roughly one state_tick per minute of ticks."""


def chat_channel(action: Any) -> str | None:
    """The chat_sent alias channel for an outbound chat action (else None)."""
    if isinstance(action, Say):
        return "public"
    if isinstance(action, PartyChat):
        return "party"
    if isinstance(action, WhisperTo):
        return "whisper"
    return None


def event_payload(event: Any) -> dict[str, Any]:
    """A self-contained field summary of one WorldEvent (never raises)."""
    payload: dict[str, Any] = {"event": type(event).__name__}
    try:
        if isinstance(event, MonsterSpotted):
            payload["monster"] = event.actor.name
            payload["monster_id"] = event.actor.id
            payload["monster_x"] = event.actor.x
            payload["monster_y"] = event.actor.y
            payload["distance"] = event.actor.distance
            payload["aggressive"] = event.aggressive
        elif isinstance(event, DamageTaken):
            payload["amount"] = event.amount
            payload["from_id"] = event.from_id
        elif isinstance(event, ChatHeard):
            payload["channel"] = event.line.channel
            payload["sender"] = event.line.sender
            payload["message"] = event.line.text
        elif isinstance(event, InviteReceived):
            payload["from"] = event.invite.from_name
            payload["invited_at"] = event.invite.at
        elif isinstance(event, ItemSeen):
            payload["item"] = event.item
            payload["x"] = event.x
            payload["y"] = event.y
        elif isinstance(event, Arrived):
            payload["x"] = event.x
            payload["y"] = event.y
        elif isinstance(event, ScriptFailed):
            payload["reason"] = event.reason
        elif isinstance(event, Heartbeat):
            payload["seq"] = event.seq
        elif isinstance(event, TimerFired):
            payload["timer"] = event.name
            payload["seq"] = event.seq
        elif isinstance(event, PlanExpired):
            payload["plan_id"] = event.plan_id
        elif isinstance(event, NpcDialogueReceived):
            payload["npc_id"] = event.dialogue.npc_id
            payload["stage"] = event.dialogue.stage
        # An unknown future event still traces, at least by type name.
    except AttributeError:  # a partially-formed event still names its type
        pass
    return payload


def action_params(action: Any) -> dict[str, Any]:
    """The action's own fields (shallow; nested values degrade to repr)."""
    try:
        params: dict[str, Any] = {f.name: getattr(action, f.name) for f in fields(action)}
    except TypeError:  # not a dataclass-shaped action
        return {}
    return params


@final
class TraceLog:
    """One persona's append-only JSONL history (owner-private, fails open)."""

    def __init__(self, root: str | Path, persona_id: str) -> None:
        if PERSONA_ID_PATTERN.fullmatch(persona_id) is None:
            msg = "persona_id must be a literal safe identifier"
            raise ValueError(msg)
        self.persona_id = persona_id
        self.path = Path(root) / f"{persona_id}.jsonl"
        self.dropped = 0
        self._lock = threading.Lock()
        self._file: Any = None
        directory = _open_private_root(Path(root))
        try:
            descriptor = os.open(
                self.path.name,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            _require_private(os.fstat(descriptor))
        finally:
            os.close(directory)
        self._file = os.fdopen(descriptor, "a", encoding="utf-8")

    def log(self, kind: str, **payload: Any) -> None:
        """Append one event line; every failure is swallowed and counted."""
        line: dict[str, Any] = {
            "t": datetime.now(UTC).isoformat(),
            "persona": self.persona_id,
            "kind": kind,
            **payload,
        }
        try:
            with self._lock:
                file = self._file
                if file is None:
                    self.dropped += 1
                    return
                file.write(json.dumps(line, default=str) + "\n")
                file.flush()
        except Exception:  # logging must never crash the tick loop
            self.dropped += 1

    def close(self) -> None:
        """Release the file; later writes degrade to the dropped counter."""
        with self._lock:
            file, self._file = self._file, None
            if file is not None:
                with suppress(Exception):
                    file.close()


@final
class TracedDecisionModel:
    """Transparent decide proxy: logs the request/response pair with duration."""

    def __init__(self, model: Any, trace: TraceLog) -> None:
        self._model = model
        self._trace = trace

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self._trace.log("decide_request", request=request)
        started = time.perf_counter()
        try:
            response: dict[str, Any] = self._model.decide(request)
        except BaseException as exc:
            self._trace.log(
                "decide_response",
                duration_s=round(time.perf_counter() - started, 6),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        answers = response.get("answers") if isinstance(response, dict) else None
        self._trace.log(
            "decide_response",
            answers=answers,
            duration_s=round(time.perf_counter() - started, 6),
        )
        return response


@final
class TracedChatGenerator:
    """Transparent chat proxy: logs llm_request/llm_response with duration.

    ``llm_request.messages`` records the escalation prompt as the user
    message; the fixed in-character system prompt (adapters.chat._http) is
    boilerplate identical on every call and is not duplicated per line.
    """

    def __init__(self, chat: Any, trace: TraceLog) -> None:
        self._chat = chat
        self._trace = trace

    def generate_chat(self, prompt: str) -> str:
        self._trace.log("llm_request", messages=[{"role": "user", "content": prompt}])
        started = time.perf_counter()
        try:
            reply: str = self._chat.generate_chat(prompt)
        except BaseException as exc:
            self._trace.log(
                "llm_response",
                duration_s=round(time.perf_counter() - started, 6),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        self._trace.log(
            "llm_response",
            reply=reply,
            duration_s=round(time.perf_counter() - started, 6),
        )
        return reply
