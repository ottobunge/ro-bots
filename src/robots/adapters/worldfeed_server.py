"""WorldFeed HTTP adapter (ADR-007/008): the Python source of truth for the
Rust dashboard.

Contract (see ``dashboard/README.md`` when it lands):

- ``GET /feed/roster`` — roster snapshot: ``{"agents": [...]}``
- ``GET /feed/agent/{agent_id}`` — persona, goal/script/plan, memory view,
  reputation entries, characters; 404 on unknown id
- ``GET /feed/events`` — SSE stream of feed items (polls the WorldState deque)
- ``POST /commands`` — apply one operator command; 400 on invalid command,
  404 on unknown persona

Demo entry: ``python -m robots.adapters.worldfeed_server`` builds a seeded
WorldState (3 groups incl. 1 solo), pushes sample events and serves on
127.0.0.1:8400.

Standalone/demo create_app(state) retains the legacy notes-only force path;
it does not execute a game action. AgentHost injects its typed dispatcher for
chat only. GET /commands/{command_id} reads bounded process-local status.
No command lifecycle SSE or server acknowledgement is implied by this API.
"""

import asyncio
import json
import random
from collections.abc import AsyncGenerator
from typing import Any, final

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from robots.app.host_commands import CommandDispatcher, HostCommandError
from robots.app.world_state import AgentRuntimeState, CommandError, FeedItem, WorldState
from robots.society.society import SocietyRoster

SSE_POLL_INTERVAL_S = 0.5

HOST = "127.0.0.1"
PORT = 8400


@final
class WorldFeedServer:
    """Thin translation layer: WorldState -> JSON, commands -> WorldState."""

    def __init__(
        self, world_state: WorldState, command_dispatcher: CommandDispatcher | None = None
    ) -> None:
        self._state = world_state
        self._dispatcher = command_dispatcher

    # -- serialization ------------------------------------------------------

    def roster_snapshot(self) -> dict[str, Any]:
        """GET /feed/roster body: every agent with persona + online flag."""
        roster = self._state.roster
        group_of: dict[str, str] = {}
        for group in roster.groups:
            for member in group.member_ids:
                group_of[member] = group.group_id
        agents = []
        for persona_id in sorted(roster.personas):
            persona = roster.personas[persona_id]
            runtime = self._agent_state(persona_id)
            agents.append(
                {
                    "persona_id": persona.persona_id,
                    "name": persona.name,
                    "playstyle": persona.playstyle.value,
                    "attitude": persona.attitude.value,
                    "chattiness": persona.chattiness,
                    "level_band": list(persona.level_band),
                    "group_id": group_of.get(persona_id),
                    "online": runtime.online,
                }
            )
        return {"agents": agents}

    def agent_detail(self, agent_id: str) -> dict[str, Any]:
        """GET /feed/agent/{agent_id} body; raises 404 for unknown ids."""
        persona = self._state.roster.personas.get(agent_id)
        if persona is None:
            raise HTTPException(status_code=404, detail=f"unknown agent: {agent_id}")
        runtime = self._agent_state(agent_id)
        return {
            "persona_id": persona.persona_id,
            "name": persona.name,
            "playstyle": persona.playstyle.value,
            "attitude": persona.attitude.value,
            "chattiness": persona.chattiness,
            "level_band": list(persona.level_band),
            "goal": runtime.current_goal,
            "script": runtime.current_script,
            "plan": runtime.current_plan,
            "online": runtime.online,
            "memory_view": list(self._state.memory_lines(agent_id)),
            "reputation": self._state.reputation_entries(agent_id),
            "characters": list(runtime.characters),
        }

    def feed_item_payload(self, item: FeedItem) -> dict[str, Any]:
        """JSON body of one feed item (SSE ``data:`` field)."""
        return {
            "ts": item.ts,
            "kind": item.kind,
            "summary": item.summary,
            "operator_forced": item.operator_forced,
        }

    def apply_command(self, cmd: dict[str, Any]) -> dict[str, Any]:
        """POST /commands body -> created feed item; CommandError -> 400/404."""
        if cmd.get("type") == "force_action" and self._dispatcher is not None:
            try:
                return self._dispatcher.submit(cmd)
            except HostCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
        try:
            item = self._state.apply_command(cmd)
        except CommandError as exc:
            raise HTTPException(
                status_code=_command_error_status(exc, cmd), detail=str(exc)
            ) from None
        return self.feed_item_payload(item)

    async def event_stream(self, request: Request) -> AsyncGenerator[str]:
        """SSE generator for GET /feed/events: replays the backlog, then polls.

        Streams every existing feed item first, then follows new ones with a
        small sleep loop (no broadcast library). ``Last-Event-ID`` from a
        reconnecting client skips already-seen items. Client disconnects stop
        the loop.
        """
        events = self._state.events
        next_sequence = events[-1].sequence + 1 if events else 0
        start = _clamp_start(_parse_cursor(request), next_sequence)
        sent = start
        for item in events:
            if item.sequence >= sent:
                yield _sse(self.feed_item_payload(item), item.sequence)
                sent = item.sequence + 1
        while True:
            if await request.is_disconnected():
                return
            await asyncio.sleep(SSE_POLL_INTERVAL_S)
            events = self._state.events
            for item in events:
                if item.sequence >= sent:
                    yield _sse(self.feed_item_payload(item), item.sequence)
                    sent = item.sequence + 1

    # -- helpers ------------------------------------------------------------

    def _agent_state(self, persona_id: str) -> AgentRuntimeState:
        state = self._state.agent_state(persona_id)
        if state is None:  # pragma: no cover - roster and states move together
            raise HTTPException(status_code=404, detail=f"unknown agent: {persona_id}")
        return state


