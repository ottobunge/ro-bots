"""Clef via Cloudflare Workers AI: remote, same SystemOne API shape."""

from typing import Any, final

from robots.adapters.decision._http import post_systemone

WORKERS_AI_URL = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/cloudflare/clef"
)


@final
class ClefRemote:
    """DecisionModel port backed by Cloudflare Workers AI ``@cf/cloudflare/clef``."""

    def __init__(self, account_id: str, api_token: str, model: str = "clef") -> None:
        self._url = WORKERS_AI_URL.format(account_id=account_id)
        self._headers = {"Authorization": f"Bearer {api_token}"}
        self._model = model

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = {**request, "model": self._model}
        return post_systemone(self._url, payload, headers=self._headers)
