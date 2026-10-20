"""Opt-in IDLE/REST and receipt-bound NPC mechanics with event-only review."""

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from robots.app.brain import TickResult
from robots.app.execution_decisions import ExecutionJob, ExecutionRuntime, execution_request
from robots.app.npc_planning_execution import (
    LocalNpcDispatch,
    NpcPhase,
    NpcUiObservation,
    execution_event_allowed,
    execution_event_data,
)
from robots.app.planning_context import ObservationSnapshot
from robots.app.planning_execution import (
    RestHold,
    RestObservation,
    RestPhase,
    rest_eligible,
    rest_semantics,
)
from robots.app.planning_job_context import capture_job_context
from robots.app.planning_runtime import PlanningRuntime
from robots.app.scripts import ScriptOutcome, ScriptStatus
from robots.domain.actions import GameAction, NpcRespond
from robots.domain.events import (
    Heartbeat,
    NpcDialogueReceived,
    WorldEvent,
)
from robots.domain.model import BotState
from robots.domain.planning import (
    Capabilities,
    NpcObservation,
    PhaseKind,
    PlanningIdentity,
    ProposedPlan,
)
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.ports import DecisionModel
from robots.ports.planning_model import PlanningModel
from robots.society.memory import Memory

if TYPE_CHECKING:
    from robots.domain.farm import FarmPlan


