"""Deterministic population ownership interleavings (offline only)."""

import random
import threading

import pytest

from robots.app.world_state import CommandError, WorldState
from robots.society.memory import ExperienceNote, MemoryLog, StubSummarizer
from robots.society.society import SocietyRoster

COMMAND = {
    "type": "regenerate_roster",
    "seed": 17,
    "groups": 2,
    "solos": 1,
    "friends_min": 7,
    "friends_max": 7,
}


def make_state() -> WorldState:
    state = WorldState(SocietyRoster.build(random.Random(42), n_groups=3))
    persona_id = next(iter(state.roster.personas))
    state.set_agent_state(persona_id, current_goal="preserved", online=True)
    state.push_event("session", "preserved")
    return state


def test_binding_after_admission_preserves_entire_aggregate(monkeypatch) -> None:
    state = make_state()
    persona_id = next(iter(state.roster.personas))
    reputation_rows = _seed_reputation(state, persona_id)
    entered, release = threading.Event(), threading.Event()
    build = SocietyRoster.build
    failures: list[BaseException] = []

    def paused_build(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return build(*args, **kwargs)

    def regenerate() -> None:
        try:
            state.apply_command(COMMAND)
        except BaseException as exc:
            failures.append(exc)

    monkeypatch.setattr(SocietyRoster, "build", paused_build)
    worker = threading.Thread(target=regenerate, daemon=True)
    worker.start()
    try:
        assert entered.wait(2)
        log = MemoryLog(StubSummarizer())
        log.append(ExperienceNote(ts=1, kind="session", text="host private memory"))
        state.bind_memory(persona_id, log)
        roster, reputation = state.roster, state._reputation
        runtimes, memories = state._agent_states, state._memories
        runtime_values, memory_values = dict(runtimes), dict(memories)
        seed, default_size = state._seed, state._group_size_max
        events, sequence = state.events, state._next_event_sequence
        memory_lines = state.memory_lines(persona_id)

    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()
    assert len(failures) == 1, "admitted regeneration must reject a later successful binding"
    assert isinstance(failures[0], CommandError)
    assert "reconciliation" in str(failures[0])
    assert state._host_bound
    assert state.roster is roster
    assert state._reputation is reputation
    assert state.reputation_entries(persona_id) == reputation_rows
    assert state._agent_states is runtimes
    assert state._agent_states == runtime_values
    assert state._memories is memories
    assert state._memories == memory_values
    assert state._memories[persona_id] is log
    assert state.memory_lines(persona_id) == memory_lines
    assert log.notes()[0].text == "host private memory"
    assert (state._seed, state._group_size_max) == (seed, default_size)
    assert state.events == events
    assert state._next_event_sequence == sequence


def _seed_reputation(state: WorldState, persona_id: str) -> list[dict[str, float | str]]:
    state._reputation._by_agent[persona_id] = {"remembered human": 0.5}
    state._reputation._by_group[state.roster.groups[0].group_id] = {"remembered human": 0.25}
    return state.reputation_entries(persona_id)


def test_unknown_binding_during_build_does_not_claim_ownership(monkeypatch) -> None:
    state = make_state()
    entered, release = threading.Event(), threading.Event()
    build = SocietyRoster.build
    failures: list[BaseException] = []

    def paused_build(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return build(*args, **kwargs)

    def regenerate() -> None:
        try:
            state.apply_command(COMMAND)
        except BaseException as exc:
            failures.append(exc)

    monkeypatch.setattr(SocietyRoster, "build", paused_build)
    worker = threading.Thread(target=regenerate, daemon=True)
    worker.start()
    try:
        assert entered.wait(2)
        with pytest.raises(CommandError, match="unknown persona_id"):
            state.bind_memory("missing-persona", MemoryLog(StubSummarizer()))
        assert not state._host_bound
        assert "missing-persona" not in state._memories
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()
    assert not failures
    assert len(state.roster.personas) == 15
    assert len(state.events) == 2


def test_candidate_failure_keeps_originating_exception_and_state(monkeypatch) -> None:
    state = make_state()
    roster, memories, runtimes = state.roster, state._memories, state._agent_states
    before = state.events
    failure = RuntimeError("candidate build failed")

    def failed_build(*args, **kwargs):
        raise failure

    monkeypatch.setattr(SocietyRoster, "build", failed_build)
    with pytest.raises(RuntimeError) as caught:
        state.apply_command(COMMAND)
    assert caught.value is failure
    assert state.roster is roster
    assert state._reputation is roster.reputation
    assert state._memories is memories
    assert state._agent_states is runtimes
    assert state.events == before
    assert state._seed == 42
    assert state._group_size_max == 6


def test_memory_reader_does_not_hold_aggregate_lock(monkeypatch) -> None:
    state = make_state()
    persona_id = next(iter(state.roster.personas))
    log = state._memories[persona_id]
    rendering, held = threading.Event(), threading.Event()
    failures: list[BaseException] = []

    def read() -> None:
        try:
            state.memory_lines(persona_id)
        except BaseException as exc:
            failures.append(exc)

    def hold_and_bind() -> None:
        try:
            with log.locked():
                held.set()
                assert rendering.wait(2)
                state.bind_memory(persona_id, log)
                state.push_event("session", "memory owner callback")
        except BaseException as exc:
            failures.append(exc)

    # Signal immediately before the reader attempts the private memory lock.
    original = WorldState._memory_lines

    def observed_lines(memory):
        rendering.set()
        return original(memory)

    monkeypatch.setattr(WorldState, "_memory_lines", staticmethod(observed_lines))
    holder = threading.Thread(target=hold_and_bind, daemon=True)
    reader = threading.Thread(target=read, daemon=True)
    holder.start()
    assert held.wait(2)
    reader.start()
    holder.join(3)
    reader.join(3)
    assert not holder.is_alive(), "memory owner could not acquire aggregate/feed lock"
    assert not reader.is_alive(), "reader retained aggregate lock while waiting on memory"
    assert not failures
    assert state._memories[persona_id] is log


@pytest.mark.parametrize("read_path", ["roster", "runtime", "memory", "reputation", "feed"])
def test_public_reads_wait_for_whole_population_commit(monkeypatch, read_path) -> None:
    state = make_state()
    committed_roster, release, reading, finished = (threading.Event() for _ in range(4))
    failures: list[BaseException] = []
    result: list[tuple] = []
    original = vars(WorldState)["roster"]
    candidate_ids: list[str] = []

    def paused_setter(self, roster):
        original.fset(self, roster)
        candidate_ids.append(next(iter(roster.personas)))
        committed_roster.set()
        assert release.wait(3)

    def regenerate() -> None:
        try:
            state.apply_command(COMMAND)
        except BaseException as exc:
            failures.append(exc)

    def read() -> None:
        reading.set()
        try:
            _read_path(state, read_path, candidate_ids[0])
            roster = state.roster
            persona_id = next(iter(roster.personas))
            result.append(
                (
                    roster,
                    state.agent_state(persona_id),
                    state.memory_lines(persona_id),
                    state.reputation_entries(persona_id),
                    state.events,
                )
            )
        except BaseException as exc:
            failures.append(exc)
        finally:
            finished.set()

    monkeypatch.setattr(WorldState, "roster", property(original.fget, paused_setter))
    writer = threading.Thread(target=regenerate, daemon=True)
    reader = threading.Thread(target=read, daemon=True)
    writer.start()
    try:
        assert committed_roster.wait(2)
        reader.start()
        assert reading.wait(2)
        assert not finished.wait(0.1), "public reader observed a partial commit"
    finally:
        release.set()
        writer.join(3)
        if reader.ident is not None:
            reader.join(3)
    assert not writer.is_alive()
    assert not reader.is_alive()
    assert not failures
    _assert_snapshot(result[0])


def _assert_snapshot(snapshot: tuple) -> None:
    roster, runtime, memory, reputation, events = snapshot
    assert len(roster.personas) == 15
    assert runtime is not None
    assert runtime.current_goal == "idle"
    assert memory == ()
    assert reputation == []
    assert events[-1].kind == "roster"


def _read_path(state: WorldState, path: str, persona_id: str) -> object:
    match path:
        case "roster":
            return state.roster
        case "runtime":
            return state.agent_state(persona_id)
        case "memory":
            return state.memory_lines(persona_id)
        case "reputation":
            return state.reputation_entries(persona_id)
        case _:
            return state.events
