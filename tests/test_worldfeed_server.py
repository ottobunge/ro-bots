"""Tests for the WorldFeed FastAPI adapter (ADR-007/008 read/write path)."""

import asyncio
import json
import random

import pytest
from fastapi.testclient import TestClient

from robots.adapters.worldfeed_server import (
    WorldFeedServer,
    _clamp_start,
    _parse_cursor,
    create_app,
    demo_world_state,
)
from robots.app.world_state import FeedItem, WorldState
from robots.society.human import HumanContribution, HumanTracker
from robots.society.society import SocietyRoster

SEED = 42
N_GROUPS = 3


def make_client() -> TestClient:
    roster = SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)
    return TestClient(create_app(WorldState(roster, clock=lambda: 1.0)))


def first_agent_id(client: TestClient) -> str:
    agents = client.get("/feed/roster").json()["agents"]
    return str(agents[0]["persona_id"])


# -- roster snapshot --------------------------------------------------------


def test_roster_snapshot_shape() -> None:
    client = make_client()
    resp = client.get("/feed/roster")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"agents"}
    agents = body["agents"]
    assert len(agents) == len(SocietyRoster.build(random.Random(SEED), n_groups=3).personas)
    expected = {
        "persona_id",
        "name",
        "playstyle",
        "attitude",
        "chattiness",
        "level_band",
        "group_id",
        "online",
    }
    assert all(set(agent) == expected for agent in agents)
    solo_groups = {a["group_id"] for a in agents if a["group_id"].startswith("solo-")}
    assert solo_groups  # the build guarantees at least one solo


def test_roster_is_sorted_and_ids_unique() -> None:
    client = make_client()
    agents = client.get("/feed/roster").json()["agents"]
    ids = [a["persona_id"] for a in agents]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


# -- agent detail -----------------------------------------------------------


def test_agent_detail_includes_memory_view_and_reputation() -> None:
    client = make_client()
    agent_id = first_agent_id(client)
    resp = client.get(f"/feed/agent/{agent_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona_id"] == agent_id
    for key in ("goal", "script", "plan", "memory_view", "reputation", "characters", "online"):
        assert key in body
    assert isinstance(body["memory_view"], list)
    assert isinstance(body["reputation"], list)


def test_agent_detail_reputation_includes_agent_score_with_tracker() -> None:
    roster = SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)
    state = WorldState(roster, clock=lambda: 1.0)
    agent_id = sorted(roster.personas)[0]
    tracker = HumanTracker(roster.reputation, roster.graph, list(roster.groups), random.Random(0))
    tracker.record(
        HumanContribution("Ally", "heal", 1.0, "prontera", 1.0),
        agent_id,
    )
    client = TestClient(create_app(state))
    reputation = client.get(f"/feed/agent/{agent_id}").json()["reputation"]
    assert any(e["human"] == "Ally" for e in reputation)
    assert all("agent_score" in e for e in reputation)


def test_agent_detail_unknown_agent_is_404() -> None:
    client = make_client()
    resp = client.get("/feed/agent/does-not-exist")
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]


# -- commands ---------------------------------------------------------------


def test_command_regenerate_roster_same_seed_reproduces_roster() -> None:
    client = make_client()
    body = {"type": "regenerate_roster", "seed": SEED, "groups": N_GROUPS, "solos": 1}
    client.post("/commands", json=body)
    ids_first = [a["persona_id"] for a in client.get("/feed/roster").json()["agents"]]
    client.post("/commands", json=body)
    ids_second = [a["persona_id"] for a in client.get("/feed/roster").json()["agents"]]
    assert ids_first == ids_second


def test_command_regenerate_roster_different_seed_differs() -> None:
    client = make_client()
    client.post("/commands", json={"type": "regenerate_roster", "seed": 1, "groups": 3})
    ids_a = [a["persona_id"] for a in client.get("/feed/roster").json()["agents"]]
    client.post("/commands", json={"type": "regenerate_roster", "seed": 2, "groups": 3})
    ids_b = [a["persona_id"] for a in client.get("/feed/roster").json()["agents"]]
    assert ids_a != ids_b


