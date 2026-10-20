"""Bounded WorldFeed SSE reader for the recent-events panel.

``GET /feed/events`` is an infinite SSE stream that replays its backlog first;
this reader consumes frames until the scan cap or the read deadline, then
returns the last ``limit`` events. A read timeout after frames arrived is a
normal end for a bounded read; other upstream failures become ``ok=False``
pages instead of exceptions so a dead feed never blanks the dashboard.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from dashboard_webapp.models import EventsPage, FeedEvent

_MAX_SCAN = 2000


def _default_client_factory(**kwargs: Any) -> httpx.Client:
    return httpx.Client(**kwargs)


class SseEventSource:
    def __init__(
        self,
        base_url: str,
        client_factory: Any = None,
        deadline_s: float = 2.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client_factory = client_factory or _default_client_factory
        self._deadline_s = deadline_s

    def recent_events(self, limit: int) -> EventsPage:
        events, error = self._scan()
        tail = events[-limit:] if limit > 0 else []
        return EventsPage(events=tail, upstream_url=self.base_url, ok=error is None, error=error)

    def _scan(self) -> tuple[list[FeedEvent], str | None]:
        events: list[FeedEvent] = []
        current_id: int | None = None
        current_data: str | None = None
        try:
            with (
                self._client_factory(timeout=self._deadline_s) as client,
                client.stream("GET", f"{self.base_url}/feed/events") as response,
            ):
                response.raise_for_status()
                for raw in response.iter_lines():
                    line = raw.strip()
                    if line.startswith("id:"):
                        current_id, current_data = self._parse_id(line), None
                    elif line.startswith("data:"):
                        current_data = line[len("data:") :].strip()
                    elif not line:
                        if current_id is not None and current_data is not None:
                            event = self._parse_event(current_id, current_data)
                            if event is not None:
                                events.append(event)
                        current_id, current_data = None, None
                        if len(events) >= _MAX_SCAN:
                            break
        except httpx.ReadTimeout:
            # Bounded read: the deadline ended a healthy stream. Keep frames.
            return events, None
        except (httpx.HTTPError, ValueError) as exc:
            return events, str(exc)
        return events, None

    def _parse_id(self, line: str) -> int | None:
        try:
            return int(line[len("id:") :].strip())
        except ValueError:
            return None

    def _parse_event(self, event_id: int, data: str) -> FeedEvent | None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return FeedEvent(
            id=event_id,
            ts=payload.get("ts") if isinstance(payload.get("ts"), (int, float)) else None,
            kind=payload.get("kind") if isinstance(payload.get("kind"), str) else None,
            summary=payload.get("summary") if isinstance(payload.get("summary"), str) else None,
            operator_forced=(
                payload.get("operator_forced")
                if isinstance(payload.get("operator_forced"), bool)
                else None
            ),
        )
