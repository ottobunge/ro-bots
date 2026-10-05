"""SystemOne HTTP plumbing shared by local and remote Clef adapters."""

from typing import Any

import httpx

SYSTEMONE_TIMEOUT_S = 30.0


class SystemOneError(RuntimeError):
    """The decision backend failed or returned a malformed answer."""


def post_systemone(
    url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None
) -> dict[str, Any]:
    """POST a SystemOne request; validate and return the response body."""
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=SYSTEMONE_TIMEOUT_S)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"systemone request to {url} failed: {exc}"
        raise SystemOneError(msg) from exc
    body = resp.json()
    if not isinstance(body, dict) or "answers" not in body:
        msg = f"systemone response from {url} missing 'answers'"
        raise SystemOneError(msg)
    return body