def test_command_regenerate_roster_response_is_feed_item() -> None:
    client = make_client()
    resp = client.post(
        "/commands", json={"type": "regenerate_roster", "seed": 9, "groups": 2, "solos": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"ts", "kind", "summary", "operator_forced"}
    assert body["operator_forced"] is False
    assert "seed 9" in body["summary"]
    assert body["ts"] == 1.0


def test_command_edit_persona_changes_attitude_and_persists() -> None:
    client = make_client()
    agent_id = first_agent_id(client)
    resp = client.post(
        "/commands",
        json={"type": "edit_persona", "persona_id": agent_id, "attitude": "grinder"},
    )
    assert resp.status_code == 200
    assert resp.json()["kind"] == "edit"
    detail = client.get(f"/feed/agent/{agent_id}").json()
    assert detail["attitude"] == "grinder"
    roster_agents = client.get("/feed/roster").json()["agents"]
    assert next(a for a in roster_agents if a["persona_id"] == agent_id)["attitude"] == "grinder"


def test_command_force_action_marks_operator_forced_and_memory() -> None:
    client = make_client()
    agent_id = first_agent_id(client)
    resp = client.post(
        "/commands",
        json={"type": "force_action", "persona_id": agent_id, "action": "wave"},
    )
    body = resp.json()
    assert body["operator_forced"] is True
    assert "operator forced: wave" in body["summary"]
    detail = client.get(f"/feed/agent/{agent_id}").json()
    assert any("operator forced: wave" in line for line in detail["memory_view"])
    # SSE is intentionally unbounded; a buffered TestClient GET never returns.
    # The stream itself is exercised with bounded consumption in the SSE tests.
    assert resp.status_code == 200
    assert body["kind"] == "force"


def test_command_force_schedule_replaces_windows() -> None:
    client = make_client()
    agent_id = first_agent_id(client)
    resp = client.post(
        "/commands",
        json={
            "type": "force_schedule",
            "persona_id": agent_id,
            "windows": [[1, 20.0, 23.5]],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["kind"] == "schedule"


def test_command_unknown_persona_is_404() -> None:
    client = make_client()
    resp = client.post(
        "/commands", json={"type": "force_action", "persona_id": "ghost", "action": "wave"}
    )
    assert resp.status_code == 404
    assert "ghost" in resp.json()["detail"]


def test_command_bad_type_is_400() -> None:
    client = make_client()
    resp = client.post("/commands", json={"type": "detonate"})
    assert resp.status_code == 400


def test_command_invalid_body_is_400() -> None:
    client = make_client()
    assert client.post("/commands", json=[]).status_code in (400, 422)
    assert client.post("/commands", json={"type": "edit_persona"}).status_code == 400


# -- SSE event stream --------------------------------------------------------


def test_sse_stream_replays_backlog_then_follows() -> None:
    roster = SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)
    state = WorldState(roster, clock=lambda: 1.0)
    state.push_event("chat", "one")
    state.push_event("combat", "two", operator_forced=True)
    server = WorldFeedServer(state)

    class FakeRequest:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}
            self.disconnected = False

        async def is_disconnected(self) -> bool:
            return self.disconnected

    async def collect() -> list[str]:
        request = FakeRequest()
        chunks = []
        gen = server.event_stream(request)  # type: ignore[arg-type]
        chunks.append(await gen.__anext__())
        chunks.append(await gen.__anext__())
        request.disconnected = True
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        return chunks

    chunks = asyncio.run(collect())
    first = json.loads(chunks[0].removeprefix("id: 0\ndata: "))
    assert first["summary"] == "one"
    second = json.loads(chunks[1].removeprefix("id: 1\ndata: "))
    assert second["summary"] == "two"
    assert second["operator_forced"] is True


def test_sse_last_event_id_skips_seen_items() -> None:
    roster = SocietyRoster.build(random.Random(SEED), n_groups=N_GROUPS)
    state = WorldState(roster, clock=lambda: 1.0)
    for i in range(3):
        state.push_event("chat", f"msg {i}")
    server = WorldFeedServer(state)

    class FakeRequest:
        def __init__(self) -> None:
            self.headers = {"last-event-id": "1"}
            self.disconnected = True

    async def first_chunk() -> dict[str, object]:
        gen = server.event_stream(FakeRequest())  # type: ignore[arg-type]
        raw = (await gen.__anext__()).removeprefix("id: 2\ndata: ")
        item: dict[str, object] = json.loads(raw)
        return item

    item = asyncio.run(first_chunk())
    assert item["summary"] == "msg 2"


def test_parse_cursor_and_clamp() -> None:
    class Req:
        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers

    assert _parse_cursor(Req({})) is None  # type: ignore[arg-type]
    assert _parse_cursor(Req({"last-event-id": "5"})) == 5  # type: ignore[arg-type]
    assert _parse_cursor(Req({"last-event-id": "junk"})) is None  # type: ignore[arg-type]
    assert _clamp_start(None, 3) == 0
    assert _clamp_start(2, 3) == 3
    assert _clamp_start(99, 3) == 0
    assert _clamp_start(-1, 3) == 0


# -- feed serialization ------------------------------------------------------


def test_feed_item_payload_snake_case() -> None:
    server = WorldFeedServer(
        WorldState(SocietyRoster.build(random.Random(SEED), n_groups=1), clock=lambda: 2.5)
    )
    payload = server.feed_item_payload(FeedItem(ts=2.5, kind="chat", summary="hi"))
    assert payload == {
        "ts": 2.5,
        "kind": "chat",
        "summary": "hi",
        "operator_forced": False,
    }


def test_demo_world_state_builds_and_is_online() -> None:
    state = demo_world_state()
    assert state.roster.personas
    assert all(s.online for s in state._agent_states.values())
    assert state.events
