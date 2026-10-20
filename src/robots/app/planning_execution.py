"""Host-owned REST mechanics; pose requests are not acceptance or progress."""

from dataclasses import dataclass
from enum import StrEnum

from robots.domain.actions import GameAction, Rest
from robots.domain.model import BotState
from robots.domain.planning import ObservableCondition, PlanningIdentity, ProposedPlan


@dataclass(frozen=True)
class RestObservation:
    epoch: int
    sequence: int
    standing: bool | None
    pose_sequence: int
    vitals: tuple[int, int, int, int] | None
    vitals_sequence: int
    arrival_ready: bool = False


def _valid_quartet(state: BotState, observation: RestObservation) -> bool:
    quartet = (state.hp, state.max_hp, state.sp, state.max_sp)
    return (
        all(type(value) is int for value in quartet)
        and 0 <= state.hp <= state.max_hp
        and state.max_hp > 0
        and 0 <= state.sp <= state.max_sp
        and observation.vitals == quartet
        and observation.vitals_sequence > 0
    )


def rest_eligible(state: BotState, observation: RestObservation | None) -> bool:
    skills = state.received_skills
    if observation is None or skills is None or skills.rows is None:
        return False
    valid = (
        _valid_quartet(state, observation)
        and observation.epoch == state.native_epoch == skills.epoch
        and type(skills.sequence) is int
        and 0 <= skills.sequence <= observation.sequence
    )
    return valid and any(
        skill.level >= {1: 3, 5018: 1}.get(skill.id, 65536) for skill in skills.rows
    )


def rest_semantics(plan: ProposedPlan, state: BotState, index: int) -> bool:
    phase = plan.phases[index]
    allowed = {ObservableCondition.RECOVERED, ObservableCondition.HEALTH_IMPROVES}
    return (
        phase.kind.value == "rest"
        and phase.map_name == state.map_name
        and phase.destination is None
        and plan.success in allowed
        and plan.progress in allowed
    )


class RestPhase(StrEnum):
    REQUEST = "rest request"
    HOLD = "rest hold"
    STAND = "stand wait"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass
class RestHold:
    identity: PlanningIdentity
    version: int
    phase_index: int
    map_name: str
    baseline: RestObservation
    success: ObservableCondition
    started: float
    last_progress: float
    phase: RestPhase = RestPhase.REQUEST
    stand_barrier: int | None = None
    stand_started: float | None = None
    failure: str | None = None
    replan_requested: bool = False
    stand_required: bool = False
    attempts: int = 0
    last_attempt: float | None = None
    progress_values: tuple[int, int] | None = None
    progress_sequence: int = 0

    def step(self, observation: RestObservation, now: float) -> tuple[GameAction, ...]:
        if self.phase == RestPhase.FAILED:
            if self.stand_barrier is None:
                self.stand_barrier = observation.sequence
                self.stand_started = now
            self._stand(observation, now)
            return ()
        if self.phase == RestPhase.STAND:
            self._stand(observation, now)
            return ()
        if self.phase in (RestPhase.FAILED, RestPhase.FINISHED):
            return ()
        self._progress(observation, now)
        if observation.pose_sequence > self.baseline.sequence and observation.standing is False:
            self.phase = RestPhase.HOLD
        if self.phase == RestPhase.HOLD:
            self._hold(observation, now)
            return ()
        return self._request(now)

    def _stand(self, observation: RestObservation, now: float) -> None:
        if (
            self.stand_barrier is not None
            and observation.pose_sequence > self.stand_barrier
            and observation.pose_sequence <= observation.sequence
            and observation.standing is True
            and observation.arrival_ready
        ):
            self.phase = RestPhase.FINISHED
        elif self.stand_started is not None and now - self.stand_started >= 3:
            self.failure = "stand receipt timeout"

    def _hold(self, observation: RestObservation, now: float) -> None:
        if self._success(observation):
            self.phase = RestPhase.STAND
            self.stand_barrier = observation.sequence
            self.stand_started = now
        elif now - self.last_progress >= 30:
            self.phase = RestPhase.FAILED
            self.failure = "no health/SP progress"
            self.stand_required = observation.standing is False
            self.stand_barrier = observation.sequence
            self.stand_started = now

    def _request(self, now: float) -> tuple[GameAction, ...]:
        if now - self.started >= 3:
            self.phase = RestPhase.FAILED
            self.failure = "sit receipt timeout"
        elif self.attempts < 3 and (self.last_attempt is None or now - self.last_attempt >= 1):
            self.last_attempt = now
            self.attempts += 1
            return (Rest(),)
        return ()

    def _progress(self, observation: RestObservation, now: float) -> None:
        if observation.vitals is None or observation.vitals_sequence <= self.progress_sequence:
            return
        values = (observation.vitals[0], observation.vitals[2])
        previous = self.progress_values
        if previous is not None and (values[0] > previous[0] or values[1] > previous[1]):
            self.last_progress = now
        self.progress_values = values
        self.progress_sequence = observation.vitals_sequence

    def _success(self, observation: RestObservation) -> bool:
        values, baseline = observation.vitals, self.baseline.vitals
        if values is None or baseline is None:
            return False
        if self.success == ObservableCondition.HEALTH_IMPROVES:
            return observation.vitals_sequence > self.baseline.vitals_sequence and (
                values[0] > baseline[0] or values[2] > baseline[2]
            )
        return values[0] >= values[1] * 0.75 and (values[3] == 0 or values[2] >= values[3] * 0.75)
