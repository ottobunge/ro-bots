"""Remote OpenAI-compatible chat endpoint (swap-in for the local model)."""

from typing import final

from robots.adapters.chat._http import chat_payload, post_chat


@final
class ChatRemote:
    """ChatGenerator port backed by any OpenAI-compatible chat API."""

    def __init__(self, url: str, api_key: str, model: str) -> None:
        self._url = url
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model

    def generate_chat(self, prompt: str) -> str:
        payload = chat_payload(prompt) | {"model": self._model}
        return post_chat(self._url, payload, headers=self._headers)
