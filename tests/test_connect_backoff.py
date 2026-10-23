"""The connect backoff: one agent's retry storm must not feed the server's
connect_check DDoS throttle (the e2e login hardens on every failure and each
failed attempt refreshes the window — leg 14's solo hammered ~4 attempts a
second and latched it for the shared source)."""

from __future__ import annotations

from robots.app.agent_runtime import ConnectBackoff


def test_ready_immediately_before_any_failure() -> None:
    backoff = ConnectBackoff()
    assert backoff.ready(monotonic=100.0)


def test_failure_backs_off_exponentially_and_caps() -> None:
    backoff = ConnectBackoff()
    backoff.record_failure(100.0)
    assert not backoff.ready(101.0)
    assert not backoff.ready(104.0)
    assert backoff.ready(105.0)  # 5s after the first failure
    backoff.record_failure(105.0)
    assert not backoff.ready(114.0)
    assert backoff.ready(115.0)  # +10s
    for _ in range(3, 8):
        backoff.record_failure(0.0)
    backoff.record_failure(200.0)
    assert not backoff.ready(439.0)
    assert backoff.ready(441.0)  # capped at 240s


def test_success_resets_the_streak() -> None:
    backoff = ConnectBackoff()
    backoff.record_failure(100.0)
    backoff.record_failure(100.1)
    backoff.record_success()
    assert backoff.ready(100.2)
    backoff.record_failure(100.3)
    assert backoff.ready(105.3)  # the streak restarted: the 5s floor again
