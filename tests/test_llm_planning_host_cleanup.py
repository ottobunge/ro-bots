"""Retained physical-worker shutdown ownership at offline boundaries."""

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from robots.app import planning_runtime
from robots.ports.planning_model import PlanningModel
from tests.test_llm_planning_host_tick import BlockedModel, tracer_host


def test_shutdown_cancels_known_unsent_before_provider_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = threading.Event(), threading.Event()
    original = planning_runtime._propose_job
    factories: list[int] = []

    def queued(
        job: planning_runtime.PlanningJob,
        factory: Callable[[], PlanningModel],
        clock: Callable[[], float],
    ) -> None:
        entered.set()
        assert release.wait(5), "test must release worker entry"
        original(job, factory, clock)

    monkeypatch.setattr(planning_runtime, "_propose_job", queued)
    model, now = BlockedModel(), [0.0]
    model.release.set()
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    factory = brain.model_factory

    def counted_factory() -> PlanningModel:
        factories.append(1)
        return factory()

    brain.model_factory = counted_factory
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert entered.wait(1)
        job = brain.runtime.job
        assert job is not None
        assert job.thread is not None
        with pytest.raises(RuntimeError, match="planning worker release unconfirmed"):
            agent.disconnect()
        assert not wire.running
        assert brain.runtime.job is job
        assert not brain.reconnect_ready
        release.set()
        brain.wait_for_worker(1)
        assert not job.thread.is_alive()
        assert factories == []
        assert model.payloads == []
        agent.disconnect()
        assert brain.reconnect_ready
    finally:
        release.set()
        model.release.set()
        brain.wait_for_worker(1)
        host.stop()


def test_shutdown_retains_blocked_worker_closes_client_and_refuses_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = BlockedModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        job = brain.runtime.job
        with pytest.raises(RuntimeError, match="planning worker release unconfirmed"):
            agent.disconnect()
        assert not wire.running
        assert brain.runtime.job is job
        assert not agent.connect()
        assert job is not None
        assert job.dispatched
        assert not job.cancelled
        assert job.thread is not None
        assert job.thread.is_alive()
        assert not brain.reconnect_ready
        assert len(model.payloads) == 1
        model.release.set()
        brain.wait_for_worker(1)
        agent.disconnect()
        assert brain.runtime.job is None
        assert brain.reconnect_ready
    finally:
        model.release.set()
        host.stop()


def test_worker_control_flow_origin_is_rethrown_on_host_poll_then_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, now = BlockedModel(), [0.0]
    origin = KeyboardInterrupt("offline-origin")
    model.failure = origin
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        with pytest.raises(KeyboardInterrupt) as raised:
            agent.tick()
        assert raised.value is origin
        frames = []
        trace = raised.value.__traceback__
        while trace is not None:
            frames.append(trace.tb_frame.f_code.co_name)
            trace = trace.tb_next
        assert frames[-1] == "complete"
        assert not wire.sent
        assert not wire.moves
        agent.disconnect()
        assert not wire.running
    finally:
        model.release.set()
        host.stop()
