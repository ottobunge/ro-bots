"""Offline owner-bound capture contracts through the approved reader."""

from dataclasses import replace
from threading import Event, Thread
from time import monotonic
from typing import Any

import pytest

from robots.app.planning_context import ObservationSnapshot
from robots.app.planning_job_context import capture_job_context
from robots.domain.planning import Capabilities, PlanningIdentity
from robots.domain.skill_knowledge import PublicSkillCard, PublicSkillKnowledge
from robots.domain.skills import EffectiveSkill, ReceivedSkillContextReadOnly
from robots.society.memory import ExperienceNote, MemoryLog, StubSummarizer
from tests.conftest import make_state

OWNER = PlanningIdentity("a", "world", "opaque-77", 1, "pre-re")
CAPS = Capabilities(frozenset(), frozenset({"prontera"}), frozenset())
PUBLIC = PublicSkillKnowledge(
    "pre-re",
    (
        PublicSkillCard(
            1,
            "pre-re",
            "Basic Skill",
            "NV_BASIC",
            "Public advice",
            9,
            None,
            "revision",
            "db",
            "hash",
            "source",
            "hash",
            "1-2",
        ),
    ),
)


def inputs() -> tuple[ObservationSnapshot, MemoryLog]:
    state = make_state(
        native_epoch=1,
        inventory={"Apple": 3},
        recent_encounters=({"species": 1002, "damage": 0},),
        received_skills=ReceivedSkillContextReadOnly((EffectiveSkill(1, 9, 0, 0, 0, 0),), 1, 0),
    )
    memory = MemoryLog(StubSummarizer())
    memory.append(ExperienceNote(1.0, "chat", "original private note"))
    return ObservationSnapshot(OWNER, state, CAPS, free_stat_points=0), memory


def test_capture_is_independent_full_reader_and_preserves_unknown_zero() -> None:
    snapshot, memory = inputs()
    captured: Any = capture_job_context(OWNER, snapshot, PUBLIC, memory)
    assert captured is not None
    assert snapshot.state is not None
    snapshot.state.inventory["Apple"] = 99
    snapshot.state.recent_encounters[0]["damage"] = 999
    memory.append(ExperienceNote(2.0, "chat", "later"))
    data = captured.read(OWNER, "character")["data"]
    assert data["inventory"]["rows"][0]["quantity"] == 3
    assert data["recent_encounters"]["rows"][0]["damage"] == 0
    assert data["free_skill_points"] is None
    assert data["free_stat_points"] == 0
    assert data["received_effective_skills"]["rows"][0] == {
        "id": 1,
        "level": 9,
        "sp": 0,
        "range": 0,
        "inf": 0,
        "up_flag_raw": 0,
    }
    data["recent_encounters"]["rows"][0]["damage"] = 700
    assert captured.read(OWNER, "encounters")["data"]["rows"][0]["damage"] == 0
    assert captured.read(OWNER, "memory_search")["data"]["source_count"] == 1
    assert captured.read(OWNER, "memory_read", note_id=0)["data"]["text"] == "original private note"
    assert "Basic Skill" in captured.public_rule(OWNER, "skill:1")
    assert captured.observed_capabilities(OWNER) == CAPS
    assert captured.read(replace(OWNER, agent="b"), "memory_search")["status"] == "DENIED"


def test_owner_and_epoch_denied_before_private_capture(monkeypatch: Any) -> None:
    snapshot, memory = inputs()
    calls: list[str] = []

    def capture_spy(_self: MemoryLog) -> tuple[ExperienceNote, ...]:
        calls.append("private")
        return ()

    monkeypatch.setattr(MemoryLog, "capture_raw_notes", capture_spy)
    assert capture_job_context(replace(OWNER, agent="b"), snapshot, PUBLIC, memory) is None
    assert capture_job_context(OWNER, replace(snapshot, identity=None), PUBLIC, memory) is None
    assert snapshot.state is not None
    wrong_epoch = replace(snapshot, state=replace(snapshot.state, native_epoch=2))
    assert capture_job_context(OWNER, wrong_epoch, PUBLIC, memory) is None
    assert calls == []


