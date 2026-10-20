"""Strict offline HTTP schema proof, not live inference or gameplay acceptance."""

import json
from copy import deepcopy
from typing import Any

import httpx
import pytest

from robots.adapters import playing_backends as backend
from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.brain import EventDrivenBrain
from robots.domain.decisions import build_decision_request
from robots.domain.events import Heartbeat
from robots.domain.model import Goal
from robots.knowledge import game_context
from tests.conftest import make_state


def _expected_decide_state(state, base_state: dict) -> dict:
    """Strict pin: decide state = base + event, plus the brain's bounded
    game-knowledge lines when the corpora are present (absent -> legacy
    schema unchanged)."""
    expected = {**base_state, "event": "periodic review #1"}
    knowledge = game_context.decide_knowledge_lines(state)
    if knowledge:
        expected["game_knowledge"] = knowledge
    return expected


@pytest.mark.parametrize("provider_kind", ["flash", "hosted", "local", "private"])
@pytest.mark.parametrize("goal", list(Goal))
def test_heartbeat_request_crosses_strict_systemone_boundary(monkeypatch, provider_kind, goal):
    wire_requests = []
    domain_requests = []
    expected_model = "clef" if provider_kind == "hosted" else "clef-flash"
    state = make_state(goal=goal, inventory_known=False)
    original_state = deepcopy(state)

    def strict_boundary(request):
        payload = json.loads(request.content)
        wire_requests.append(payload)
        if set(payload) != {"model", "state", "questions"}:
            return httpx.Response(
                422,
                json={"errors": [{"code": 5012, "message": "Extra inputs are not permitted"}]},
            )
        assert payload["model"] == expected_model
        assert len(payload["questions"]) == 11
        assert payload["state"]["inventory"] == "unknown"
        # Empty answers exercise the adapter envelope, not invented inference.
        body: dict[str, Any] = {"answers": {}}
        if provider_kind in {"flash", "hosted"}:
            assert request.url.path.endswith(f"/@cf/cloudflare/{expected_model}")
            body = {"success": True, "result": body}
        else:
            assert request.url.path == "/v1/systemone"
        return httpx.Response(200, json=body)

    with httpx.Client(transport=httpx.MockTransport(strict_boundary)) as client:
        monkeypatch.setattr(httpx, "post", client.post)
        if provider_kind in {"flash", "hosted"}:
            provider = backend.make_workers_decision(
                "a" * 32, "test-only-token", model=expected_model
            )
        elif provider_kind == "local":
            provider = backend.make_local_decision("http://127.0.0.1:8302/v1/systemone")
        else:
            provider = backend.make_private_decision("http://192.168.1.156:8091/v1/systemone")
        assert isinstance(provider, backend.PlayingDecision)
        assert not wire_requests  # Real construction never probes HTTP.
        real_decide = provider.decide

        def spy(request):
            original_request = deepcopy(request)
            domain_requests.append(original_request)
            response = real_decide(request)
            assert request == original_request
            return response

        monkeypatch.setattr(provider, "decide", spy)
        brain = EventDrivenBrain(provider, StaticChatGenerator())
        result = brain.handle_event(state, Heartbeat(seq=1))

    assert result.answers == {}
    assert brain.decision_count == 1
    assert len(wire_requests) == len(domain_requests) == 1
    sent, original = wire_requests[0], domain_requests[0]
    assert set(original) == {"model", "state", "questions"}
    assert original["model"] == "clef"
    assert sent["state"] == original["state"]
    assert sent["questions"] == original["questions"]
    base = build_decision_request(state)
    assert original["state"] == _expected_decide_state(state, base["state"])
    assert {k: v for k, v in original["questions"].items() if k != "change_goal"} == base[
        "questions"
    ]
    assert original["questions"]["change_goal"]["criteria"]["keep"] == (
        "Keep pursuing my current goal."
    )
    assert state == original_state
