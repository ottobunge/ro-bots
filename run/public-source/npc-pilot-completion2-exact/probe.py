"""Finite fixed Bard NEXT pilot; offline tests replace only effect boundaries."""

import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

import guards
from pilot_evidence import RecordingClient, RunEvidence
from pilot_inputs import Inputs, Lock, reviewed_lock

from robots import playing
from robots.adapters.native_vitals import NativeTelemetryUnavailable, require_native_vitals
from robots.adapters.planning_llm import LocalPlanningModel
from robots.app.agent_runtime import AgentHost, ManifestEntry, ScheduledAgent, _raise_cleanup_errors
from robots.app.planning_brain import PlannedBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import GameAction, NpcRespond, TalkToNpc
from robots.domain.model import BotState, Goal
from robots.domain.planning import PhaseKind, PlanningIdentity
from robots.ports import DecisionModel
from robots.ports.planning_model import PlanningModel


def select_actor(client: PlayingClient) -> int:
    state = client.build_native_state(Goal.GRIND)
    actor = received_actor(state, client)
    if actor is None:
        msg = "scenario received actor/readiness unavailable"
        raise ValueError(msg)
    return actor


def received_actor(state: BotState, client: PlayingClient) -> int | None:
    candidates = [
        actor
        for actor in state.nearby
        if actor.kind == "npc" and actor.name == "Bard#brising" and actor.distance <= 3
    ]
    if len(candidates) != 1 or not received_ready(state, client):
        return None
    return candidates[0].id


def received_ready(state: BotState, client: PlayingClient) -> bool:
    return bool(
        state.map_name == "prt_fild08"
        and state.alive_known
        and state.alive is True
        and client._standing is True
        and client._stand_pending is None
        and client._rest_seq is None
        and client._npc_motion_ready()
    )


def startup_vitals(client: PlayingClient) -> dict[str, Any]:
    """Only received/validated flags; never fabricated counts or life authority."""
    parameters = client.wire.status_params
    received = [parameter in parameters for parameter in (5, 6, 7, 8)]
    validated = False
    try:
        require_native_vitals(parameters)
    except NativeTelemetryUnavailable:
        pass
    else:
        validated = True
    return {"received": received, "complete": all(received), "validated": validated}


def startup_snapshot(client: PlayingClient) -> dict[str, Any]:
    """Observe the existing bounded map ring, never queues/auth buffers/raw payloads."""
    wire = client.wire
    epoch, base, frames = wire.native_frame_snapshot()
    latest = [
        {"sequence": sequence, "packet_id": packet}
        for sequence, _at, packet, _raw in frames[-16:]
        if type(sequence) is int and type(packet) is int and 0 <= packet <= 65535
    ]
    return {
        "receive_epoch": epoch if type(epoch) is int else None,
        "frame_base_sequence": base if type(base) is int else None,
        "latest_frames": latest,
        "retained_frame_count": len(frames),
        "vitals": startup_vitals(client),
        **startup_transport(client),
    }


def startup_transport(client: PlayingClient) -> dict[str, Any]:
    """Health flags and error provenance only; native dispatch retains no class."""
    wire = client.wire
    reader = wire.rx_thread
    dispatch = wire.dispatch_errors
    return {
        "running": wire.running is True,
        "connected_map": wire.connected_map is True,
        "socket_present": wire.sock is not None,
        "reader_present": reader is not None,
        "reader_alive": reader is not None and reader.is_alive() is True,
        "closed": client._closed is True,
        "keepalive_failed": client._keepalive_failed is True,
        "rx_error_class": type(wire.rx_error).__name__ if wire.rx_error is not None else None,
        "dispatch_error_count": len(dispatch),
        "dispatch_error_class": None if not dispatch else "unavailable: source retains text only",
        "dispatch_packet_ids": [
            packet
            for packet, _message in dispatch[-16:]
            if type(packet) is int and 0 <= packet <= 65535
        ],
    }


