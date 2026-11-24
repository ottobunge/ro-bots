"""A real process kill during the drain must leave the window verdict on disk."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from robots import playing
from robots.app import swing_funnel
from tests.test_host_memory import memory_host
from tests.test_population_runner_transport_reporting import runner_module


def run_killed_envelope(root: str, boundary: str) -> None:
    """Child-process harness: all clocks, producers and transport are offline fakes."""
    module = runner_module()
    now = [0.0]
    agent = SimpleNamespace(
        online=True,
        transport_failure=None,
        transport_error=None,
        rebuild_attempts=0,
        rebuild_exhausted=False,
        tick_count=7,
        brain=SimpleNamespace(decision_count=3),
    )

    def kill() -> None:
        Path(root, "drain-entered").touch()
        os.kill(os.getpid(), signal.SIGKILL)

    def step(*, on_schedule_sample) -> None:
        on_schedule_sample(now[0] < (1 if boundary == "schedule" else 100))
        if now[0] >= 1:
            kill()
        now[0] = 1.0

    host = SimpleNamespace(
        agents={"pop_test": agent},
        clock=SimpleNamespace(local_now=lambda: (1, now[0])),
        roster=SimpleNamespace(groups=[]),
        start_worldfeed=lambda: None,
        _scheduled_on=lambda _pid, tick: tick[1] < (1 if boundary == "schedule" else 100),
        step=step,
        stop=kill,
    )
    patcher = pytest.MonkeyPatch()
    patcher.setattr(playing, "build_host", lambda _args: host)
    module.time = SimpleNamespace(time=lambda: now[0], sleep=lambda _duration: None)
    swing_funnel.summarize_swing_traces = lambda _paths, **bounds: {"bounds": bounds}
    module.main(
        [
            "--manifest",
            "unused",
            "--runtime-root",
            root,
            "--memory-root",
            root,
            "--decision-url",
            "unused",
            "--chat-url",
            "unused",
            "--leg",
            "kill",
            "--out-dir",
            root,
            "--trace-dir",
            root,
            "--duration",
            "5" if boundary == "schedule" else "1",
        ]
    )


@pytest.mark.parametrize("boundary", ["schedule", "duration"])
def test_kill_during_envelope_preserves_complete_close_receipt(tmp_path, boundary):
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from tests.test_population_receipt_close import run_killed_envelope; "
                "run_killed_envelope(*__import__('sys').argv[1:])"
            ),
            str(tmp_path),
            boundary,
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert child.returncode == -signal.SIGKILL, child.stdout + child.stderr
    assert (tmp_path / "drain-entered").exists()
    paths = list(tmp_path.glob("population-receipt-kill-*.json"))
    assert len(paths) == 1
    receipt = json.loads(paths[0].read_text())
    assert receipt["steps"] == 1
    assert receipt["step_errors"] == 0
    assert receipt["samples"][-1]["t"] == 1
    assert receipt["samples"][-1]["pop_test"]["decides"] == 3
    assert receipt["samples"][-1]["pop_test"]["online"] is True
    assert receipt["offline_agents"] == []
    assert receipt["transport_recovery"] == {}
    assert receipt["passed"] is None
    assert receipt["swing_conversion"]["bounds"]["end"] == "1970-01-01T00:00:01+00:00"


def test_schedule_observer_runs_before_any_agent_close(tmp_path, monkeypatch):
    host = memory_host(tmp_path, max_agents=2)
    order: list[bool | str] = []
    monkeypatch.setattr(host, "_scheduled_on", lambda _pid, _now: False)
    monkeypatch.setattr(host, "_step_agent", lambda *_args: order.append("close"))
    try:
        host.step(on_schedule_sample=order.append)
        assert order == [False, "close", "close"]
    finally:
        host.stop()
