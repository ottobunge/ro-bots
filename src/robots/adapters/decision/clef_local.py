"""Clef-Flash served locally (llama.cpp-based SystemOne service, spike 001)."""

from typing import Any, final

from robots.adapters.decision._http import post_systemone


@final
class ClefLocal:
    """DecisionModel port backed by the local Clef SystemOne service."""

    def __init__(self, url: str = "http://127.0.0.1:8300/v1/systemone") -> None:
        self._url = url

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        return post_systemone(self._url, request)
