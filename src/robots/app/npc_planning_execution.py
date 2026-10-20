"""One admitted received-prompt response; no menu authorship or NPC opening.

Issued/denied/failed are local dispatch dispositions, never native ACKs. A newer
same-open UI proves received UI progress only, not causality, rewards or quests.
"""

from dataclasses import dataclass

from robots.domain.actions import NpcRespond
from robots.domain.events import (
    DamageTaken,
    Heartbeat,
    NpcDialogueReceived,
    ScriptFailed,
    WorldEvent,
)
from robots.domain.npc import NpcDialogue
from robots.domain.planning import (
    NpcIntent,
    NpcObservation,
    PhaseKind,
    PlanningIdentity,
    ProposedPlan,
)


def execution_event_allowed(plan: ProposedPlan, event: WorldEvent) -> bool:
    if isinstance(event, NpcDialogueReceived):
        return plan.phases[0].kind == PhaseKind.NPC
    return isinstance(event, (Heartbeat, DamageTaken, ScriptFailed))


def execution_event_data(event: WorldEvent) -> str:
    if not isinstance(event, NpcDialogueReceived):
        return str(event)
    dialog = event.dialogue
    binding = (dialog.npc_id, dialog.epoch, dialog.map_name)
    return str(
        (
            *binding,
            dialog.opened_sequence,
            dialog.sequence,
            dialog.stage,
        )
    )


@dataclass(frozen=True)
class LocalNpcDispatch:
    action: NpcRespond
    disposition: str


@dataclass(frozen=True)
class NpcHostBinding:
    """Owner-local object references, not a serialized or cryptographic nonce."""

    client: object
    wire: object
    session: object

    def matches(self, client: object, wire: object, session: object) -> bool:
        return self.client is client and self.wire is wire and self.session is session


@dataclass(frozen=True)
class NpcUiObservation:
    dialogue: NpcDialogue
    observed_at: float
    expires_at: float
    failed: bool


@dataclass
class NpcPhase:
    identity: PlanningIdentity
    version: int
    intent: NpcIntent
    admitted_observation: NpcObservation
    action: NpcRespond | None = None
    status: str = "review"
    progress_sequence: int | None = None
    failure: str | None = None
    replan_requested: bool = False

    def queued_for(self, action: NpcRespond, identity: PlanningIdentity, version: int) -> bool:
        return all(
            (
                self.action is action,
                self.status == "queued",
                self.identity == identity,
                self.version == version,
            )
        )

    def request(self, choice: str, choice_version: int, *, pending: bool) -> tuple[NpcRespond, ...]:
        if (
            self.action is not None
            or pending
            or choice != "continue"
            or choice_version != self.version
        ):
            return ()
        self.action = NpcRespond(self.identity, self.intent)
        self.status = "queued"
        return (self.action,)

    def dispatched(self, action: NpcRespond, receipt: LocalNpcDispatch | None) -> None:
        if action is not self.action or self.status != "queued":
            return
        issued = (
            receipt is not None and receipt.action is action and receipt.disposition == "issued"
        )
        self.status = "waiting" if issued else "failed"
        if not issued:
            self.failure = "local NPC dispatch not issued"

    def observe(self, observation: NpcUiObservation | None) -> None:
        if self.status != "waiting":
            return
        if observation is None or not self.same_open(observation.dialogue) or observation.failed:
            self.status = "failed"
            self.failure = "received NPC binding or lease lost"
            return
        dialog = observation.dialogue
        if dialog.sequence <= self.intent.prompt_sequence:
            return
        if dialog.stage in ("text", "next", "menu"):
            self.progress_sequence = dialog.sequence
            self.status = "completed"
        elif dialog.stage != "waiting":
            self.status = "failed"
            self.failure = "unsupported received NPC UI"

    def same_open(self, dialog: NpcDialogue) -> bool:
        return (
            dialog.npc_id == self.intent.npc_id
            and dialog.epoch == self.intent.epoch
            and dialog.map_name == self.intent.map_name
            and dialog.opened_sequence == self.intent.opened_sequence
        )
