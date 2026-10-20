"""Finite detached run evidence; no journals, native callbacks or credentials."""

import hashlib
import json
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import httpx

PUBLIC_FIELDS = {
    "passed",
    "native_acceptance",
    "quest_or_reward_acceptance",
    "provider_result",
    "admission",
    "request",
    "ui_progress",
    "cleanup",
    "errors",
}


def public_report(document: dict[str, Any]) -> dict[str, Any]:
    return {key: redact(value) for key, value in document.items() if key in PUBLIC_FIELDS}


def redact(value: Any) -> Any:
    if isinstance(value, str):
        if re.search(r"(?i)([a-z][a-z0-9+.-]*://|(?:password|token|host|user|socket)\s*=)", value):
            return "[REDACTED]"
        return value
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items() if key in {"stage", "type"}}
    return value


def encode(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return encode(asdict(value))
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [encode(item) for item in value]
    return value


class RunEvidence:
    """Each write creates one durable immutable record in a private run directory."""

    def __init__(self, directory: Path, run_id: str) -> None:
        self.directory, self.run_id = directory, run_id
        self.guard = threading.Lock()
        self.sequence = 0
        self.private_digests: list[str] = []

    def write(self, _kind: str, document: dict[str, Any], *, private: bool) -> str:
        body = json.dumps(encode(document), allow_nan=False, indent=2).encode() + b"\n"
        digest = hashlib.sha256(body).hexdigest()
        if len(body) > 262144:
            msg = "finite evidence size exhausted"
            raise ValueError(msg)
        with self.guard:
            if self.sequence >= 16:
                msg = "finite evidence count exhausted"
                raise ValueError(msg)
            self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.sequence += 1
            prefix = "private" if private else "primary"
            target = self.directory / f"{prefix}-{self.sequence:03d}.json"
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            if private:
                self.private_digests.append(digest)
        return digest

    def public(self, document: dict[str, Any]) -> None:
        primary = public_report(document)
        with self.guard:
            primary["private_evidence_digests"] = tuple(self.private_digests)
        self.write("primary", primary, private=False)

    def private(self, kind: str, document: dict[str, Any]) -> str:
        return self.write(
            kind,
            {"kind": kind, "run_id": self.run_id, "clock": time.monotonic(), **document},
            private=True,
        )


class RecordingClient(httpx.Client):
    """Capture bounded model bytes before the unchanged adapter decodes them."""

    def __init__(self, evidence: RunEvidence, check: Callable[[], None]) -> None:
        super().__init__(trust_env=False)
        self.evidence = evidence
        self.check = check

    def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        self.check()
        response = super().send(request, **kwargs)
        if request.url.path != "/v1/chat/completions":
            return response
        body = bytearray()
        try:
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 65536:
                    msg = "finite model response size exhausted"
                    raise ValueError(msg)
        finally:
            response.close()
        raw = bytes(body)
        self.evidence.private(
            "planning_http",
            {
                "payload": json.loads(request.content),
                "request_digest": hashlib.sha256(request.content).hexdigest(),
                "raw_response": raw.decode("utf-8", errors="surrogateescape"),
                "response_digest": hashlib.sha256(raw).hexdigest(),
                "http_status": response.status_code,
            },
        )
        return httpx.Response(response.status_code, content=raw, request=request)
