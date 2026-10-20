"""Control-flow dispatch policy at the owned host cleanup boundary."""

from pathlib import Path
from typing import Any

import pytest

from robots.app.agent_runtime import _raise_cleanup_errors
from robots.domain.events import Heartbeat
from tests.test_llm_planning_clef_execution import FreshModel
from tests.test_llm_planning_host_tick import tracer_host
from tests.test_llm_planning_rest_execution import vitals
from tests.test_native_skill_context import row, skill_list


class HostileControl(BaseException):
    def __getattribute__(self, name: str) -> Any:
        if name == "__dict__":
            message = "overridden exception dict must not be called"
            raise RuntimeError(message)
        return super().__getattribute__(name)

    def add_note(self, note: str) -> None:
        message = "overridden diagnostics must not replace origin"
        raise RuntimeError(message)


@pytest.mark.parametrize("control_type", [KeyboardInterrupt, SystemExit, HostileControl])
def test_control_flow_keeps_identity_and_secondary_failures(
    control_type: type[BaseException],
) -> None:
    origin = control_type("synthetic control flow")
    secondary = OSError("synthetic cleanup failure")
    with pytest.raises(control_type) as caught:
        _raise_cleanup_errors([secondary, origin])
    assert caught.value is origin
    metadata = BaseException.__dict__["__dict__"].__get__(origin)
    assert metadata["shutdown_cleanup_errors"] == (secondary,)
    later = RuntimeError("synthetic outer cleanup failure")
    with pytest.raises(control_type) as again:
        _raise_cleanup_errors([origin, later])
    assert again.value is origin
    assert metadata["shutdown_cleanup_errors"] == (secondary, later)


def test_ordinary_cleanup_failures_still_aggregate() -> None:
    first, second = OSError("first"), RuntimeError("second")
    with pytest.raises(ExceptionGroup) as caught:
        _raise_cleanup_errors([first, second])
    assert caught.value.exceptions == (first, second)


def test_single_ordinary_cleanup_keeps_identity() -> None:
    origin = OSError("single")
    with pytest.raises(OSError, match=r"^single$") as caught:
        _raise_cleanup_errors([origin])
    assert caught.value is origin


def test_empty_cleanup_has_no_error() -> None:
    _raise_cleanup_errors([])


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_actual_host_keeps_execution_origin_despite_client_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    model, now = FreshModel(), [0.0]
    host, wire, brain = tracer_host(tmp_path, monkeypatch, model, now)
    wire.add(skill_list(row(level=3)))
    vitals(wire, 20, 2)
    origin = error_type("synthetic decision origin")
    secondary = RuntimeError("synthetic client cleanup")
    cleanup: list[str] = []

    def failed_decision(request: dict[str, Any]) -> dict[str, Any]:
        raise origin

    def failed_close(*args: Any, **kwargs: Any) -> None:
        wire.running = False
        cleanup.append("client")
        raise secondary

    monkeypatch.setattr(brain.decision, "decide", failed_decision)
    agent = host.agents["one"]
    try:
        assert agent.connect()
        assert model.entered.wait(1)
        model.release.set()
        brain.wait_for_worker(1)
        agent.tick()
        agent.deliver_event(agent.build_state(), Heartbeat(7))
        brain.execution.wait_for_worker(1)
        job = brain.execution.job
        assert job is not None
        assert job.error is origin
        monkeypatch.setattr(wire, "close", failed_close)
        with pytest.raises(error_type) as caught:
            host.stop()
        assert caught.value is origin
        traceback = caught.value.__traceback__
        assert traceback is not None
        while traceback.tb_next is not None:
            traceback = traceback.tb_next
        assert traceback.tb_frame.f_code.co_name == "failed_decision"
        assert cleanup == ["client"]
        assert not wire.running
        assert brain.execution.job is None
        metadata = BaseException.__dict__["__dict__"].__get__(origin)
        assert metadata["shutdown_cleanup_errors"] == (secondary,)
    finally:
        model.release.set()
        model.replan_release.set()
        monkeypatch.undo()
        host.stop()
