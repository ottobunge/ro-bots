"""One physical planning job, owned independently of logical request expiry."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from robots.app.llm_planner import LlmPlanner
from robots.app.plan_lifecycle import PlanLifecycle
from robots.app.planning_context import InvestigationReader
from robots.domain.planning import Capabilities, PlanningIdentity, PlanningRequest, ProposedPlan
from robots.ports.planning_model import PlanningModel


@dataclass
class PlanningJob:
    request: PlanningRequest
    reader: InvestigationReader
    generation: int
    result: ProposedPlan | None = None
    error: BaseException | None = None
    thread: threading.Thread | None = None
    dispatch_guard: threading.Lock = field(default_factory=threading.Lock)
    dispatched: bool = False
    cancelled: bool = False


def _propose_job(
    job: PlanningJob, factory: Callable[[], PlanningModel], clock: Callable[[], float]
) -> None:
    try:
        with job.dispatch_guard:
            if job.cancelled:
                return
            job.dispatched = True
        job.result = LlmPlanner(factory(), job.reader, clock).propose(job.request, job.reader)
    except BaseException as error:
        job.error = error


class PlanningRuntime:
    def __init__(self, identity: PlanningIdentity) -> None:
        self.clock: Callable[[], float] = time.monotonic
        self.lifecycle = PlanLifecycle(identity, self.now, wait=120)
        self.job: PlanningJob | None = None
        self.generation = 0

    def now(self) -> float:
        return self.clock()

    def request(
        self, reason: str, reader: InvestigationReader, factory: Callable[[], PlanningModel]
    ) -> None:
        if self.job is not None:
            if reason not in self.lifecycle.reasons and len(self.lifecycle.reasons) < 8:
                self.lifecycle.reasons += (reason,)
            return
        request = self.lifecycle.request(reason)
        if request is None:
            return
        job = PlanningJob(request, reader, self.generation)
        job.thread = threading.Thread(
            target=_propose_job, args=(job, factory, self.clock), name="planning-job", daemon=False
        )
        self.job = job
        job.thread.start()

    def poll(self, capabilities: Capabilities) -> None:
        self.lifecycle.poll()
        job = self.job
        if job is None or job.thread is None:
            return
        job.thread.join(0)
        if job.thread.is_alive():
            return
        self.job = None
        if job.error is not None:
            if not isinstance(job.error, Exception):
                raise job.error
            self.lifecycle.pending = None
            self.lifecycle.outcome = "planning denied"
        elif job.result is not None and job.generation == self.generation:
            self.lifecycle.admit(job.request, job.result, capabilities)
        else:
            self.lifecycle.outcome = "stale"

    def invalidate(self) -> None:
        job = self.job
        if job is not None:
            with job.dispatch_guard:
                if not job.dispatched:
                    job.cancelled = True
        self.generation += 1
        self.lifecycle.pending = None
        self.lifecycle.active = None
        self.lifecycle.version += 1
        self.lifecycle.outcome = "context unavailable"

    def wait_for_worker(self, timeout: float) -> None:
        """Bounded owner-side join; polling never calls this blocking seam."""
        if not 0 <= timeout <= 1:
            message = "invalid planning join budget"
            raise ValueError(message)
        job = self.job
        if job is not None and job.thread is not None:
            job.thread.join(timeout)

    def close(self) -> None:
        self.invalidate()
        self.wait_for_worker(1)
        job = self.job
        if job is not None and job.thread is not None and job.thread.is_alive():
            message = "planning worker release unconfirmed"
            raise RuntimeError(message)
        self.poll(Capabilities(frozenset(), frozenset(), frozenset()))