def _parse_cursor(request: Request) -> int | None:
    """``Last-Event-ID`` header as an int; None when absent/unparseable."""
    raw = request.headers.get("last-event-id")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _clamp_start(cursor: int | None, feed_len: int) -> int:
    """Where to start replaying: honor the cursor, clamp to retained history."""
    if cursor is None or cursor < 0 or cursor >= feed_len:
        return 0
    return cursor + 1


def _sse(payload: dict[str, Any], index: int) -> str:
    return f"id: {index}\ndata: {json.dumps(payload)}\n\n"


def _command_error_status(exc: CommandError, cmd: dict[str, Any]) -> int:
    """Unknown persona ids are 404, everything else 400."""
    persona_id = cmd.get("persona_id") if isinstance(cmd, dict) else None
    if isinstance(persona_id, str) and persona_id and persona_id in str(exc):
        return 404
    return 400


def create_app(
    world_state: WorldState, *, command_dispatcher: CommandDispatcher | None = None
) -> FastAPI:
    """Build the WorldFeed FastAPI app over the given WorldState."""
    server = WorldFeedServer(world_state, command_dispatcher)
    app = FastAPI(title="ro-bots WorldFeed", version="1.0.0")

    @app.get("/feed/roster")
    async def get_roster() -> dict[str, Any]:
        return server.roster_snapshot()

    @app.get("/feed/agent/{agent_id}")
    async def get_agent(agent_id: str) -> dict[str, Any]:
        return server.agent_detail(agent_id)

    @app.get("/feed/events")
    async def get_events(request: Request) -> StreamingResponse:
        return StreamingResponse(
            server.event_stream(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/commands")
    async def post_command(cmd: dict[str, Any]) -> dict[str, Any]:
        return server.apply_command(cmd)

    @app.get("/commands/{command_id}")
    async def get_command(command_id: str) -> dict[str, Any]:
        if command_dispatcher is None:
            raise HTTPException(status_code=404, detail="no host command dispatcher")
        try:
            return command_dispatcher.status(command_id)
        except HostCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None

    return app


def demo_world_state() -> WorldState:
    """A seeded society: 3 friend groups (the last built group is a solo)."""
    roster = SocietyRoster.build(random.Random(42), n_groups=3)
    state = WorldState(roster)
    for persona_id in roster.personas:
        state.set_agent_state(
            persona_id,
            current_goal="grind",
            current_script="farm_poring.py",
            current_plan="level to 45, then gear up in Prontera South",
            online=True,
        )
    state.push_event("session", "demo world started (seed 42, 3 groups incl. 1 solo)")
    state.push_event("chat", "someone: anyone need a heal?")
    state.push_event("combat", "a Poring was killed")
    return state


def main() -> None:
    app = create_app(demo_world_state())
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