class PlannedBrain:
    def __init__(
        self,
        identity: PlanningIdentity,
        memory: Memory,
        decision: DecisionModel,
        model_factory: Callable[[], PlanningModel],
    ) -> None:
        self.identity = identity
        self.memory = memory
        self.decision = decision
        self.model_factory = model_factory
        self.runtime = PlanningRuntime(identity)
        self.execution = ExecutionRuntime()
        self._bound = False
        self._request_failure_version = -1
        self._pose_reader: Callable[[], RestObservation] | None = None
        self._rest_hold: RestHold | None = None
        self._npc_reader: Callable[[PlanningIdentity], NpcObservation | None] | None = None
        self._npc_phase: NpcPhase | None = None
        self._npc_ui_reader: Callable[[PlanningIdentity], NpcUiObservation | None] | None = None

    @property
    def mechanical_fallback_allowed(self) -> bool:
        return False

    @property
    def is_recovering(self) -> bool:
        return self._rest_hold is not None and self._rest_hold.phase != RestPhase.FINISHED

    @property
    def current_plan(self) -> FarmPlan | None:
        return None

    @property
    def reconnect_ready(self) -> bool:
        return self.runtime.job is None and self.execution.job is None

    @property
    def active_plan(self) -> ProposedPlan | None:
        return self.runtime.lifecycle.active

    @property
    def planning_status(self) -> str:
        if self.runtime.lifecycle.pending is not None:
            return "pending"
        return self.runtime.lifecycle.outcome

    def bind_session(
        self,
        clock: Callable[[], float],
        pose_reader: Callable[[], RestObservation] | None = None,
        npc_reader: Callable[[PlanningIdentity], NpcObservation | None] | None = None,
        npc_ui_reader: Callable[[PlanningIdentity], NpcUiObservation | None] | None = None,
    ) -> None:
        self.invalidate_binding()
        if not self.reconnect_ready:
            message = "planning worker release unconfirmed"
            raise RuntimeError(message)
        self.runtime.invalidate()
        self.runtime.clock = clock
        self.execution.invalidate()
        self._pose_reader = pose_reader
        self._rest_hold = None
        self._npc_reader = npc_reader
        self._npc_phase = None
        self._npc_ui_reader = npc_ui_reader
        self._bound = True

    def _received_context(self, state: BotState) -> bool:
        return (
            self._bound
            and type(state.native_epoch) is int
            and state.native_epoch > 0
            and state.progression_source != "legacy"
            and state.name == self.identity.character
            and bool(state.map_name)
            and state.alive_known
            and state.alive is True
        )

    def invalidate_binding(self) -> None:
        self._bound = False
        self._npc_reader = None
        self._npc_ui_reader = None
        self._npc_phase = None
        self.sync_context(None)

    def npc_action_current(self, action: NpcRespond) -> bool:
        phase = self._npc_phase
        if phase is None or not self._bound:
            return False
        return all(
            (
                phase.queued_for(action, self.identity, self.runtime.lifecycle.version),
                self.runtime.lifecycle.execution_plan() is not None,
                self.runtime.lifecycle.pending is None,
                self.execution.job is None,
                self.execution.choice == "continue",
                self.execution.choice_version == phase.version,
            )
        )

    @staticmethod
    def _fresh_vitals(state: BotState) -> bool:
        return (
            type(state.max_hp) is int
            and state.max_hp > 0
            and type(state.hp) is int
            and 0 <= state.hp <= state.max_hp
        )

    def _capabilities(self, state: BotState) -> Capabilities:
        valid = self._received_context(state) and self._fresh_vitals(state)
        supported = {PhaseKind.IDLE} if valid else set()
        observation = self._pose_reader() if valid and self._pose_reader else None
        if valid and rest_eligible(state, observation):
            supported.add(PhaseKind.REST)
        npc = self._received_npc(valid)
        if npc is not None:
            supported.add(PhaseKind.NPC)
        return Capabilities(
            frozenset(supported),
            frozenset({state.map_name}) if valid else frozenset(),
            frozenset({"vitals"}) if valid else frozenset(),
            npc,
        )

    def _received_npc(self, valid: bool) -> NpcObservation | None:
        if not valid or self._npc_reader is None:
            return None
        observation = self._npc_reader(self.identity)
        if observation is None or not observation.eligible(self.identity, self.runtime.clock()):
            return None
        return observation

    def start(self, state: BotState) -> TickResult:
        if type(state.native_epoch) is int and state.native_epoch > 0:
            self.identity = replace(self.identity, session_epoch=state.native_epoch)
            self.runtime.lifecycle.update_identity(self.identity)
        caps = self._capabilities(state)
        if not caps.supported or state.native_epoch is None:
            message = "planning context unavailable"
            raise RuntimeError(message)
        self.identity = replace(self.identity, session_epoch=state.native_epoch)
        self.runtime.lifecycle.update_identity(self.identity)
        self.request_replan(state, "start")
        return TickResult((), {})

    def request_replan(self, state: BotState, reason: str) -> None:
        caps = self._capabilities(state)
        if not caps.supported:
            return
        public = state.public_skill_knowledge or PublicSkillKnowledge(self.identity.ruleset, ())
        reader = capture_job_context(
            self.identity, ObservationSnapshot(self.identity, state, caps), public, self.memory.log
        )
        if reader is None:
            message = "planning context unavailable"
            raise RuntimeError(message)
        self.runtime.request(reason, reader, self.model_factory)

    def sync_context(self, state: BotState | None) -> None:
        if state is None:
            self._rest_hold = None
            self._npc_phase = None
            self.runtime.invalidate()
            self.execution.invalidate()
            return
        if type(state.native_epoch) is int and state.native_epoch > 0:
            identity = replace(self.identity, session_epoch=state.native_epoch)
            self.identity = identity
            self.runtime.lifecycle.update_identity(identity)
        caps = self._capabilities(state)
        self.runtime.poll(caps)
        self._observe_npc(state)
        if self.runtime.lifecycle.execution_plan(caps) is None and not self._npc_waiting(state):
            self.runtime.lifecycle.active = None
        self._poll_execution(state)
        self._install_npc(state)

    def _install_npc(self, state: BotState) -> None:
        plan = self.active_plan
        if plan is None or plan.phases[0].kind != PhaseKind.NPC:
            return
        if (
            self._npc_phase is not None
            and self._npc_phase.version == self.runtime.lifecycle.version
        ):
            return
        intent = plan.phases[0].npc_intent
        observation = self._capabilities(state).npc_observation
        if intent is not None and state.npc_dialogue is not None and observation is not None:
            self._npc_phase = NpcPhase(
                plan.identity, self.runtime.lifecycle.version, intent, observation
            )
            self.handle_event(state, NpcDialogueReceived(state.npc_dialogue))

    def _observe_npc(self, state: BotState) -> None:
        phase = self._npc_phase
        if phase is None:
            return
        if phase.version != self.runtime.lifecycle.version:
            if phase.status != "completed":
                phase.status = "failed"
                phase.failure = "admitted NPC version or identity changed"
            self._npc_phase = None
            return
        observation = self._npc_ui_reader(self.identity) if self._npc_ui_reader else None
        if not self._received_context(state) or self.runtime.lifecycle.execution_plan() is None:
            observation = None
        phase.observe(observation)
        if phase.failure is not None and not phase.replan_requested:
            phase.replan_requested = True
            self.execution.choice = "hold"
            self.execution.choice_version = phase.version
            self.request_replan(state, "NPC phase failure")

    def _npc_waiting(self, state: BotState) -> bool:
        phase = self._npc_phase
        plan = self.runtime.lifecycle.execution_plan()
        return (
            phase is not None
            and phase.status == "waiting"
            and plan is not None
            and phase.version == self.runtime.lifecycle.version
            and phase.identity == self.identity == plan.identity
            and self._received_context(state)
            and state.map_name == phase.intent.map_name
        )

    def npc_dispatched(self, action: NpcRespond, receipt: LocalNpcDispatch | None) -> None:
        if self._npc_phase is not None:
            self._npc_phase.dispatched(action, receipt)

    def _poll_execution(self, state: BotState) -> None:
        pending = self.execution.job
        current = pending is not None and self._execution_current(pending, state)
        expired = self.execution.timeout(self.runtime.clock(), current=current)
        if expired is not None and current:
            self.execution.counters["replans"] += 1
            self.request_replan(state, "CLEF execution timeout")
        job = self.execution.finished()
        if job is None:
            return
        if job.error is not None and not isinstance(job.error, Exception):
            raise job.error
        if not self._execution_current(job, state):
            self.execution.counters["stale"] += 1
            return
        if self.execution.apply(job):
            self.execution.counters["replans"] += 1
            self.request_replan(state, "CLEF execution review")

    def _execution_current(self, job: ExecutionJob, state: BotState) -> bool:
        plan = self.runtime.lifecycle.execution_plan(self._capabilities(state))
        return (
            self.execution.matches(job, plan, self.runtime.lifecycle.version)
            and job.plan.identity == self.identity
            and state.native_epoch == job.plan.identity.session_epoch
            and state.map_name == job.plan.phases[0].map_name
        )

    def wait_for_worker(self, timeout: float) -> None:
        self.runtime.wait_for_worker(timeout)

    def close(self) -> None:
        self._bound = False
        self._npc_phase = None
        self._npc_reader = None
        self._npc_ui_reader = None
        failures: list[BaseException] = []
        for runtime in (self.runtime, self.execution):
            try:
                runtime.close()
            except BaseException as error:
                failures.append(error)
        if failures:
            raise next(
                (error for error in failures if not isinstance(error, Exception)), failures[0]
            )

    def handle_event(self, state: BotState, event: WorldEvent) -> TickResult:
        if self._request_failure_version == self.runtime.lifecycle.version:
            return TickResult((), {})
        try:
            return self._handle_execution_event(state, event)
        except Exception:
            self._hold_request_failure()
            return TickResult((), {})
        except BaseException:
            self._hold_request_failure()
            raise

    def _hold_request_failure(self) -> None:
        self._request_failure_version = self.runtime.lifecycle.version
        self.execution.choice = "hold"
        self.execution.choice_version = self.runtime.lifecycle.version

    def _handle_execution_event(self, state: BotState, event: WorldEvent) -> TickResult:
        plan = self.runtime.lifecycle.execution_plan(self._capabilities(state))
        if plan is None or not execution_event_allowed(plan, event):
            return TickResult((), {})
        observation = self._pose_reader() if self._pose_reader else None
        if observation is None or observation.epoch != state.native_epoch:
            return TickResult((), {})
        key, event_data = self._execution_event_key(plan, event, observation.sequence)
        if self.execution.event_seen(key, type(event).__name__):
            return TickResult((), {})
        public = state.public_skill_knowledge or PublicSkillKnowledge(self.identity.ruleset, ())
        reader = capture_job_context(
            self.identity,
            ObservationSnapshot(self.identity, state, self._capabilities(state)),
            public,
            self.memory.log,
        )
        if reader is None:
            message = "execution capture unavailable"
            raise ValueError(message)

        request = execution_request(
            plan,
            self.runtime.lifecycle.version,
            reader,
            {"kind": type(event).__name__, "data": event_data},
        )
        job = ExecutionJob(
            plan,
            self.runtime.lifecycle.version,
            self.execution.generation,
            self.runtime.clock(),
            request,
        )
        self.execution.dispatch(job, self.decision.decide)
        return TickResult((), {})

    def _execution_event_key(
        self, plan: ProposedPlan, event: WorldEvent, sequence: int
    ) -> tuple[tuple[object, ...], str]:
        event_data = execution_event_data(event)
        if len(event_data.encode("utf-8")) > 4096:
            message = "execution event budget exceeded"
            raise ValueError(message)
        marker = event.seq if isinstance(event, Heartbeat) else (sequence, event_data)
        key = (plan.identity, self.runtime.lifecycle.version, type(event).__name__, marker)
        return key, event_data

    def step_script(self, state: BotState, *, can_resume: bool = True) -> ScriptOutcome:
        del can_resume
        npc_outcome = self._step_npc(state)
        if npc_outcome is not None:
            return npc_outcome
        observation = self._pose_reader() if self._pose_reader else None
        if observation is None:
            return ScriptOutcome((), ScriptStatus.ACTIVE)
        self._install_rest(state, observation)
        hold = self._rest_hold
        if hold is None:
            return ScriptOutcome((), ScriptStatus.ACTIVE)
        actions = self._rest_actions(state, observation, hold)
        if (
            hold.failure is not None
            and not hold.replan_requested
            and (self.runtime.clock() - hold.started >= 10)
        ):
            hold.replan_requested = True
            self.request_replan(state, "REST mechanical failure")
        return ScriptOutcome(actions, ScriptStatus.ACTIVE)

    def _step_npc(self, state: BotState) -> ScriptOutcome | None:
        plan = self.runtime.lifecycle.execution_plan(self._capabilities(state))
        if plan is None or plan.phases[0].kind != PhaseKind.NPC:
            return None
        phase = self._npc_phase
        actions = (
            phase.request(
                self.execution.choice,
                self.execution.choice_version,
                pending=self.execution.job is not None
                or self.runtime.lifecycle.pending is not None,
            )
            if phase is not None
            else ()
        )
        return ScriptOutcome(actions, ScriptStatus.ACTIVE)

    def _install_rest(self, state: BotState, observation: RestObservation) -> None:
        plan = self.active_plan
        hold = self._rest_hold
        if (
            hold is not None
            and hold.phase == RestPhase.FINISHED
            and hold.version != self.runtime.lifecycle.version
        ):
            self._rest_hold = None
        if self._rest_hold is not None or plan is None:
            return
        if rest_semantics(plan, state, 0) and rest_eligible(state, observation):
            now = self.runtime.clock()
            self._rest_hold = RestHold(
                plan.identity,
                self.runtime.lifecycle.version,
                0,
                state.map_name,
                observation,
                plan.success,
                now,
                now,
            )

    def _rest_actions(
        self, state: BotState, observation: RestObservation, hold: RestHold
    ) -> tuple[GameAction, ...]:
        if not self._rest_session_valid(state, observation, hold):
            self._rest_hold = None
            return ()
        if hold.failure is not None or hold.phase == RestPhase.STAND:
            return hold.step(observation, self.runtime.clock())
        if state.map_name != hold.map_name or not rest_eligible(state, observation):
            hold.phase = RestPhase.FAILED
            hold.failure = "received prerequisite lost"
            hold.stand_required = observation.standing is False
            return hold.step(observation, self.runtime.clock())
        if not self._rest_plan_valid(state, hold):
            hold.phase = RestPhase.FAILED
            hold.failure = "REST map or semantics lost"
            return ()
        if self._execution_paused(hold, observation):
            return ()
        actions = hold.step(observation, self.runtime.clock())
        if hold.phase == RestPhase.FAILED and hold.stand_barrier is None:
            hold.stand_barrier = observation.sequence
            hold.stand_started = self.runtime.clock()
        return actions

    def _execution_paused(self, hold: RestHold, observation: RestObservation) -> bool:
        return (
            self.execution.pauses_request(hold.version)
            and hold.phase == RestPhase.REQUEST
            and observation.standing is not False
        )

    def _rest_plan_valid(self, state: BotState, hold: RestHold) -> bool:
        plan = self.active_plan
        if (
            plan is None
            or plan.identity != hold.identity
            or self.runtime.lifecycle.version != hold.version
        ):
            return True
        return rest_semantics(plan, state, hold.phase_index)

    def _rest_session_valid(
        self, state: BotState, observation: RestObservation, hold: RestHold
    ) -> bool:
        return (
            self._received_context(state)
            and hold.identity == self.identity
            and observation.epoch == hold.identity.session_epoch
        )

    @property
    def stand_barrier(self) -> int | None:
        hold = self._rest_hold
        if hold is None:
            return None
        if hold.phase == RestPhase.STAND or (
            hold.phase == RestPhase.FAILED and hold.stand_required
        ):
            return hold.stand_barrier
        return None

    def current_script(self) -> object | None:
        return None

    def recovery_health_ready(self, state: BotState) -> bool:
        del state
        return False

    @property
    def required_recovery_hp_ratio(self) -> float:
        return 0.9
