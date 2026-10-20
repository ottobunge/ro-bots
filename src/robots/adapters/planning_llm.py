"""Explicit loopback OpenAI-compatible adapter; no discovery or activation.

Caller owns an injected client; otherwise each completion owns a temporary client.
Capacity is measured from the actual server template and tokenizer every round.
"""

import ipaddress
import json
from typing import Any
from urllib.parse import urlsplit

import httpx

from robots.app.llm_planner import PlanningError, strict_json
from robots.domain.planning import bounded_text, positive_number


def _validate_url(url: str, model: str) -> None:
    parsed = urlsplit(url)
    try:
        local = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        local = False
    if (
        not local
        or parsed.scheme != "http"
        or parsed.path not in ("", "/")
        or any(
            (
                parsed.username is not None,
                parsed.password is not None,
                bool(parsed.query),
                bool(parsed.fragment),
            )
        )
        or not bounded_text(model, 96)
    ):
        msg = "invalid local planning configuration"
        raise PlanningError(msg)


def _validate_limits(
    timeout: float, generation_tokens: int, max_body_bytes: int, token_ceiling: int | None
) -> None:
    if (
        not positive_number(timeout)
        or type(generation_tokens) is not int
        or not 1 <= generation_tokens <= 8192
        or type(max_body_bytes) is not int
        or not 1024 <= max_body_bytes <= 1048576
    ):
        msg = "invalid local planning limits"
        raise PlanningError(msg)
    if token_ceiling is not None and (type(token_ceiling) is not int or token_ceiling < 1):
        msg = "invalid local planning ceiling"
        raise PlanningError(msg)


class LocalPlanningModel:
    def __init__(
        self,
        url: str,
        model: str,
        timeout: float,
        generation_tokens: int,
        *,
        client: httpx.Client | None = None,
        token_ceiling: int | None = None,
        max_body_bytes: int = 65536,
    ) -> None:
        _validate_url(url, model)
        _validate_limits(timeout, generation_tokens, max_body_bytes, token_ceiling)
        self.url, self.model = url.rstrip("/"), model
        self.timeout, self.generation_tokens = float(timeout), generation_tokens
        self.client, self.token_ceiling = client, token_ceiling
        self.max_body_bytes = max_body_bytes

    def _json(
        self, client: httpx.Client, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        content = b"" if payload is None else json.dumps(payload, allow_nan=False).encode("utf-8")
        if len(content) > self.max_body_bytes:
            msg = "local planning request too large"
            raise PlanningError(msg)
        request = httpx.Request(
            "GET" if payload is None else "POST",
            self.url + path,
            content=content,
            headers={"Content-Type": "application/json"},
            extensions={"timeout": httpx.Timeout(self.timeout).as_dict()},
        )
        response = client.send(request, stream=True, auth=None, follow_redirects=False)
        try:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > self.max_body_bytes:
                    msg = "local planning response too large"
                    raise PlanningError(msg)
            return strict_json(body.decode("utf-8"))
        finally:
            response.close()

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.client is not None:
                return self._complete(self.client, payload)
            with httpx.Client(trust_env=False, timeout=self.timeout) as client:
                return self._complete(client, payload)
        except httpx.HTTPError, ValueError, TypeError, KeyError, UnicodeError:
            msg = "local planning transport denied"
            raise PlanningError(msg) from None

    def _complete(self, client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.keys() != {"messages", "tools", "tool_choice", "parallel_tool_calls"}:
            msg = "invalid planning payload"
            raise PlanningError(msg)
        request = {
            **payload,
            "model": self.model,
            "max_tokens": self.generation_tokens,
            "stream": False,
        }
        self._preflight(client, request)
        response = self._json(client, "/v1/chat/completions", request)
        return _response(response)

    def _preflight(self, client: httpx.Client, request: dict[str, Any]) -> None:
        props = self._json(client, "/props")
        capacity = props["default_generation_settings"]["n_ctx"]
        if type(capacity) is not int or not 1 <= capacity <= 1048576:
            msg = "unknown planning capacity"
            raise PlanningError(msg)
        prompt = self._json(client, "/apply-template", request)["prompt"]
        if not isinstance(prompt, str):
            msg = "invalid planning template"
            raise PlanningError(msg)
        tokens = self._json(
            client, "/tokenize", {"content": prompt, "add_special": False, "parse_special": True}
        )["tokens"]
        if not isinstance(tokens, list) or any(type(t) is not int or t < 0 for t in tokens):
            msg = "invalid planning tokenizer"
            raise PlanningError(msg)
        ceiling = capacity if self.token_ceiling is None else min(capacity, self.token_ceiling)
        if len(tokens) + self.generation_tokens > ceiling:
            msg = "planning capacity exceeded"
            raise PlanningError(msg)


def _response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response["choices"]
    if not isinstance(choices, list) or len(choices) != 1:
        msg = "invalid planning response"
        raise PlanningError(msg)
    choice = choices[0]
    message = choice["message"]
    if choice["finish_reason"] not in ("tool_calls", "stop") or message["role"] != "assistant":
        msg = "incomplete planning response"
        raise PlanningError(msg)
    if "content" not in message:
        msg = "invalid planning message"
        raise PlanningError(msg)
    return response
