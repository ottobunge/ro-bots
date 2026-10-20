"""Offline plan data, not native mechanics/resource authority.

Map, target and duration concepts follow FarmPlan without importing legacy models.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


def bounded_text(value: str, limit: int = 256) -> bool:
    if not isinstance(value, str) or "\x00" in value or not value.strip():
        return False
    try:
        return len(value.encode("utf-8")) <= limit
    except UnicodeEncodeError:
        return False


def positive_number(value: float) -> bool:
    return type(value) in (int, float) and 0 < value <= 86400 and isfinite(value)


class PhaseKind(StrEnum):
    TRAVEL = "travel"
    GRIND = "grind"
    FARM = "farm"
    REST = "rest"
    IDLE = "idle"
    NPC = "npc"


class ObservableCondition(StrEnum):
    ARRIVED = "arrived"
    XP_GAINED = "xp gained"
    ITEM_GAINED = "item gained"
    RECOVERED = "recovered"
    HEALTH_IMPROVES = "health improves"
    WAIT_COMPLETE = "wait complete"
    NPC_UI_ADVANCED = "npc ui advanced"


class ReplanCondition(StrEnum):
    DANGER = "danger"
    NO_PROGRESS = "no progress"
    PREREQUISITE_LOST = "prerequisite lost"
    REVIEW_DUE = "review due"


@dataclass(frozen=True, slots=True)
class PlanningIdentity:
    agent: str
    world: str
    character: str
    session_epoch: int
    ruleset: str

    def __post_init__(self) -> None:
        values = (self.agent, self.world, self.character, self.ruleset)
        if (
            any(
                not isinstance(v, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", v) is None
                for v in values
            )
            or type(self.session_epoch) is not int
            or self.session_epoch < 0
        ):
            message = "invalid planning identity"
            raise ValueError(message)


class NpcOperation(StrEnum):
    NEXT = "next"
    CHOOSE = "choose"


def npc_binding_valid(npc_id: int, epoch: int, map_name: str, opened: int, prompt: int) -> bool:
    return (
        type(npc_id) is int
        and 1 <= npc_id <= 0xFFFFFFFF
        and type(epoch) is int
        and epoch >= 0
        and isinstance(map_name, str)
        and re.fullmatch(r"[A-Za-z0-9_]{1,32}", map_name) is not None
        and type(opened) is int
        and type(prompt) is int
        and 0 <= opened < prompt
    )


@dataclass(frozen=True, slots=True)
class NpcIntent:
    """One bound received-prompt response, not native dispatch authority."""

    operation: NpcOperation
    npc_id: int
    epoch: int
    map_name: str
    opened_sequence: int
    prompt_sequence: int
    expected_stage: str
    option_index: int | None = None

    def valid(self) -> bool:
        binding = npc_binding_valid(
            self.npc_id, self.epoch, self.map_name, self.opened_sequence, self.prompt_sequence
        )
        return binding and npc_response_valid(
            self.operation, self.expected_stage, self.option_index
        )


@dataclass(frozen=True, slots=True)
class Phase:
    kind: PhaseKind
    map_name: str
    destination: tuple[int, int] | None = None
    public_species: int | None = None
    public_item: int | None = None
    npc_intent: NpcIntent | None = None

    def valid(self) -> bool:
        return targets_valid(self) and destination_valid(self) and npc_phase_valid(self)


@dataclass(frozen=True, slots=True)
class NpcObservation:
    """Caller-owned receipt/readiness summary, never model or native permission.

    Times are finite caller monotonic readings, not protocol/host response timers.
    Option indices are the exact received menu indices, not inferred text choices.
    """

    identity: PlanningIdentity
    npc_id: int
    epoch: int
    map_name: str
    opened_sequence: int
    prompt_sequence: int
    stage: str
    option_indices: tuple[int, ...] = ()
    ready: bool = False
    observed_at: float = 0.0
    expires_at: float = 0.0

    def eligible(self, identity: PlanningIdentity, now: float) -> bool:
        checks = (
            isinstance(self.identity, PlanningIdentity) and self.identity == identity,
            self.epoch == identity.session_epoch,
            npc_binding_valid(
                self.npc_id, self.epoch, self.map_name, self.opened_sequence, self.prompt_sequence
            ),
            self.ready is True,
            npc_options_valid(self.stage, self.option_indices),
            npc_receipt_time_valid(self.observed_at, self.expires_at, now),
        )
        return all(checks)


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Caller observations, never model-authored ownership/native permission.

    Fresh facts must describe current observations, not public build advice.
    The caller recomputes this summary before admission/action revalidation.
    """

    supported: frozenset[PhaseKind]
    known_maps: frozenset[str]
    fresh_facts: frozenset[str]
    npc_observation: NpcObservation | None = None


@dataclass(frozen=True, slots=True)
class ProposedPlan:
    identity: PlanningIdentity
    objective: str
    reason: str
    phases: tuple[Phase, ...]
    success: ObservableCondition
    progress: ObservableCondition
    duration: float
    review_at: float
    fallback: PhaseKind
    replan_conditions: tuple[ReplanCondition, ...]
    required_facts: frozenset[str] = frozenset()
    safety_stop_conditions: tuple[ReplanCondition, ...] = (
        ReplanCondition.DANGER,
        ReplanCondition.PREREQUISITE_LOST,
    )

    def denial(self, capabilities: Capabilities, now: float) -> str | None:
        checks = (
            (plan_shape_valid(self) and self.fallback in capabilities.supported, "shape"),
            (plan_timing_valid(self, now), "timing"),
            (phases_supported(self, capabilities), "unsupported"),
            (prerequisites_known(self, capabilities), "unknown-prerequisite"),
            (npc_receipt_matches(self, capabilities, now), "npc-receipt"),
        )
        return next((reason for valid, reason in checks if not valid), None)


