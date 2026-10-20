"""MemoryLog must serialize durable acknowledgements and local history ordering."""

import threading

from robots.society.memory import ExperienceNote, Memory, StubSummarizer


class ControlledJournal:
    def __init__(self) -> None:
        self.first_entered = threading.Event()
        self.release_first = threading.Event()
        self.second_entered = threading.Event()
        self.saved: list[ExperienceNote] = []
        self.closed = threading.Event()

    def load(self) -> tuple[ExperienceNote, ...]:
        return ()

    def append(self, note: ExperienceNote) -> None:
        self.saved.append(note)
        if note.text == "first":
            self.first_entered.set()
            if not self.release_first.wait(timeout=2):
                msg = "test journal release timed out"
                raise TimeoutError(msg)
        else:
            self.second_entered.set()

    def close(self) -> None:
        self.closed.set()


def test_concurrent_memory_writes_cannot_overtake_durable_acknowledgement() -> None:
    store = ControlledJournal()
    memory = Memory(StubSummarizer(), store=store)
    errors: list[Exception] = []
    second_attempting = threading.Event()

    def remember(text: str) -> None:
        try:
            if text == "second":
                second_attempting.set()
            memory.remember("chat", text)
        except Exception as exc:
            errors.append(exc)

    first = threading.Thread(target=remember, args=("first",))
    second = threading.Thread(target=remember, args=("second",))
    first.start()
    try:
        assert store.first_entered.wait(timeout=1)
        second.start()
        assert second_attempting.wait(timeout=1)
        assert not store.second_entered.wait(timeout=0.2), "second write overtook first ack"
    finally:
        store.release_first.set()
        first.join(timeout=2)
        if second.ident is not None:
            second.join(timeout=2)
        memory.close()
    assert not first.is_alive()
    assert not second.is_alive()
    assert not errors
    assert memory.log.notes() == tuple(store.saved)


def test_journal_close_waits_for_the_in_flight_durable_append() -> None:
    store = ControlledJournal()
    memory = Memory(StubSummarizer(), store=store)
    closing = threading.Event()
    errors: list[Exception] = []

    def remember() -> None:
        try:
            memory.remember("chat", "first")
        except Exception as exc:
            errors.append(exc)

    def close() -> None:
        closing.set()
        memory.close()

    writer = threading.Thread(target=remember)
    closer = threading.Thread(target=close)
    writer.start()
    try:
        assert store.first_entered.wait(timeout=1)
        closer.start()
        assert closing.wait(timeout=1)
        assert not store.closed.wait(timeout=0.2), "journal closed before durable ack"
    finally:
        store.release_first.set()
        writer.join(timeout=2)
        if closer.ident is not None:
            closer.join(timeout=2)
    assert not errors
    assert not writer.is_alive()
    assert not closer.is_alive()
    assert store.closed.is_set()
    assert len(memory.log.notes()) == 1


class ControlledSummarizer:
    def __init__(self) -> None:
        self.first_entered = threading.Event()
        self.release_first = threading.Event()
        self.second_entered = threading.Event()
        self.calls = 0

    def summarize(self, text_a: str, text_b: str | None) -> str:
        self.calls += 1
        if self.calls == 1:
            self.first_entered.set()
            if not self.release_first.wait(timeout=2):
                msg = "test summarizer release timed out"
                raise TimeoutError(msg)
        else:
            self.second_entered.set()
        return text_a if text_b is None else f"{text_a} / {text_b}"


def test_concurrent_inspection_cannot_build_the_same_summary_twice() -> None:
    summarizer = ControlledSummarizer()
    memory = Memory(summarizer)
    memory.remember("chat", "first")
    views: list[list[str]] = []
    errors: list[Exception] = []
    second_attempting = threading.Event()

    def inspect(second: bool = False) -> None:
        try:
            if second:
                second_attempting.set()
            views.append(memory.view())
        except Exception as exc:
            errors.append(exc)

    first = threading.Thread(target=inspect)
    second = threading.Thread(target=inspect, args=(True,))
    first.start()
    try:
        assert summarizer.first_entered.wait(timeout=1)
        second.start()
        assert second_attempting.wait(timeout=1)
        assert not summarizer.second_entered.wait(timeout=0.2), "summary recomputed concurrently"
    finally:
        summarizer.release_first.set()
        first.join(timeout=2)
        if second.ident is not None:
            second.join(timeout=2)
    assert not errors
    assert not first.is_alive()
    assert not second.is_alive()
    assert summarizer.calls == 1
    assert views == [memory.view()] * 2
