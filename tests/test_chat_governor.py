"""The chat governor: leg 14's mutual-reply loop sent 818 chats per agent in
one window (mostly the same line) — a cooldown plus a repeat filter keeps
each agent sounding like a player, not a bot flooding the channel."""

from __future__ import annotations

from robots.adapters.chat_prompt import should_send_chat


def test_first_chat_always_allowed() -> None:
    assert should_send_chat("hey", last_text=None, since_s=None, cooldown_s=12.0)


def test_cooldown_blocks_rapid_chats() -> None:
    assert not should_send_chat("hey", last_text=None, since_s=3.0, cooldown_s=12.0)
    assert should_send_chat("hey", last_text=None, since_s=13.0, cooldown_s=12.0)


def test_identical_repeat_blocked_even_after_cooldown() -> None:
    assert not should_send_chat("Always.", last_text="Always.", since_s=60.0, cooldown_s=12.0)


def test_different_text_after_cooldown_allowed() -> None:
    assert should_send_chat("brb farming", last_text="Always.", since_s=60.0, cooldown_s=12.0)


def test_empty_text_never_sends() -> None:
    assert not should_send_chat("", last_text=None, since_s=None, cooldown_s=12.0)
