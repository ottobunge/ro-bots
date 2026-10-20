"""WorldFeed cursor regressions: event identity must survive retention."""

import asyncio
import json
import random
import threading

from robots.adapters.worldfeed_server import WorldFeedServer
from robots.app.world_state import EVENT_FEED_MAXLEN, FeedItem, WorldState
from robots.society.society import SocietyRoster


class StreamRequest:
    def __init__(self, cursor: int | None = None) -> None:
        self.headers = {} if cursor is None else {"last-event-id": str(cursor)}

    async def is_disconnected(self) -> bool:
        return False


def make_state() -> WorldState:
    return WorldState(SocietyRoster.build(random.Random(42), n_groups=1))


def frame_data(raw: str) -> tuple[int, dict]:
    lines = raw.splitlines()
    return int(lines[0].removeprefix("id: ")), json.loads(lines[1].removeprefix("data: "))


def test_reconnect_starts_after_last_delivered_event() -> None:
    state = make_state()
    for index in range(3):
        state.push_event("chat", f"msg {index}")

    async def first() -> str:
        stream = WorldFeedServer(state).event_stream(StreamRequest(1))  # type: ignore[arg-type]
        try:
            return await asyncio.wait_for(anext(stream), timeout=1)
        finally:
            await stream.aclose()

    identity, payload = frame_data(asyncio.run(first()))
    assert identity == 2
    assert payload["summary"] == "msg 2"


def test_connected_stream_follows_new_event_after_retention_fills() -> None:
    state = make_state()
    for index in range(EVENT_FEED_MAXLEN):
        state.push_event("chat", f"msg {index}")

    async def follow() -> str:
        stream = WorldFeedServer(state).event_stream(StreamRequest())  # type: ignore[arg-type]
        try:
            for _ in range(EVENT_FEED_MAXLEN):
                await asyncio.wait_for(anext(stream), timeout=1)
            state.push_event("chat", "new after retention")
            return await asyncio.wait_for(anext(stream), timeout=1)
        finally:
            await stream.aclose()

    identity, payload = frame_data(asyncio.run(follow()))
    assert identity == EVENT_FEED_MAXLEN
    assert payload["summary"] == "new after retention"


def test_concurrent_producers_cannot_reuse_an_event_identity(monkeypatch) -> None:
    state = make_state()
    entered, release, second_entered = (threading.Event() for _ in range(3))

    def controlled_item(**fields):
        item = FeedItem(**fields)
        if fields["summary"] == "first":
            entered.set()
            assert release.wait(2)
        else:
            second_entered.set()
        return item

    monkeypatch.setattr("robots.app.world_state.FeedItem", controlled_item)
    failures: list[BaseException] = []

    def push(summary: str) -> None:
        try:
            state.push_event("chat", summary)
        except BaseException as exc:
            failures.append(exc)

    first = threading.Thread(target=push, args=("first",))
    second = threading.Thread(target=push, args=("second",))
    first.start()
    try:
        assert entered.wait(1)
        second.start()
        assert not second_entered.wait(0.1), "event allocation overtook its earlier producer"
    finally:
        release.set()
        first.join(2)
        if second.ident is not None:
            second.join(2)
    assert not failures
    assert not first.is_alive()
    assert not second.is_alive()
    assert [item.sequence for item in state.events] == [0, 1]


def test_reconnect_uses_global_identity_after_old_events_are_evicted() -> None:
    state = make_state()
    for index in range(EVENT_FEED_MAXLEN + 3):
        state.push_event("chat", f"msg {index}")

    async def first() -> str:
        stream = WorldFeedServer(state).event_stream(
            StreamRequest(EVENT_FEED_MAXLEN)  # type: ignore[arg-type]
        )
        try:
            return await asyncio.wait_for(anext(stream), timeout=1)
        finally:
            await stream.aclose()

    identity, payload = frame_data(asyncio.run(first()))
    assert identity == EVENT_FEED_MAXLEN + 1
    assert payload["summary"] == f"msg {EVENT_FEED_MAXLEN + 1}"


def test_feed_retention_is_bounded_even_without_readers() -> None:
    state = make_state()
    for index in range(EVENT_FEED_MAXLEN + 3):
        state.push_event("chat", str(index))
    assert len(state._feed) == EVENT_FEED_MAXLEN
    assert state.events[0].sequence == 3
    assert state.events[-1].sequence == EVENT_FEED_MAXLEN + 2
