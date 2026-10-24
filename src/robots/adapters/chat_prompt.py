"""The chat persona layer: mortal-sounding game chat from an LLM.

The live leg-12/13 chats showed the failure mode: with no system prompt, the
escalation prompt (the memory dump included) makes the model answer like an
assistant — emoji, multi-line meta commentary ("thanks for the context!").
`build_system_prompt` gives each model style an explicit roleplay contract
with hard format rules; `sanitize_reply` forces the reply into game-chat
shape and returns None when the model answered like an assistant (the caller
stays silent or falls back to a premade line).

The style registry is the per-inference-backend customization knob: Qwen
needs the heavy roleplay framing; other models get the generic contract.
Select via CHAT_PROMPT_STYLE (playing.build_host).
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable

MAX_CHAT_LEN = 100

_STYLE_RULES: dict[str, str] = {
    "qwen": (
        "You are doing text ROLEPLAY in an online game chat. Stay in character "
        "at all times. Reply with exactly ONE short casual line (max 100 chars), "
        "lowercase-friendly game-chat tone, like a real player typing fast. "
        "Never break character, never mention being an AI, a model, a system or "
        "an assistant, never thank anyone for context, never explain yourself, "
        "no emoji, no markdown, no lists, no newlines. If you would refuse or "
        "explain, instead just answer in character briefly."
    ),
    "generic": (
        "You roleplay a player in an online game chat. Reply with ONE short "
        "casual in-character line. No emoji, no markdown, no newlines, never "
        "mention being an AI or an assistant."
    ),
}


def build_system_prompt(
    *,
    name: str,
    job: str,
    map_name: str,
    goal: str,
    style: str = "generic",
) -> str:
    """The roleplay system prompt for one escalation, per model style."""
    rules = _STYLE_RULES.get(style, _STYLE_RULES["generic"])
    return (
        f"You are {name}, a {job} playing an online game, currently in {map_name} "
        f"working on: {goal}.\n"
        f"{rules}\n"
        f"You know other players by name and speak to them like a regular "
        f"player would: short, casual, sometimes ignoring them."
    )


_ASSISTANT_SPEAK = (
    "as an ai",
    "i'm here to help",
    "im here to help",
    "i can help you",
    "language model",
    "thanks for the context",
)

_EMOJI = re.compile(
    "[\\U0001F300-\\U0001FAFF\\U00002600-\\U000027BF\\U0001F000-\\U0001F02F\\uFE0F]",
)


def sanitize_reply(text: str) -> str | None:
    """Force an LLM reply into game-chat shape; None = stay silent.

    Takes the first non-empty line, strips the wrapping quotes, markdown and
    emoji, caps the length, and rejects assistant-speak outright.
    """
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    line = line.strip("\"'`* ")
    line = _EMOJI.sub("", line)
    line = re.sub(r"[*_`#]", "", line)
    line = re.sub(r"\s{2,}", " ", line).strip()
    if not line:
        return None
    low = line.lower()
    if any(s in low for s in _ASSISTANT_SPEAK):
        return None
    return line[:MAX_CHAT_LEN]


def should_send_chat(
    text: str,
    *,
    last_text: str | None,
    since_s: float | None,
    cooldown_s: float,
) -> bool:
    """The spam governor: cooldown + repeat filter (leg 14's reply storm)."""
    if not text.strip():
        return False
    if since_s is not None and since_s < cooldown_s:
        return False
    return not (last_text is not None and text.strip() == last_text.strip())


_GOAL_PREMADE: dict[str, str] = {
    "GRIND": "lfp",
    "FARM_ITEM": "lfp",
    "SOCIAL": "lfp",
    "QUEST": "lfp",
}


def initiative_premade(goal: object, *, inventory: object) -> str:
    """The goal-keyed default premade id (the sell line only with stock)."""
    name = getattr(goal, "name", str(goal))
    if name == "IDLE_TOWN":
        return "sell_wts" if inventory else "greet"
    return _GOAL_PREMADE.get(name, "lfp")


def initiative_due(
    *,
    last_s: float | None,
    now_s: float,
    min_s: float,
    roll: Callable[[], float] | None = None,
    chance: float = 1.0,
) -> bool:
    """The initiative cadence: the min gap + the probability roll."""
    if last_s is not None and (now_s - last_s) < min_s:
        return False
    if chance >= 1.0:
        return True
    draw = roll() if roll is not None else random.random()
    return draw < chance