def test_bounded_raw_capture_preserves_ids_or_explicit_unknown() -> None:
    snapshot, _ = inputs()
    memory = MemoryLog(StubSummarizer())
    for index in range(65):
        memory.append(ExperienceNote(float(index), "chat", "note"))
    captured = capture_job_context(OWNER, snapshot, PUBLIC, memory)
    assert captured is not None
    assert captured.read(OWNER, "memory_search")["status"] == "UNKNOWN"
    assert "source_count" not in captured.read(OWNER, "memory_search")["data"]
    assert captured.read(OWNER, "memory_read")["status"] == "UNKNOWN"
    assert captured.read(OWNER, "character")["status"] == "OK"
    bounded = MemoryLog(StubSummarizer())
    for index in range(64):
        bounded.append(ExperienceNote(float(index), "chat", "é" * 64))
    assert len(bounded.capture_raw_notes() or ()) == 64
    job = capture_job_context(OWNER, snapshot, PUBLIC, bounded)
    assert job is not None
    ids: list[int] = []
    cursor = 0
    while True:
        page = job.read(OWNER, "memory_search", cursor=cursor)["data"]
        assert page["source_count"] == 64
        ids.extend(row["note_id"] for row in page["rows"])
        if not page["has_more"]:
            break
        cursor = page["next_cursor"]
    assert ids == list(range(64))
    bounded.append(ExperienceNote(65.0, "chat", "later"))
    assert job.read(OWNER, "memory_read", note_id=63)["data"]["ts"] == 63.0
    overbytes = MemoryLog(StubSummarizer())
    overbytes.append(ExperienceNote(0.0, "chat", "é" * 4097))
    assert overbytes.capture_raw_notes() is None
    invalid = MemoryLog(StubSummarizer())
    invalid.append(ExperienceNote(0.0, "chat", "\ud800"))
    assert invalid.capture_raw_notes() is None
    assert MemoryLog(StubSummarizer()).capture_raw_notes() == ()


def test_contended_capture_is_nonblocking_and_preserves_other_thread_lock() -> None:
    snapshot, memory = inputs()
    held, release = Event(), Event()

    def own_lock() -> None:
        with memory.locked():
            held.set()
            release.wait(3)

    thread = Thread(target=own_lock)
    thread.start()
    try:
        assert held.wait(1)
        start = monotonic()
        job = capture_job_context(OWNER, snapshot, PUBLIC, memory)
        assert monotonic() - start < 0.5
        assert job is not None
        assert job.read(OWNER, "memory_search")["status"] == "UNKNOWN"
        assert thread.is_alive()
        assert memory.capture_raw_notes() is None
    finally:
        release.set()
        thread.join(1)
    assert not thread.is_alive()
    assert memory.capture_raw_notes() == memory.notes()


def test_whole_job_budget_invalid_encoding_and_nonfinite_clock_denied() -> None:
    snapshot, memory = inputs()
    assert snapshot.state is not None
    huge = replace(snapshot, state=replace(snapshot.state, name="界" * 12000))
    assert capture_job_context(OWNER, huge, PUBLIC, memory) is None
    invalid = replace(snapshot, state=replace(snapshot.state, name="\ud800"))
    assert capture_job_context(OWNER, invalid, PUBLIC, memory) is None
    badclock = MemoryLog(StubSummarizer())
    badclock.append(ExperienceNote(float("nan"), "chat", "note"))
    assert capture_job_context(OWNER, snapshot, PUBLIC, badclock) is None
    largecard = replace(PUBLIC, cards=(replace(PUBLIC.cards[0], meaning="x" * 32768),))
    assert capture_job_context(OWNER, snapshot, largecard, memory) is None
    valid = capture_job_context(OWNER, snapshot, PUBLIC, memory)
    assert valid is not None
    with pytest.raises(ValueError, match="invalid investigation"):
        valid.read(OWNER, "memory_search", max_utf8_bytes=255)


def test_invalid_note_clock_denied_and_capture_has_no_effects(monkeypatch: Any) -> None:
    snapshot, memory = inputs()
    invalid_clock: Any = "not a received clock"
    memory.append(ExperienceNote(invalid_clock, "chat", "note"))
    assert capture_job_context(OWNER, snapshot, PUBLIC, memory) is None
    snapshot, memory = inputs()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("capture called live notes, summary, render or store boundary")

    monkeypatch.setattr(memory, "notes", forbidden)
    monkeypatch.setattr(memory, "ensure_summarized", forbidden)
    monkeypatch.setattr(memory, "close", forbidden)
    monkeypatch.setattr(memory._summarizer, "summarize", forbidden)
    monkeypatch.setattr("robots.society.memory.render_view", forbidden)
    job = capture_job_context(OWNER, snapshot, PUBLIC, memory)
    assert job is not None
    assert job.read(OWNER, "memory_read")["data"]["text"] == "original private note"
    assert memory.dirty_upto == 0
    advice = job.read(OWNER, "public_rule", rule_topic="skill:1")["data"]
    assert advice["ownership"] == "UNKNOWN"
    assert advice["casting_legality"] == "UNKNOWN"
    assert len(str(job.read(OWNER, "character"))) < 4096

    origin = KeyboardInterrupt("synthetic capture cancellation")

    class InterruptedText(str):
        def __len__(self) -> int:
            raise origin

    interrupted = MemoryLog(StubSummarizer())
    interrupted.append(ExperienceNote(0.0, "chat", InterruptedText("note")))
    with pytest.raises(KeyboardInterrupt) as caught:
        interrupted.capture_raw_notes()
    assert caught.value is origin
    finished = Event()

    def acquire_after_failure() -> None:
        with interrupted.locked():
            finished.set()

    thread = Thread(target=acquire_after_failure)
    thread.start()
    thread.join(1)
    assert finished.is_set()
    assert not thread.is_alive()
