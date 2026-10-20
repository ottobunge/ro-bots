"""WorldFeed goal-enrichment tests (best-effort, offline via MockTransport)."""

from __future__ import annotations

import httpx

from dashboard_webapp.goals_source import HttpGoalSource
from tests.conftest import AGENT_0, AGENT_1


def _transport(handler) -> type[httpx.Client]:
    def factory(**kwargs: object) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    return factory  # type: ignore[return-value]


def _worldfeed_app() -> httpx.Response:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/feed/roster":
            return httpx.Response(
                200,
                json={
                    "agents": [
                        {"persona_id": "p0", "name": "Fx_0"},
                        {"persona_id": "p1", "name": "Other"},
                    ]
                },
            )
        if request.url.path == "/feed/agent/p0":
            return httpx.Response(
                200,
                json={"goal": "grind", "plan": "level to 45", "persona_id": "p0", "name": "Fx_0"},
            )
        return httpx.Response(404, json={"detail": "unknown agent"})

    return handler  # type: ignore[return-value]


def test_enrich_matches_character_name_to_persona() -> None:
    source = HttpGoalSource("http://worldfeed:8400", client_factory=_transport(_worldfeed_app()))

    enriched = source.enrich([AGENT_0, AGENT_1])
    by_id = {a.char_id: a for a in enriched}

    assert by_id[150001].goal == "grind"
    assert by_id[150001].plan == "level to 45"
    # no matching persona -> goals stay None
    assert by_id[150002].goal is None
    assert by_id[150002].plan is None


def test_upstream_failure_degrades_to_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    source = HttpGoalSource("http://worldfeed:8400", client_factory=_transport(handler))
    enriched = source.enrich([AGENT_0])

    assert enriched[0].goal is None
    assert source.last_error is not None


def test_http_error_status_degrades_to_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    source = HttpGoalSource("http://worldfeed:8400", client_factory=_transport(handler))
    enriched = source.enrich([AGENT_0])

    assert enriched[0].goal is None
    assert source.last_error is not None