class Budget:
    def __init__(self, deadline: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.deadline, self.clock = deadline, clock
        self.completions = 0
        self.decisions = 0
        self.episodes = 0
        self.poisoned = False
        self.activation_expires: float | None = None

    def check(self) -> None:
        if self.poisoned or self.clock() >= self.deadline:
            self.poisoned = True
            msg = "pilot budget unavailable"
            raise TimeoutError(msg)
        if self.activation_expires is not None and time.time() >= self.activation_expires:
            self.poisoned = True
            msg = "pilot activation expired"
            raise TimeoutError(msg)

    def claim(self, name: str, limit: int) -> None:
        self.check()
        count = getattr(self, name)
        if count >= limit:
            self.poisoned = True
            msg = "pilot provider budget exhausted"
            raise ValueError(msg)
        setattr(self, name, count + 1)


class BoundedPlanning:
    def __init__(self, source: PlanningModel, budget: Budget, evidence: RunEvidence) -> None:
        self.source, self.budget = source, budget
        self.evidence = evidence

    def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.budget.claim("completions", 3)
        if isinstance(self.source, LocalPlanningModel):
            with RecordingClient(self.evidence, self.budget.check) as client:
                self.source.client = client
                try:
                    return self.source.complete(payload)
                finally:
                    self.source.client = None
        return self.source.complete(payload)


class BoundedDecision:
    def __init__(self, source: DecisionModel, budget: Budget) -> None:
        self.source, self.budget = source, budget

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.budget.claim("decisions", 1)
        return self.source.decide(request)


class CleanupBudget(Budget):
    """Readback only; the active provider/action budget remains expired."""

    def claim(self, _name: str, _limit: int) -> None:
        msg = "cleanup cannot authorize providers"
        raise ValueError(msg)


def helper(path: Path, inputs: Inputs, budget: Budget) -> dict[str, Any]:
    if path not in guards.HELPERS:
        msg = "operational helper path refused"
        raise ValueError(msg)
    cleanup = isinstance(budget, CleanupBudget)
    inputs.refresh(cleanup=cleanup)
    budget.check()
    result = subprocess.run(
        [sys.executable, "-B", str(path)],
        cwd=guards.ROOT,
        env=dict(os.environ, PYTHONOPTIMIZE="0", PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        timeout=min(35, budget.deadline - budget.clock()),
        check=False,
    )
    if result.returncode:
        msg = "operational helper refused"
        raise ValueError(msg)
    proof = json.loads(result.stdout)
    flags = ("passed", "read_only", "exact_two_fixture_ownership_verified", "both_fixtures_offline")
    if (
        not isinstance(proof, dict)
        or any(proof.get(key) is not True for key in flags)
        or type(proof.get("all_online_character_count")) is not int
        or proof["all_online_character_count"] != 0
    ):
        msg = "operational helper proof refused"
        raise ValueError(msg)
    inputs.refresh(cleanup=cleanup)
    return proof


class Pilot:
    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs
        self.run_id = uuid.uuid4().hex

        self.evidence: RunEvidence | None = None
        path = Path(inputs.location["private_directory"]).parent / "native-fixture-observer.lock"
        self.lock: Lock = reviewed_lock(path)
        self.host: AgentHost | None = None
        self.budget: Budget | None = None
        self.requests = 0
        self.clicks = 0
        self.actor_id: int | None = None
        self.retained = False
        self.report: dict[str, Any] = {
            "passed": False,
            "native_acceptance": False,
            "quest_or_reward_acceptance": False,
            "provider_result": "unavailable",
            "admission": "unavailable",
            "request": "not issued",
            "ui_progress": False,
            "cleanup": "not attempted",
            "errors": [],
        }

    def _identity(self, client: PlayingClient, entry: ManifestEntry) -> None:
        wire = client.wire
        expected = self.inputs.config["exact_pairs"][entry.persona_id]
        if (wire.aid, wire.gid, wire.char_name) != (*expected, entry.char_name):
            msg = "received fixture identity refused"
            raise ValueError(msg)
        client.build_native_state(Goal.GRIND)

    def _factory(
        self,
        source: Callable[[ManifestEntry], PlayingClient],
        entry: ManifestEntry,
        agent: ScheduledAgent,
    ) -> PlayingClient:
        self.inputs.refresh()
        client = source(entry)
        client.wire.log = lambda _message: None
        connect = client.connect
        perform = client.perform_native

        def connected(*args: Any, **kwargs: Any) -> Any:
            result = self._startup_boundary(
                "native_connect", client, lambda: connect(*args, **kwargs)
            )
            self._scope_transport(client)
            return result

        vars(agent)["_wait_for_telemetry"] = lambda: self._startup_boundary(
            "telemetry_and_fixed_npc",
            client,
            lambda: self._startup_wait(agent, lambda: ScheduledAgent._wait_for_telemetry(agent)),
        )
        vars(client)["connect"] = connected
        vars(client)["perform_native"] = lambda action: self._guarded_perform(
            client, perform, action
        )
        return client

    def _startup_boundary(
        self, stage: str, client: PlayingClient, operation: Callable[[], Any]
    ) -> Any:
        try:
            return operation()
        except BaseException as origin:
            # Diagnostics are best effort, never a substitute failure or cleanup owner.
            with suppress(BaseException):
                self._startup_failure(stage, client, origin)
            raise

    def _startup_failure(self, stage: str, client: PlayingClient, origin: BaseException) -> None:
        try:
            snapshot = startup_snapshot(client)
        except BaseException as diagnostic:
            snapshot = {"diagnostic_error_class": type(diagnostic).__name__}
        self._evidence().private(
            "startup_failure",
            {"stage": stage, "origin_class": type(origin).__name__, "snapshot": snapshot},
        )

    def _scope_transport(self, client: PlayingClient) -> None:
        send = client.wire._send

        def scoped_send(raw: bytes) -> None:
            self.inputs.refresh()
            self._budget().check()
            packet = int.from_bytes(raw[:2], "little")
            npc_id = int.from_bytes(raw[2:6], "little")
            allowed_tick = packet == 0x0360 and len(raw) == 6
            allowed_click = packet == 0x0090 and len(raw) == 7 and raw[6] == 1
            allowed_next = packet == 0x00B9 and len(raw) == 6
            if not allowed_tick and not (
                (allowed_click or allowed_next) and npc_id == self.actor_id
            ):
                msg = "scenario transport packet refused"
                raise ValueError(msg)
            send(raw)

        client.wire._send = scoped_send

    def _prepare_npc(self, client: PlayingClient, entry: ManifestEntry) -> None:
        self._identity(client, entry)
        self.actor_id = select_actor(client)
        client.perform_native(TalkToNpc(self.actor_id))
        deadline = min(self._budget().deadline, time.monotonic() + 10)
        identity = PlanningIdentity(
            entry.persona_id, "ro-bots-test", entry.char_name, client.wire.native_epoch, "pre-re"
        )
        while time.monotonic() < deadline:
            self.inputs.refresh()
            self._budget().check()
            client.drain_native_events()
            observation = client.planning_npc_observation(identity)
            if observation is not None:
                if observation.stage != "next" or observation.npc_id != self.actor_id:
                    msg = "scenario first UI not NEXT"
                    raise ValueError(msg)
                return
            time.sleep(0.01)
        msg = "scenario first UI unavailable"
        raise ValueError(msg)

    def _startup_wait(self, agent: ScheduledAgent, wait: Callable[[], None]) -> None:
        client = agent.client
        if not isinstance(client, PlayingClient):
            msg = "actual startup client unavailable"
            raise ValueError(msg)
        state = agent.build_state

        def ready_state() -> BotState:
            self.inputs.refresh()
            self._budget().check()
            current = state()
            if received_actor(current, client) is None:
                msg = "scenario received actor/readiness unavailable"
                raise NativeTelemetryUnavailable(msg)
            return current

        vars(agent)["build_state"] = ready_state
        try:
            wait()
        finally:
            vars(agent)["build_state"] = state
        self._prepare_npc(client, agent.entry)

    def _budget(self) -> Budget:
        if self.budget is None:
            msg = "pilot not started"
            raise ValueError(msg)
        return self.budget

    def _guarded_perform(
        self, client: PlayingClient, source: Callable[[GameAction], None], action: GameAction
    ) -> None:
        self.inputs.refresh()
        self._budget().check()
        current = select_actor(client)
        if current != self.actor_id:
            msg = "scenario actor changed"
            raise ValueError(msg)
        self._claim_action(action, current)
        source(action)
        if isinstance(action, NpcRespond):
            receipt = client.local_npc_dispatch
            self.report["request"] = receipt.disposition if receipt is not None else "unavailable"

    def _claim_action(self, action: GameAction, current: int) -> None:
        if isinstance(action, TalkToNpc) and self.clicks == 0 and action.npc_id == current:
            self.clicks += 1
        elif isinstance(action, NpcRespond) and self._next_available(action, current):
            self.requests += 1
        else:
            msg = "scenario queued action refused"
            raise ValueError(msg)

    def _next_available(self, action: NpcRespond, current: int) -> bool:
        return bool(
            self.requests == 0
            and action.intent.operation == "next"
            and action.intent.expected_stage == "next"
            and action.intent.npc_id == current
        )

    def _construct(self) -> tuple[ScheduledAgent, PlannedBrain]:
        inputs = self.inputs
        inputs.refresh()
        args = playing.parse_args(
            [
                "--manifest",
                inputs.location["host_manifest"],
                "--runtime-root",
                inputs.config["runtime_root"],
                "--memory-root",
                inputs.location["memory_root"],
                "--decision-url",
                inputs.config["decision_url"],
                "--llm-planning",
                "--planning-world",
                "ro-bots-test",
                "--solo",
            ]
        )
        self.host = playing.build_host(args)
        rows = inputs.manifest["accounts"]
        selected = rows[inputs.authority["fixture_index"]]["persona_id"]
        agent = self.host.agents[selected]
        brain = agent.brain
        if not isinstance(brain, PlannedBrain):
            msg = "actual planned host unavailable"
            raise ValueError(msg)
        budget = self._budget()
        original = brain.model_factory
        evidence = self._evidence()

        def model() -> PlanningModel:
            budget.claim("episodes", 1)
            return BoundedPlanning(original(), budget, evidence)

        brain.model_factory = model
        brain.decision = BoundedDecision(brain.decision, budget)
        source = agent._client_factory
        if not callable(source):
            message = "actual client factory unavailable"
            raise ValueError(message)
        agent._client_factory = lambda entry: self._factory(source, entry, agent)
        agent._threaded = False
        return agent, brain

    def _drive(self) -> None:
        agent, brain = self._construct()
        if not agent.connect():
            msg = "target startup refused"
            raise ValueError(msg)
        self._wait_planning(agent, brain)
        self._require_next_plan(brain)
        self._wait_issuance(agent, brain)
        self._wait_progress(agent, brain)

    def _wait_planning(self, agent: ScheduledAgent, brain: PlannedBrain) -> None:
        while brain.runtime.job is not None:
            self._budget().check()
            agent.tick()
            time.sleep(0.01)
        self.report["provider_result"] = brain.planning_status
        self.report["admission"] = brain.planning_status

    def _require_next_plan(self, brain: PlannedBrain) -> None:
        plan = brain.active_plan
        if plan is not None:
            self._evidence().private("admitted_plan", {"plan": plan})
        if (
            plan is None
            or len(plan.phases) != 1
            or plan.phases[0].kind != PhaseKind.NPC
            or plan.phases[0].npc_intent is None
            or plan.phases[0].npc_intent.operation != "next"
        ):
            msg = "scenario provider proposal denied"
            raise ValueError(msg)

    def _wait_issuance(self, agent: ScheduledAgent, brain: PlannedBrain) -> None:
        while self.report["request"] != "issued":
            self._budget().check()
            agent.tick()
            phase = brain._npc_phase
            if phase is None or phase.status == "failed":
                msg = "scenario response failed"
                raise ValueError(msg)
            time.sleep(0.01)

    def _wait_progress(self, agent: ScheduledAgent, brain: PlannedBrain) -> None:
        while True:
            self._budget().check()
            agent.tick()
            phase = brain._npc_phase
            if phase is None or phase.status == "failed":
                msg = "scenario UI progress unavailable"
                raise ValueError(msg)
            if phase.status == "completed":
                self.report["ui_progress"] = True
                return
            time.sleep(0.01)

    def _evidence(self) -> RunEvidence:
        if self.evidence is None:
            self.evidence = RunEvidence(guards.HERE / "runs" / self.run_id, self.run_id)
        return self.evidence

    def _save(self) -> None:
        self._evidence().public(self.report)

    def _cleanup(self) -> None:
        cleanup = CleanupBudget(time.monotonic() + guards.LIMITS["cleanup_readback_seconds"])
        if self.host is not None:
            self.host.stop()
            if any(
                agent._client_cleanup_pending
                or agent._startup_cleanup_uncertain
                or not agent._planning_reconnect_ready()
                for agent in self.host.agents.values()
            ):
                msg = "physical worker/transport release unconfirmed"
                raise RuntimeError(msg)
        paths = list(guards.HELPERS)
        helper(paths[2], self.inputs, cleanup)
        helper(paths[1], self.inputs, cleanup)
        self.lock.release()
        self.report["cleanup"] = "supported cleanup and exact offline readback"

    def run(self) -> dict[str, Any]:
        self.inputs.refresh()
        if self.budget is not None or self.retained:
            msg = "pilot retry refused"
            raise ValueError(msg)
        self.budget = Budget(time.monotonic() + 90)
        self.budget.activation_expires = float(self.inputs.authority["expires_at"])
        self.lock.acquire()
        failures: list[BaseException] = []
        self._attempt("session", self._session, failures)
        self._attempt("evidence", self._save, failures)
        self._attempt("cleanup", self._cleanup, failures)
        self.report["passed"] = not failures and self.report["ui_progress"] is True
        self._attempt("evidence", self._save, failures)
        if any(not isinstance(error, Exception) for error in failures):
            _raise_cleanup_errors(failures)
        if failures:
            self.report["passed"] = False
        return self.report

    def _session(self) -> None:
        helper(list(guards.HELPERS)[1], self.inputs, self._budget())
        self._drive()

    def _attempt(
        self, stage: str, operation: Callable[[], None], failures: list[BaseException]
    ) -> None:
        try:
            operation()
        except BaseException as error:
            failures.append(error)
            if stage == "cleanup":
                self.retained = True
                self.report["cleanup"] = "release unconfirmed; owner retained; no retry"
            self.report["errors"].append({"stage": stage, "type": type(error).__name__})
