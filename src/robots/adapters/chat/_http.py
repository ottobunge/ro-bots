"""Base plumbing shared by chat adapters."""

from typing import Any

import httpx

CHAT_TIMEOUT_S = 60.0
SYSTEM_PROMPT = (
    "You are a player in the MMORPG Ragnarok Online. Reply in character, in "
    "at most two short sentences, with the tone of a casual MMO player. "
    "Never mention being an AI or a bot."
)


class ChatError(RuntimeError):
    """The chat backend failed."""


def post_chat(url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> str:
    """POST an OpenAI-compatible /v1/chat/completions request; return the text."""
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=CHAT_TIMEOUT_S)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"chat request to {url} failed: {exc}"
        raise ChatError(msg) from exc
    body = resp.json()
    try:
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        msg = f"malformed chat response from {url}"
        raise ChatError(msg) from exc


def chat_payload(prompt: str) -> dict[str, Any]:
    """Shared request body for in-character chat generation."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 60,
        "temperature": 0.8,
    }
