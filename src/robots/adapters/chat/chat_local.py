"""Small local instruct model (llama-server, OpenAI-compatible)."""

from typing import final

from robots.adapters.chat._http import chat_payload, post_chat


@final
class LocalChatServer:
    """ChatGenerator port backed by a local llama.cpp server (e.g. Qwen3-4B)."""

    def __init__(self, url: str = "http://127.0.0.1:8301/v1/chat/completions") -> None:
        self._url = url

    def generate_chat(self, prompt: str) -> str:
        return post_chat(self._url, chat_payload(prompt))
