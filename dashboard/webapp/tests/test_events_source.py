"""WorldFeed SSE event proxy tests (bounded read, offline via MockTransport)."""

from __future__ import annotations

import httpx

from dashboard_webapp.events_source import SseEventSource


def _transport(handler) -> type[httpx.Client]:
    def factory(**kwargs: object) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    return factory  # type: ignore[return-value]


def _sse_body(*items: tuple[int, str]) -> bytes:
    frames = []
    for seq, kind in items:
        forced = "true" if seq == 2 else "false"  # JSON booleans, not Python's
        frames.append(
            f'id: {seq}\ndata: {{"ts": 179240000{seq}.0, "kind": "{kind}", '
            f'"summary": "event {seq}", "operator_forced": {forced}}}\n\n'
        )
    return "".join(frames).encode()


def test_parses_events_and_keeps_the_tail() -> None:
    body = _sse_body((1, "chat"), (2, "combat"), (3, "session"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    source = SseEventSource("http://worldfeed:8400", client_factory=_transport(handler))
    page = source.recent_events(limit=2)

    assert page.ok is True
    assert page.error is None
    assert page.upstream_url == "http://worldfeed:8400"
    assert [(e.id, e.kind) for e in page.events] == [(2, "combat"), (3, "session")]
    assert page.events[0].operator_forced is True
    assert page.events[0].summary == "event 2"


def test_malformed_frames_are_skipped() -> None:
    body = (
        b"id: 1\ndata: {not json}\n\n"
        b'id: 2\ndata: {"kind": "chat", "summary": "ok"}\n\n'
        b": comment only\n\n"
        b'data: {"kind": "orphan"}\n\n'  # no id -> skipped
        b'id: 3\ndata: {"kind": "loot", "summary": "last"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    source = SseEventSource("http://worldfeed:8400", client_factory=_transport(handler))
    page = source.recent_events(limit=10)

    assert [(e.id, e.kind) for e in page.events] == [(2, "chat"), (3, "loot")]


def test_upstream_connection_failure_is_reported_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    source = SseEventSource("http://worldfeed:8400", client_factory=_transport(handler))
    page = source.recent_events(limit=50)

    assert page.events == []
    assert page.ok is False
    assert "connection refused" in (page.error or "")


def test_http_error_status_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502)

    source = SseEventSource("http://worldfeed:8400", client_factory=_transport(handler))
    page = source.recent_events(limit=50)

    assert page.ok is False
    assert "502" in (page.error or "")
