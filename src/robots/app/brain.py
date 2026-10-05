"""The brain: scripts do the walking; events and goal reviews wake Clef.

Decision-model calls happen ONLY here — on world events or periodic heartbeats
— never per tick. Between events, the active behavior script runs mechanically.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, final

from robots.app.escalation import EscalationPolicy
from robots.app.scripts import (
    BehaviorScript,
    FarmScript,
    GrindScript,
    ScriptOutcome,
    ScriptStatus,
    script_for,
)
from robots.domain.actions import (
    AcceptInvite,
    GameAction,
    MoveTo,
    PartyChat,
    Rest,
    Say,
)
from robots.domain.decisions import PREMADE_CHAT, build_decision_request
from robots.domain.events import (
    ChatHeard,
    DamageTaken,
    Heartbeat,
    InviteReceived,
    MonsterSpotted,
    PlanExpired,
    WorldEvent,
    event_summary,
)
from robots.domain.farm import FARM_DURATION_S, INTERRUPT_LEVEL_MARGIN, FarmPlan
from robots.domain.model import Goal

if TYPE_CHECKING:
    from robots.domain.model import BotState
    from robots.ports import ChatGenerator, DecisionModel, MobDatabase

REVIEW_BAD = 0.5
URGENCY_TALK = 1.5


@dataclass(frozen=True, slots=True)
class TickResult:
    """Outcome of one event handling — actions plus introspection for observers."""

    actions: tuple[GameAction, ...]
    answers: dict[str, Any]
    escalated: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


@final
class EventDrivenBrain:
    """Clef decides *what to do next*; a script executes it until an event.

    Every decision-model call is counted, as is every LLM escalation — the
    ratio is the experiment's headline metric.
    """

    def __init__(
        self,
        decision_model: DecisionModel,
        chat: ChatGenerator,
        policy: EscalationPolicy | None = None,
        mob_db: MobDatabase | None = None,
    ) -> None:
        self._model = decision_model
        self._chat = chat
        self.policy = policy or EscalationPolicy()
        self._script: BehaviorScript | None = None
        self._plan: FarmPlan | None = None
        self._plan_seq = 0
        self._mob_db: MobDatabase | None = mob_db
        self.decision_count = 0
        self.escalation_count = 0

    @property
    def escalation_rate(self) -> float:
        """Fraction of Clef decisions that needed the LLM (the metric we track)."""
        return self.escalation_count / self.decision_count if self.decision_count else 0.0

    def current_script(self) -> object | None:
        return self._script

    @property
    def current_plan(self) -> FarmPlan | None:
        return self._plan

    def should_interrupt(self, event: MonsterSpotted) -> bool:
        """FarmPlan customizes the interrupt system: while farming, only
        very-high-level or MVP/unique mobs wake the brain; everything else
        is below the plan's notice. Without a plan, everything interrupts."""
        plan = self._plan
        if plan is None:
            return True
        info = self._mob_db.by_name(event.actor.name) if self._mob_db else None
        if info is None:
            return True  # unknown mob: treat as unique, interrupt
        if plan.interrupt_on_mvp and info.is_mvp:
            return True
        return info.level >= plan.interrupt_level_above + INTERRUPT_LEVEL_MARGIN

    def start(self, state: BotState) -> TickResult:
        """Initial plan: one heartbeat review to pick a goal and a script."""
        return self.handle_event(state, Heartbeat(seq=0))

    def handle_event(self, state: BotState, event: WorldEvent) -> TickResult:
        """React to one world event — the only path that reaches Clef."""
        request = build_decision_request(state)
        request["state"] = {**request["state"], "event": event_summary(event)}
        self._augment_request_for_event(event, request)
        if isinstance(event, Heartbeat):
            self._augment_request_for_review(state, request)

        response = self._model.decide(request)
        self.decision_count += 1
        answers: dict[str, Any] = response["answers"]
        actions: list[GameAction] = []
        notes: list[str] = [f"event:{event_summary(event)}"]
        escalated = False

        match event:
            case MonsterSpotted():
                actions.extend(self._react_monster(state, answers, notes))
            case DamageTaken():
                actions.extend(self._react_damage(state, answers))
            case ChatHeard():
                chat_actions, escalated = self._react_to_chat(state, answers, event)
                actions.extend(chat_actions)
            case InviteReceived():
                if self._noul(answers, "accept_invite"):
                    actions.append(AcceptInvite())
                    notes.append(f"accepted invite from {event.invite.from_name}")
            case PlanExpired():
                notes.append("farm plan ended; goal review on next heartbeat")
                self._plan = None
            case Heartbeat():
                actions.extend(self._run_review(state, answers, notes))
            case _:
                pass

        return TickResult(
            actions=tuple(actions), answers=answers, escalated=escalated, notes=tuple(notes)
        )

    def _run_review(
        self, state: BotState, answers: dict[str, Any], notes: list[str]
    ) -> list[GameAction]:
        """Heartbeat: goal review, farm-plan authoring, optional announcement."""
        goal = self._review_goal(state, answers, notes)
        plan = self._setup_farm_plan(state, answers, notes) if self._wants_farming(goal) else None
        self._plan = plan
        self._script = FarmScript(plan) if plan is not None else script_for(goal, state)
        notes.append(f"script->{type(self._script).__name__}")
        announce = self._premade_text(state, answers, min_urgency=URGENCY_TALK)
        if announce is None:
            return []
        text, is_party = announce
        notes.append("announce")
        return [PartyChat(text) if is_party else Say(text)]

    def _augment_request_for_event(self, event: WorldEvent, request: dict[str, Any]) -> None:
        """Add event-specific questions to the request (react_monster etc.)."""
        if isinstance(event, MonsterSpotted):
            request["questions"]["react_monster"] = {
                "type": "choice",
                "instructions": "A monster appeared. How do I react?",
                "criteria": {
                    "ignore": "Not worth my time; keep doing what I am doing.",
                    "attack": "Switch to fighting it.",
                    "flee": "Too dangerous for my level; move away.",
                },
            }
        elif isinstance(event, DamageTaken):
            request["questions"]["react_damage"] = {
                "type": "choice",
                "instructions": "I just took damage. What now?",
                "criteria": {
                    "keep": "Keep going.",
                    "rest": "Sit and regenerate.",
                    "flee": "Run away from the attacker.",
                },
            }

    def step_script(self, state: BotState) -> ScriptOutcome:
        """One mechanical script step (no model calls); clears script when done."""
        if self._script is None:
            self._script = script_for(state.goal, state)
        outcome: ScriptOutcome = self._script.step(state)
        if outcome.status in (ScriptStatus.DONE, ScriptStatus.FAILED):
            self._script = None
        return outcome

    # -- event reactions ----------------------------------------------------

    def _react_monster(
        self, state: BotState, answers: dict[str, Any], notes: list[str]
    ) -> list[GameAction]:
        match self._choice(answers, "react_monster", "ignore"):
            case "attack":
                self._script = GrindScript()
                notes.append("script->grind")
                return []
            case "flee":
                notes.append("fleeing")
                return [MoveTo(x=state.x, y=state.y + 4)]
            case _:
                notes.append("monster ignored")
                return []

    def _react_damage(self, state: BotState, answers: dict[str, Any]) -> list[GameAction]:
        match self._choice(answers, "react_damage", "keep"):
            case "rest":
                return [Rest()]
            case "flee":
                return [MoveTo(x=state.x, y=state.y + 4)]
            case _:
                return []

    def _react_to_chat(
        self, state: BotState, answers: dict[str, Any], event: ChatHeard
    ) -> tuple[list[GameAction], bool]:
        directed = event.line.channel == "whisper" or state.name in event.line.text
        escalate, _reason = self.policy.needs_escalation(
            {"next_action": answers.get("next_action", {"confidence": 1.0})},
            chat_directed_at_bot=directed,
        )
        if escalate:
            self.escalation_count += 1
            prompt = f"A player named {event.line.sender} said: {event.line.text}"
            return [Say(self._chat.generate_chat(prompt))], True
        premade = self._premade_text(state, answers, min_urgency=None)
        if premade is not None:
            text, is_party = premade
            return [PartyChat(text) if is_party else Say(text)], False
        return [], False

    # -- helpers -------------------------------------------------------------

    def _augment_request_for_review(self, state: BotState, request: dict[str, Any]) -> None:
        """Heartbeat review gets extra questions: goal change + farm setup."""
        questions = request["questions"]
        questions["change_goal"] = {
            "type": "choice",
            "instructions": "Time to review my day. Keep my goal or switch?",
            "criteria": {
                "keep": "Keep pursuing my current goal.",
                "social": "Switch: find players, party, chat.",
                "grind": "Switch: go level up somewhere.",
                "farm": "Switch: set up a farming session.",
                "town": "Switch: go idle in town for a while.",
            },
        }
        if self._mob_db is not None:
            mobs = self._mob_db.mobs_on_map(state.map_name)
            if mobs:
                mob_lines = "; ".join(
                    f"{m.name} lvl{m.level}{' MVP' if m.is_mvp else ''}" for m in mobs[-6:]
                )
                request["state"] = {**request["state"], "map_mobs": mob_lines}
                questions["farm_duration"] = {
                    "type": "score",
                    "instructions": (
                        "If I farm here, how long should the session run? "
                        f"Mobs here: {mob_lines}."
                    ),
                    "criteria": ["Short", "Medium", "Long"],
                }
                questions["farm_target"] = {
                    "type": "choice",
                    "instructions": "Which mob is the best farming target for my level?",
                    "criteria": {
                        m.name: f"Level {m.level}{' (MVP)' if m.is_mvp else ''}" for m in mobs
                    },
                }

    def _wants_farming(self, goal: Goal) -> bool:
        return goal in (Goal.GRIND, Goal.FARM_ITEM)

    def _setup_farm_plan(
        self, state: BotState, answers: dict[str, Any], notes: list[str]
    ) -> FarmPlan | None:
        """Clef authors the plan: duration, target mobs, interrupt thresholds."""
        self._plan_seq += 1
        duration = FARM_DURATION_S.get(
            int(float(answers.get("farm_duration", {}).get("score", 1.0)) + 0.5),
            FARM_DURATION_S[1],
        )
        target = self._choice(answers, "farm_target", "")
        mobs = list(self._mob_db.mobs_on_map(state.map_name)) if self._mob_db else []
        targets = [target] if target in {m.name for m in mobs} else [m.name for m in mobs[:2]]
        plan = FarmPlan(
            plan_id=self._plan_seq,
            map_name=state.map_name,
            target_mobs=tuple(targets),
            duration_s=duration,
            interrupt_level_above=state.base_level,
        )
        notes.append(
            f"plan#{plan.plan_id}: farm {plan.target_mobs} for {plan.duration_s / 60:.0f}min"
        )
        return plan

    def _review_goal(self, state: BotState, answers: dict[str, Any], notes: list[str]) -> Goal:
        change = self._choice(answers, "change_goal", "keep")
        if change != "keep":
            new_goal: Goal | None = {
                "social": Goal.SOCIAL,
                "grind": Goal.GRIND,
                "farm": Goal.FARM_ITEM,
                "town": Goal.IDLE_TOWN,
            }.get(change)
            if new_goal is not None and new_goal != state.goal:
                notes.append(f"goal {state.goal}->{new_goal}")
                return new_goal
        score = float(answers.get("goal_review", {}).get("score", 1.0))
        if score < REVIEW_BAD:
            new_goal = Goal.SOCIAL if state.goal != Goal.SOCIAL else Goal.GRIND
            notes.append(f"goal {state.goal}->{new_goal} (bad review)")
            return new_goal
        return state.goal

    def _premade_text(
        self, state: BotState, answers: dict[str, Any], *, min_urgency: float | None
    ) -> tuple[str, bool] | None:
        if not self._noul(answers, "use_premade"):
            return None
        if min_urgency is not None:
            urgency = float(answers.get("chat_urgency", {}).get("score", 0.0))
            if urgency < min_urgency:
                return None
        premade = self._choice(answers, "premade_pick", "none")
        if premade == "none" or premade not in PREMADE_CHAT:
            return None
        text = (
            PREMADE_CHAT[premade]
            .replace("%job", state.job)
            .replace("%level", str(state.base_level))
            .replace("%item", next(iter(state.inventory), "stuff"))
        )
        return text, state.in_party

    def _choice(self, answers: dict[str, Any], qid: str, default: str) -> str:
        return str(answers.get(qid, {}).get("choice", default))

    def _noul(self, answers: dict[str, Any], qid: str) -> bool:
        return float(answers.get(qid, {}).get("noul", 0.0)) >= 0.5
