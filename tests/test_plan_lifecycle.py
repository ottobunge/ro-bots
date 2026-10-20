from dataclasses import replace
from typing import Any, cast

import pytest

from robots.app.plan_lifecycle import PlanLifecycle
from robots.domain.planning import (
    Capabilities,
    ObservableCondition,
    Phase,
    PhaseKind,
    PlanningIdentity,
    ProposedPlan,
    ReplanCondition,
)
from robots.ports.planning import InvestigationTools, PlannerPort


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def identity() -> PlanningIdentity:
    return PlanningIdentity("agent-a", "world-a", "character-a", 1, "classic")


def capabilities() -> Capabilities:
    return Capabilities(frozenset(PhaseKind), frozenset({"field"}), frozenset({"vitals"}))


def proposal(
    _planner: PlannerPort | None = None, _tools: InvestigationTools | None = None
) -> ProposedPlan:
    return ProposedPlan(
        identity(),
        "recover",
        "observed low health",
        (Phase(PhaseKind.REST, "field"),),
        ObservableCondition.RECOVERED,
        ObservableCondition.HEALTH_IMPROVES,
        30.0,
        120.0,
        PhaseKind.IDLE,
        (ReplanCondition.DANGER,),
        frozenset({"vitals"}),
    )


def test_request_admission_execution_path() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    assert owner.admit(request, proposal(), capabilities())
    assert owner.execution_plan() == proposal()
    assert owner.version == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent", "other"),
        ("world", "other"),
        ("character", "other"),
        ("session_epoch", 2),
        ("ruleset", "renewal"),
    ],
)
def test_foreign_identity_denied(field: str, value: str | int) -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    foreign = replace(identity(), **{field: cast(Any, value)})
    assert not owner.admit(request, replace(proposal(), identity=foreign), capabilities())
    assert owner.active is None
    assert owner.counters["rejected"] == 1


@pytest.mark.parametrize(
    "phase", [Phase(cast(PhaseKind, "quest"), "field"), Phase(PhaseKind.IDLE, "unknown")]
)
def test_unsupported_phase_or_map_denied(phase: Phase) -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    assert not owner.admit(request, replace(proposal(), phases=(phase,)), capabilities())


def test_current_unknown_prerequisite_denied() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    unknown = replace(capabilities(), fresh_facts=frozenset())
    assert not owner.admit(request, replace(proposal(), required_facts=frozenset()), unknown)
    assert owner.active is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration", True),
        ("duration", float("nan")),
        ("review_at", 100.0),
        ("review_at", float("inf")),
    ],
)
def test_invalid_timing_denied(field: str, value: float) -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    assert not owner.admit(
        request, replace(proposal(), **{field: cast(Any, value)}), capabilities()
    )


def test_stale_token_cannot_replace_active() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    assert owner.admit(request, proposal(), capabilities())
    assert not owner.admit(request, replace(proposal(), objective="other"), capabilities())
    assert owner.active == proposal()
    assert owner.version == 1


def test_single_flight_reasons_are_deduplicated_and_bounded() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    first = owner.request("start")
    assert first is not None
    for index in range(20):
        assert owner.request(f"reason-{index}") is not None
    assert owner.request("start") is not None
    assert owner.pending is not None
    assert owner.pending.token == first.token
    assert len(owner.reasons) == 8
    assert owner.counters["requests"] == 1
    assert owner.counters["coalesced"] == 21


def test_timeout_cooldown_and_retry_exhaustion() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock, max_attempts=2)
    first = owner.request("start")
    assert first is not None
    clock.now = 105.0
    assert owner.request("retry") is None
    assert owner.pending is None
    assert owner.counters["timeouts"] == 1
    assert not owner.admit(first, proposal(), capabilities())
    clock.now = 110.0
    second = owner.request("retry")
    assert second is not None
    assert second.token != first.token
    assert not owner.admit(first, proposal(), capabilities())
    assert cast(Any, owner.pending) == second
    assert not owner.admit(replace(second, base_version=99), proposal(), capabilities())
    assert cast(Any, owner.pending) == second
    clock.now = 120.0
    assert owner.request("retry") is None
    assert owner.pending is None
    assert owner.outcome == "exhausted"
    assert owner.counters["requests"] == 2


def test_invalid_reply_consumes_attempt_and_releases_request() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock, max_attempts=1)
    request = owner.request("start")
    assert request is not None
    assert not owner.admit(request, replace(proposal(), duration=-1), capabilities())
    assert owner.pending is None
    clock.now = 1000.0
    assert owner.request("retry") is None
    assert owner.counters["requests"] == 1


