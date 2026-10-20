"""Host command admission and worker status; a send return is not a server ACK.

IDs deduplicate only while retained in this process: pending/in-flight requests
plus the latest 256 terminal results. Evicted IDs may execute again; restart
forgets all IDs. Never retry an uncertain retained ID under a different ID
without operator investigation. Statuses are not server acknowledgements.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


class CommandDispatcher(Protocol):
    def submit(self, command: dict[str, Any]) -> dict[str, Any]: ...

    def status(self, command_id: str) -> dict[str, Any]: ...


class HostCommandError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code


class ChatTarget(Protocol):
    @property
    def online(self) -> bool: ...

    @property
    def stop_flag(self) -> bool: ...

    @property
    def client(self) -> Any: ...


def _available(target: ChatTarget | None) -> bool:
    if target is None or not target.online or target.stop_flag or target.client is None:
        return False
    client = target.client
    return bool(getattr(client, "connected_map", getattr(client, "connected", True)))


def _validate(command: dict[str, Any]) -> tuple[str, str, str]:
    if command.keys() - {"type", "action", "command_id", "persona_id", "args"}:
        raise HostCommandError(400, "unexpected host chat command fields")
    if command.get("type") != "force_action" or command.get("action") != "chat":
        raise HostCommandError(400, "host supports only force_action action=chat")
    command_id = _string(command, "command_id")
    persona_id = _string(command, "persona_id")
    text = _string(command, "args")
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", command_id) is None:
        raise HostCommandError(400, "required command_id must match [A-Za-z0-9_-]{1,128}")
    if any(unicodedata.category(char).startswith("C") for char in text):
        raise HostCommandError(400, "chat control characters are forbidden")
    return command_id, persona_id, text


def _string(command: dict[str, Any], field: str) -> str:
    value = command.get(field)
    if not isinstance(value, str) or not value.strip():
        raise HostCommandError(400, f"{field} must be a nonempty string")
    return value


@dataclass
class ChatRequest:
    command_id: str
    persona_id: str
    text: str
    ts: float
    status: str = "queued"
    phase: str = "pending"
    error_class: str | None = None
    audit_error_class: str | None = None

    def payload(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "kind": "force",
            "summary": f"operator chat {self.status}",
            "operator_forced": True,
            "command_id": self.command_id,
            "persona_id": self.persona_id,
            "status": self.status,
            "delivery_confirmation": False,
            "idempotency_scope": "retained_process_lifetime",
            "terminal_retention": 256,
            "phase": self.phase,
            "error_class": self.error_class,
            "audit_error_class": self.audit_error_class,
        }


class HostChatCommands:
    """Short locked state transitions; transport and memory remain worker-owned."""

    def __init__(self, agents: Mapping[str, ChatTarget]) -> None:
        self._agents = agents
        self._lock = threading.Lock()
        self._pending: deque[ChatRequest] = deque()
        self._records: dict[str, ChatRequest] = {}
        self._terminal: deque[str] = deque()
        self._stopped = False

    def submit(self, command: dict[str, Any]) -> dict[str, Any]:
        command_id, persona_id, text = _validate(command)
        target = self._agents.get(persona_id)
        if target is None:
            raise HostCommandError(404, "unknown or unowned persona")
        # BotClient.say encodes '<char_name> : <text>\\0'; packetdb.pack adds
        # four bytes and uses uint16 total length. This is a transport ceiling,
        # NOT a claim about server-side chat acceptance or gameplay limits.
        name = getattr(target.client, "char_name", "")
        if len(f"{name} : {text}".encode()) + 5 > 65535:
            raise HostCommandError(400, "chat exceeds the client UTF-8 packet byte limit")
        request = ChatRequest(command_id, persona_id, text, time.time())
        with self._lock:
            prior = self._records.get(command_id)
            if prior is not None:
                if (prior.persona_id, prior.text) != (persona_id, text):
                    raise HostCommandError(400, "command_id conflicts with a retained request")
                return prior.payload()
            if self._stopped:
                raise HostCommandError(503, "host command dispatch stopped")
            if not _available(target):
                raise HostCommandError(409, "owned agent is offline or stopping")
            if len(self._pending) >= 64:
                raise HostCommandError(429, "host chat pending queue is full")
            self._records[request.command_id] = request
            self._pending.append(request)
            return request.payload()

    def status(self, command_id: str) -> dict[str, Any]:
        with self._lock:
            request = self._records.get(command_id)
            if request is None:
                raise HostCommandError(404, "command_id unknown or evicted; dedupe not guaranteed")
            return request.payload()

    def take(self, persona_id: str) -> ChatRequest | None:
        with self._lock:
            target = self._agents.get(persona_id)
            if self._stopped or not _available(target):
                self._cancel_pending(persona_id)
                return None
            for request in self._pending:
                if request.persona_id == persona_id:
                    self._pending.remove(request)
                    request.phase = "claimed"
                    return request
        return None

    def begin_send(self, request: ChatRequest) -> bool:
        with self._lock:
            target = self._agents.get(request.persona_id)
            if request.phase == "terminal":
                return False
            if self._stopped or not _available(target):
                self._finish(request, "cancelled")
                return False
            request.phase = "sending"
            request.status = "uncertain"
            return True

    def finish(
        self,
        request: ChatRequest,
        status: str,
        *,
        error_class: str | None = None,
        audit_error_class: str | None = None,
    ) -> None:
        with self._lock:
            if request.phase == "terminal":
                return
            request.error_class = error_class
            request.audit_error_class = audit_error_class
            self._finish(request, status)

    def _finish(self, request: ChatRequest, status: str) -> None:
        request.status = status
        request.phase = "terminal"
        self._terminal.append(request.command_id)
        while len(self._terminal) > 256:
            del self._records[self._terminal.popleft()]

    def cancel_pending(self, persona_id: str | None = None) -> None:
        with self._lock:
            self._cancel_pending(persona_id)

    def _cancel_pending(self, persona_id: str | None) -> None:
        for request in tuple(self._records.values()):
            if request.phase not in {"pending", "claimed"}:
                continue
            if persona_id is None or request.persona_id == persona_id:
                if request in self._pending:
                    self._pending.remove(request)
                self._finish(request, "cancelled")

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            self._cancel_pending(None)
