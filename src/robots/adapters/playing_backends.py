"""Explicit real inference providers, never scripted fallbacks.

Inject make_workers_decision (via a zero-argument closure) and make_local_chat
into AgentHost's decision_factory/chat_generator seams. Credentials are explicit
constructor arguments, never auto-discovered, logged or included in errors.
"""

import math
import re
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import httpx


class PlayingBackendError(RuntimeError):
    """A real provider failed; callers must surface unavailability."""


def _post(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
) -> dict[str, Any]:
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPError, ValueError:
        msg = "real inference request failed (details redacted)"
        raise PlayingBackendError(msg) from None
    if not isinstance(body, dict):
        msg = "real inference response is not an object"
        raise PlayingBackendError(msg) from None
    return body


class PlayingDecision:
    """DecisionModel backed by a matching Workers AI model endpoint."""

    def __init__(self, url: str, token: str, model: str, timeout: float) -> None:
        self._url = url
        self._token = token
        self._model = model
        self._timeout = timeout

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        body = _post(
            self._url,
            {**request, "model": self._model},
            {"Authorization": f"Bearer {self._token}"} if self._token else {},
            self._timeout,
        )
        try:
            if body.get("success") is False:
                msg = "real decision provider rejected request"
                raise PlayingBackendError(msg) from None
            answers = body["result"]["answers"] if self._token else body["answers"]
            if not isinstance(answers, dict):
                msg = "real decision response has malformed answers"
                raise PlayingBackendError(msg) from None
        except KeyError, TypeError:
            msg = "real decision response missing answers"
            raise PlayingBackendError(msg) from None
        return {"answers": answers}


def make_workers_decision(
    account_id: str,
    api_token: str,
    *,
    model: str = "clef-flash",
    timeout: float = 30.0,
) -> PlayingDecision:
    """Construct Workers AI Clef with URL and payload model in agreement."""
    _validate_timeout(timeout)
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id) or not api_token.strip():
        msg = "explicit Workers AI credentials required (details redacted)"
        raise ValueError(msg)
    if model not in {"clef", "clef-flash"}:
        msg = "model must be clef or clef-flash"
        raise ValueError(msg)
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/cloudflare/{model}"
    )
    return PlayingDecision(url, api_token, model, timeout)


def _validate_timeout(timeout: float) -> None:
    if not math.isfinite(timeout) or timeout <= 0:
        msg = "timeout must be finite and positive"
        raise ValueError(msg)


def _validate_local(url: str, path: str, timeout: float) -> None:
    _validate_endpoint(url, path, timeout)
    if urlsplit(url).hostname not in {"127.0.0.1", "::1"}:
        msg = "explicit loopback model endpoint required"
        raise ValueError(msg)


def _validate_endpoint(url: str, path: str, timeout: float) -> None:
    _validate_timeout(timeout)
    parsed = urlsplit(url)
    valid = (
        parsed.scheme == "http"
        and parsed.port is not None
        and parsed.username is None
        and parsed.path == path
    )
    if not valid or parsed.query or parsed.fragment:
        msg = "explicit uncredentialed loopback model endpoint required"
        raise ValueError(msg)


def make_local_decision(url: str, *, timeout: float = 90.0) -> PlayingDecision:
    """Construct local Clef; caller explicitly chooses local rather than fallback."""
    _validate_local(url, "/v1/systemone", timeout)
    return PlayingDecision(url, "", "clef-flash", timeout)


def make_private_decision(url: str, *, timeout: float = 90.0) -> PlayingDecision:
    """Explicit owned private-network Clef endpoint; does not start remote services.

    90s default: a cold ~2.2k-token decide on the local iGPU costs 12-35s and
    the brain's decide gates every tick — a 30s budget turned latency spikes
    into total script starvation (windows 50-53). Fast backends (heavengraph
    CUDA) are unaffected: the timeout is a ceiling, not a wait.
    """
    _validate_endpoint(url, "/v1/systemone", timeout)
    address = ip_address(urlsplit(url).hostname or "")
    if not address.is_private or address.is_unspecified or address.is_multicast:
        msg = "explicit private-network model endpoint required"
        raise ValueError(msg)
    return PlayingDecision(url, "", "clef-flash", timeout)


class PlayingChat:
    """ChatGenerator backed by an explicit OpenAI-compatible local endpoint."""

    def __init__(self, url: str, timeout: float) -> None:
        self._url = url
        self._timeout = timeout

    def generate_chat(self, prompt: str) -> str:
        body = _post(
            self._url,
            {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 60,
                "temperature": 0.8,
            },
            {},
            self._timeout,
        )
        try:
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                msg = "real chat response has no text"
                raise PlayingBackendError(msg) from None
        except KeyError, IndexError, TypeError:
            msg = "real chat response is malformed"
            raise PlayingBackendError(msg) from None
        return content


def make_local_chat(url: str, *, timeout: float = 60.0) -> PlayingChat:
    """Construct real local chat without probing or silently selecting a stub."""
    _validate_local(url, "/v1/chat/completions", timeout)
    return PlayingChat(url, timeout)


def make_private_chat(url: str, *, timeout: float = 60.0) -> PlayingChat:
    """Explicit owned private-network chat endpoint (mirrors make_private_decision).

    The heavengraph LLM serves the friend groups' escalations; the endpoint is
    uncredentialed and private-network only, and the caller chooses it
    explicitly rather than by probing.
    """
    _validate_endpoint(url, "/v1/chat/completions", timeout)
    return PlayingChat(url, timeout)