def test_identity_switch_invalidates_old_context_and_reply() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock)
    first = owner.request("start")
    assert first is not None
    assert owner.admit(first, proposal(), capabilities())
    clock.now = 110.0
    old = owner.request("review")
    assert old is not None
    owner.update_identity(replace(identity(), session_epoch=2))
    assert owner.execution_plan() is None
    assert owner.pending is None
    new = owner.request("start")
    assert new is not None
    assert not owner.admit(old, proposal(), capabilities())
    assert owner.pending == new


def test_reason_and_config_bounds() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    with pytest.raises(ValueError, match="reason"):
        owner.request("é" * 129)
    with pytest.raises(ValueError, match="configuration"):
        PlanLifecycle(identity(), FakeClock(), max_attempts=True)
    with pytest.raises(ValueError, match="identity"):
        replace(identity(), session_epoch=True)
    with pytest.raises(ValueError, match="identity"):
        replace(identity(), agent=" agent-a")


def test_empty_plan_unsafe_fallback_and_target_bool_denied() -> None:
    for plan in (
        replace(proposal(), phases=()),
        replace(proposal(), fallback=PhaseKind.TRAVEL),
        replace(proposal(), phases=(Phase(PhaseKind.FARM, "field", public_item=True),)),
    ):
        owner = PlanLifecycle(identity(), FakeClock())
        request = owner.request("start")
        assert request is not None
        summary = replace(capabilities(), fresh_facts=frozenset({"vitals", "inventory"}))
        assert not owner.admit(request, plan, summary)


def test_execution_reads_revalidate_without_requesting() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock)
    request = owner.request("start")
    assert request is not None
    assert owner.admit(request, proposal(), capabilities())
    assert owner.pending is None
    for _ in range(20):
        assert owner.execution_plan(capabilities()) == proposal()
    assert owner.execution_plan(replace(capabilities(), fresh_facts=frozenset())) is None
    clock.now = 120.0
    assert owner.execution_plan(capabilities()) is None
    assert owner.counters["requests"] == 1


def test_success_resets_retry_episode_but_keeps_cooldown() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock, max_attempts=1)
    first = owner.request("start")
    assert first is not None
    assert owner.admit(first, proposal(), capabilities())
    assert owner.request("new episode") is None
    clock.now = 110.0
    second = owner.request("new episode")
    assert second is not None
    assert second.reasons == ("new episode",)
    assert owner.admit(second, proposal(), capabilities())


def test_observable_conditions_must_be_typed() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    assert not owner.admit(
        request,
        replace(proposal(), success=cast(ObservableCondition, "execute shell")),
        capabilities(),
    )


def test_mutable_phase_sequence_denied() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    mutable = replace(proposal(), phases=cast(tuple[Phase, ...], [Phase(PhaseKind.IDLE, "field")]))
    assert not owner.admit(request, mutable, capabilities())


def test_prerequisite_metadata_is_bounded() -> None:
    owner = PlanLifecycle(identity(), FakeClock())
    request = owner.request("start")
    assert request is not None
    facts = frozenset(f"fact-{index}" for index in range(9))
    summary = replace(capabilities(), fresh_facts=facts | {"vitals"})
    assert not owner.admit(request, replace(proposal(), required_facts=facts), summary)


@pytest.mark.parametrize("field", ["duration", "review_at"])
def test_oversized_timing_rejection_preserves_active_and_attempt_budget(field: str) -> None:
    clock = FakeClock()
    owner = PlanLifecycle(identity(), clock, max_attempts=1)
    first = owner.request("start")
    assert first is not None
    active = proposal()
    assert owner.admit(first, active, capabilities())
    clock.now = 110.0
    request = owner.request("review")
    assert request is not None
    invalid = replace(proposal(), **{field: cast(Any, 10**400)})
    assert not owner.admit(request, invalid, capabilities())
    assert owner.pending is None
    assert owner.outcome == "timing"
    assert owner.counters["rejected"] == 1
    assert owner.active == active
    assert owner.version == 1
    assert owner.execution_plan(capabilities()) == active
    clock.now = 120.0
    assert owner.request("retry") is None
    assert owner.outcome == "exhausted"
    assert owner.counters["requests"] == 2


@pytest.mark.parametrize("field", ["cooldown", "wait"])
def test_oversized_config_timing_raises_value_error(field: str) -> None:
    with pytest.raises(ValueError, match="configuration"):
        PlanLifecycle(identity(), FakeClock(), **{field: 10**400})
