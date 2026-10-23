"""The chat persona layer: mortal-sounding game chat from an LLM.

The live leg-12/13 chats showed the failure mode: with no system prompt, the
escalation prompt (the memory dump included) makes the model answer like an
assistant — emoji, multi-line meta commentary ("thanks for the context!").
The builder gives each model style an explicit roleplay contract with hard
format rules, and the sanitizer forces the reply into game-chat shape.
"""

from __future__ import annotations

from robots.adapters.chat_prompt import build_system_prompt, sanitize_reply


def _state_stub(name: str = "NyxSong") -> dict[str, str]:
    return {
        "name": name,
        "job": "Novice",
        "map_name": "prontera",
        "goal": "farm_item",
    }


def test_system_prompt_names_the_character_and_forbids_assistant_speak() -> None:
    prompt = build_system_prompt(**_state_stub())
    assert "NyxSong" in prompt
    for rule in ("one", "no emoji", "never"):
        assert rule in prompt.lower(), prompt
    assert "ai" in prompt.lower() or "assistant" in prompt.lower()


def test_qwen_style_is_stricter_than_generic() -> None:
    qwen = build_system_prompt(**_state_stub(), style="qwen")
    generic = build_system_prompt(**_state_stub(), style="generic")
    assert qwen != generic
    assert "roleplay" in qwen.lower()


def test_unknown_style_falls_back_to_generic() -> None:
    prompt = build_system_prompt(**_state_stub(), style="no-such-style")
    assert "NyxSong" in prompt


def test_sanitize_takes_first_line_and_caps_length() -> None:
    reply = "Hey!\n\nI'm an AI assistant here to help you with your question."
    out = sanitize_reply(reply)
    assert out == "Hey!"


def test_sanitize_strips_emoji_and_wrapping_quotes() -> None:
    assert sanitize_reply('"Welcome back! 🌟"') == "Welcome back!"
    first = sanitize_reply("Welcome 🎉 back!")
    assert first == "Welcome back!"


def test_sanitize_rejects_assistant_speak_with_fallback() -> None:
    assert sanitize_reply("As an AI language model, I cannot do that.") is None
    assert sanitize_reply("I'm here to help you with anything!") is None


def test_sanitize_caps_to_game_chat_length() -> None:
    out = sanitize_reply("a" * 300)
    assert out is not None
    assert len(out) <= 100