@dataclass(frozen=True, slots=True)
class PlanningRequest:
    token: str
    identity: PlanningIdentity
    base_version: int
    reasons: tuple[str, ...]
    deadline: float


def targets_valid(phase: Phase) -> bool:
    return all(
        target is None or (type(target) is int and target > 0)
        for target in (phase.public_species, phase.public_item)
    )


def destination_valid(phase: Phase) -> bool:
    if phase.destination is None:
        return phase.kind != PhaseKind.TRAVEL
    return (
        isinstance(phase.destination, tuple)
        and len(phase.destination) == 2
        and all(type(value) is int and 0 <= value <= 1023 for value in phase.destination)
    )


def conditions_valid(plan: ProposedPlan) -> bool:
    sequences = (plan.replan_conditions, plan.safety_stop_conditions)
    return all(isinstance(values, tuple) and 1 <= len(values) <= 8 for values in sequences) and all(
        isinstance(value, ReplanCondition) for values in sequences for value in values
    )


def phases_valid(plan: ProposedPlan) -> bool:
    return (
        isinstance(plan.phases, tuple)
        and 1 <= len(plan.phases) <= 8
        and all(phase.valid() for phase in plan.phases)
    )


def plan_shape_valid(plan: ProposedPlan) -> bool:
    checks = (
        all(bounded_text(text) for text in (plan.objective, plan.reason)),
        all(isinstance(value, ObservableCondition) for value in (plan.success, plan.progress)),
        isinstance(plan.fallback, PhaseKind) and plan.fallback in (PhaseKind.IDLE, PhaseKind.REST),
        phases_valid(plan),
        conditions_valid(plan),
        facts_valid(plan.required_facts),
        npc_plan_shape_valid(plan),
    )
    return all(checks)


def plan_timing_valid(plan: ProposedPlan, now: float) -> bool:
    return (
        positive_number(plan.duration)
        and type(plan.review_at) in (int, float)
        and now < plan.review_at <= now + plan.duration
        and positive_number(plan.review_at - now)
    )


def phases_supported(plan: ProposedPlan, capabilities: Capabilities) -> bool:
    return all(
        isinstance(phase.kind, PhaseKind)
        and phase.kind in capabilities.supported
        and phase.map_name in capabilities.known_maps
        for phase in plan.phases
    )


def facts_valid(facts: frozenset[str]) -> bool:
    return (
        isinstance(facts, frozenset)
        and len(facts) <= 8
        and all(bounded_text(fact, 96) for fact in facts)
    )


def prerequisites_known(plan: ProposedPlan, capabilities: Capabilities) -> bool:
    needed = set(plan.required_facts)
    requirements = {
        PhaseKind.TRAVEL: {"navigation"},
        PhaseKind.GRIND: {"vitals"},
        PhaseKind.FARM: {"vitals", "inventory"},
        PhaseKind.REST: {"vitals"},
    }
    for phase in plan.phases:
        needed.update(requirements.get(phase.kind, set()))
    return needed <= capabilities.fresh_facts


def npc_phase_valid(phase: Phase) -> bool:
    intent = phase.npc_intent
    if phase.kind != PhaseKind.NPC:
        return intent is None
    return (
        isinstance(intent, NpcIntent)
        and intent.valid()
        and intent.map_name == phase.map_name
        and all(v is None for v in (phase.destination, phase.public_species, phase.public_item))
    )


def finite_clock(value: float) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def npc_receipt_time_valid(observed: float, expires: float, now: float) -> bool:
    return all(finite_clock(v) for v in (observed, expires, now)) and observed <= now < expires


def npc_options_valid(stage: str, indices: tuple[int, ...]) -> bool:
    if not isinstance(indices, tuple) or len(indices) > 254:
        return False
    if stage == "next":
        return indices == ()
    return (
        stage == "menu"
        and bool(indices)
        and all(type(index) is int and 1 <= index <= 254 for index in indices)
        and len(set(indices)) == len(indices)
    )


def npc_receipt_matches(plan: ProposedPlan, capabilities: Capabilities, now: float) -> bool:
    for phase in plan.phases:
        if phase.kind == PhaseKind.NPC and not npc_intent_matches(
            phase.npc_intent, capabilities.npc_observation, plan.identity, now
        ):
            return False
    return True


def npc_intent_matches(
    intent: NpcIntent | None,
    observation: NpcObservation | None,
    identity: PlanningIdentity,
    now: float,
) -> bool:
    if not isinstance(intent, NpcIntent) or not isinstance(observation, NpcObservation):
        return False
    if not intent.valid() or not observation.eligible(identity, now):
        return False
    fields = ("npc_id", "epoch", "map_name", "opened_sequence", "prompt_sequence")
    checks = (
        all(getattr(intent, field) == getattr(observation, field) for field in fields),
        intent.expected_stage == observation.stage,
        intent.option_index is None or intent.option_index in observation.option_indices,
    )
    return all(checks)


def npc_plan_shape_valid(plan: ProposedPlan) -> bool:
    conditions = (plan.success, plan.progress)
    if not any(phase.kind == PhaseKind.NPC for phase in plan.phases):
        return ObservableCondition.NPC_UI_ADVANCED not in conditions
    return len(plan.phases) == 1 and all(
        condition is ObservableCondition.NPC_UI_ADVANCED for condition in conditions
    )


def npc_response_valid(operation: object, stage: str, index: int | None) -> bool:
    if not isinstance(operation, NpcOperation):
        return False
    if operation is NpcOperation.NEXT:
        return stage == "next" and index is None
    return stage == "menu" and type(index) is int and 1 <= index <= 254
