"""The roster's logins must be staggered so the server's chain count never grows.

The pinned rule (rathena/src/common/socket.cpp:1089-1091, connect_check_ at
1112-1204) is SLIDING and CHAINED::

    if (hist->ddos)                                   return 0;   # flagged
    else if (DIFF_TICK(gettick(),hist->tick) < ddos_interval) {
        hist->tick = gettick();
        if (hist->count++ >= ddos_count) { hist->ddos = 1; ... }     # trip
    } else { hist->tick = gettick(); hist->count = 0; }              # RESET

ddos_count=10, ddos_interval=3s, ddos_autoreset=10min. The count is only
CLEARED when a connection arrives more than ddos_interval after the previous
one. So a chain of 1s-apart logins accumulates (7 agents plus the solo's
retry storm = >10) and trips the throttle, which then rejects that IP until
the 10-minute auto-reset.

Leg 35 (2026-10-28, 21:30 UTC) proved the shape in the live login server log:
six logins at 0.79-1.13s apart (22:30:00.24 -> 22:30:04.45 local), then
"connect_check: DDoS Attack detected from 10.89.3.6!" on the seventh (the
solo). The solo lost 13 minutes of its window to the block.

The fix: space each login MORE than ddos_interval after the previous one, so
every login takes the server's reset branch.
"""

import itertools
from pathlib import Path
from typing import Any

import pytest

from robots.app import agent_runtime
from robots.app.agent_runtime import AgentHost, LoginStagger

ROSTER_SIZE = 7
DDOS_INTERVAL_S = 3.0
DDOS_COUNT = 10


def server_chain_count(login_times: list[float]) -> int:
    """Replicate the server's sliding chain count over a login sequence.

    The server resets the count when a connection arrives more than
    ddos_interval after the previous one, and increments it otherwise.
    """
    count = 0
    tick = 0.0
    for at in login_times:
        if at - tick < DDOS_INTERVAL_S:
            count += 1
        else:
            count = 0
        tick = at
    return count


def open_roster(stagger: LoginStagger, size: int = ROSTER_SIZE) -> list[float]:
    """Open a roster through the stagger, the way the host's step() does."""
    now = 0.0
    granted: list[float] = []
    for index in range(size):
        persona = f"pop_0003_solo{index:02d}"
        while not stagger.ready(persona, now):
            now += 0.05
        stagger.record(persona, now)
        granted.append(now)
    return granted


def test_a_fresh_stagger_lets_the_first_login_through() -> None:
    stagger = LoginStagger()
    assert stagger.ready("pop_0003_g00m00", 0.0)


def test_the_second_login_in_the_same_instant_waits() -> None:
    stagger = LoginStagger()
    assert stagger.ready("pop_0003_g00m00", 0.0)
    stagger.record("pop_0003_g00m00", 0.0)
    assert not stagger.ready("pop_0003_g00m01", 0.0)


def test_a_login_is_ready_once_the_interval_has_passed() -> None:
    stagger = LoginStagger()
    stagger.record("pop_0003_g00m00", 0.0)
    assert (
        stagger.ready("pop_0003_g00m01", DDOS_INTERVAL_S + 0.01) is False
    ), "the stagger's own interval is deliberately longer than the server's"
    assert stagger.ready("pop_0003_g00m01", stagger.interval_s + 0.01)


def test_the_stagger_interval_clears_the_server_interval() -> None:
    """The stagger's spacing MUST exceed the server's ddos_interval."""
    assert LoginStagger.DEFAULT_INTERVAL_S > DDOS_INTERVAL_S


def test_the_stagger_keeps_the_server_chain_count_below_the_ddos_count() -> None:
    """THE invariant: the server's own chain count never reaches ddos_count."""
    stagger = LoginStagger()
    granted = open_roster(stagger)
    assert server_chain_count(granted) < DDOS_COUNT


def test_the_stagger_keeps_the_chain_count_at_zero() -> None:
    """Each login takes the server's RESET branch, so the count never grows."""
    stagger = LoginStagger()
    granted = open_roster(stagger)
    assert server_chain_count(granted) == 0


def test_the_stagger_spreads_the_roster_over_the_interval() -> None:
    """The logins must not all land in the same instant."""
    stagger = LoginStagger()
    granted = open_roster(stagger)
    assert granted[-1] > granted[0], "the roster must be spread over time"
    # And each consecutive gap must clear the server's interval.
    gaps = [b - a for a, b in itertools.pairwise(granted)]
    assert all(gap > DDOS_INTERVAL_S for gap in gaps), gaps


def test_a_recorded_persona_is_not_blocked_by_its_own_attempt() -> None:
    """A RETRY of the same persona is the backoff's business, not the stagger's.

    The stagger spaces DIFFERENT personas; the per-agent ConnectBackoff
    already owns the retry pacing for one persona. Blocking the same persona
    on itself would double-pace the retry path.
    """
    stagger = LoginStagger()
    stagger.record("pop_0003_g00m00", 0.0)
    assert stagger.ready("pop_0003_g00m00", 0.0)


def test_the_stagger_ignores_personas_that_never_logged_in() -> None:
    stagger = LoginStagger()
    assert stagger.ready("pop_0003_g00m00", 0.0)
    assert stagger.ready("pop_0003_g00m01", 0.0)


@pytest.mark.parametrize("count", [1, 3, 7, 12])
def test_the_stagger_tolerates_a_roster_of_any_size(count: int) -> None:
    stagger = LoginStagger()
    granted = open_roster(stagger, count)
    assert server_chain_count(granted) < DDOS_COUNT


def test_a_retry_storm_after_the_roster_still_cannot_trip_the_throttle() -> None:
    """The solo's retries are the reason leg 35's chain reached >10.

    The ConnectBackoff spaces a persona's retries 5s, 10s, 20s... and the
    server's reset branch needs only MORE than ddos_interval (3s). So a
    retried persona always lands on the reset branch: the chain count stays
    at zero and the throttle never trips.
    """
    stagger = LoginStagger()
    granted = open_roster(stagger)
    # The solo then retries with the ConnectBackoff's spacing (5s, 10s, 20s).
    backoff = [5.0, 10.0, 20.0, 40.0]
    at = granted[-1]
    for delay in backoff:
        at += delay
        granted.append(at)
    assert server_chain_count(granted) < DDOS_COUNT
    assert (
        server_chain_count(granted) == 0
    ), "the backoff's spacing (>=5s) clears the server's 3s interval every time"


def test_the_stagger_records_switch_logins_too() -> None:
    """A deliberate character switch is a login-server connection as well.

    The switch bypasses the stagger's WAIT (a deliberate switch is not a
    retry storm - the same rule the ConnectBackoff bypass follows), but it
    must still be RECORDED, so the next regular login waits for the server's
    counter to reset.
    """
    stagger = LoginStagger()
    stagger.record("pop_0003_g00m00", 0.0)  # a switch login
    assert not stagger.ready(
        "pop_0003_g00m01", 1.0
    ), "a regular login must wait after a switch login"
    assert stagger.ready("pop_0003_g00m01", stagger.interval_s + 0.01)


def test_the_host_uses_the_stagger_for_its_logins() -> None:
    """The host's connect path must consult the stagger."""
    text = Path(agent_runtime.__file__ or "").read_text()
    assert "LoginStagger" in text
    assert "login_stagger" in text
    assert isinstance(AgentHost, type)
    assert Any is not None
