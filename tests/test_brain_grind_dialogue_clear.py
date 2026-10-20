"""Bounded NPC-dialogue clear for grind goals (window-8 root cause).

Live shape (window 8, fixture 1): the character spawns adjacent to NPC
Nelliorde (prt_fild08,175,374 vs spawn 176,374), a non-terminal dialogue is
retained, and EventDrivenBrain.step_script diverts every mechanical step to
_npc_step — dialogue actions only, zero Attack, for the whole window. These
tests pin the bounded clear contract: strict handling first, one reviewed
terminal/cancel drive per received stage beyond a bounded step budget, then
the goal script resumes. Non-grind goals and dialogue memory stay unchanged.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import GRIND_DIALOGUE_BLOCK_BUDGET, EventDrivenBrain
from robots.domain.actions import Attack, NpcClose, NpcNext, NpcSelect
from robots.domain.model import ActorRef, BotState, Goal
from robots.domain.npc import NpcDialogue

if TYPE_CHECKING:
    from robots.ports import ChatGenerator, DecisionModel
    from robots.society.memory import Memory

NPC_ID = 110015662
PORING_ID = 110015659
EPOCH = 3
OPENED_SEQUENCE = 41


class FakeMemory:
    """Minimal Memory seam: records remembered lines, replays them in view()."""

    def __init__(self) -> None:
        self.entries: list[str] = []

    def remember(self, channel: str, text: str, ts: float | None = None) -> None:
        self.entries.append(f"{channel}: {text}")

    def view(self) -> list[str]:
        return list(self.entries)


def blocked_state(
    stage: str = "next",
    goal: Goal = Goal.GRIND,
    pages: tuple[str, ...] = (),
    options: tuple[tuple[int, str], ...] = (),
    opened_sequence: int = OPENED_SEQUENCE,
) -> BotState:
    """Fixture 1 offline twin: adjacent NPC, retained non-terminal dialogue,
    an observed Poring in attack range, grind goal."""
    return BotState(
        name="host_fixture_1",
        job="Swordsman",
        base_level=42,
        hp=800,
        max_hp=1000,
        sp=60,
        max_sp=80,
        map_name="prt_fild08",
        x=176,
        y=374,
        goal=goal,
        in_party=False,
        nearby=(ActorRef(id=PORING_ID, name="Poring", kind="monster", distance=8.25),),
        inventory={"Jellopy": 23, "Red Potion": 5},
        pending_invites=(),
        recent_chat=(),
        native_epoch=EPOCH,
        npc_dialogue=NpcDialogue(
            npc_id=NPC_ID,
            epoch=EPOCH,
            map_name="prt_fild08",
            opened_sequence=opened_sequence,
            sequence=opened_sequence,
            stage=stage,
            pages=pages,
            options=options,
        ),
    )


def make_brain(memory: FakeMemory | None = None) -> EventDrivenBrain:
    return EventDrivenBrain(
        decision_model=cast("DecisionModel", ScriptedDecisionModel(answers={}, queue=[])),
        chat=cast("ChatGenerator", StaticChatGenerator(["gg"])),
        memory=cast("Memory", memory) if memory is not None else None,
    )


def step_many(brain: EventDrivenBrain, state: BotState, steps: int) -> list[list]:
    return [list(brain.step_script(state).actions) for _ in range(steps)]


# -- the bounded clear contract (RED on window-8 bytes) -----------------------


def test_next_stage_one_drive_then_goal_script_attacks() -> None:
    brain = make_brain()
    state = blocked_state(stage="next")
    outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
    strict = outcomes[:GRIND_DIALOGUE_BLOCK_BUDGET]
    assert all(a == NpcNext(NPC_ID) for step in strict for a in step)
    after = [a for step in outcomes[GRIND_DIALOGUE_BLOCK_BUDGET:] for a in step]
    drives = [a for a in after if isinstance(a, NpcNext)]
    assert drives == [NpcNext(NPC_ID)]  # exactly one bounded drive
    attacks = [a for a in after if isinstance(a, Attack)]
    assert attacks
    assert attacks[0] == Attack(target_id=PORING_ID)
    assert brain.current_script() is not None


def test_close_stage_one_drive_then_goal_script_attacks() -> None:
    brain = make_brain()
    state = blocked_state(stage="close")
    outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
    after = [a for step in outcomes[GRIND_DIALOGUE_BLOCK_BUDGET:] for a in step]
    assert len([a for a in after if isinstance(a, NpcClose)]) == 1
    attacks = [a for a in after if isinstance(a, Attack)]
    assert attacks
    assert attacks[0] == Attack(target_id=PORING_ID)


def test_menu_stage_cancels_255_once_never_repeats() -> None:
    brain = make_brain()
    state = blocked_state(stage="menu", options=((1, "Talk"), (2, "Leave")))
    outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
    strict = outcomes[:GRIND_DIALOGUE_BLOCK_BUDGET]
    assert all(not step for step in strict)  # menus stay event-driven while strict
    cancels = [
        a
        for step in outcomes[GRIND_DIALOGUE_BLOCK_BUDGET:]
        for a in step
        if isinstance(a, NpcSelect)
    ]
    assert cancels == [NpcSelect(NPC_ID, 255)]  # prompt/menu cancel-255, once
    attacks = [a for a in outcomes[-1] if isinstance(a, Attack)]
    assert attacks == [Attack(target_id=PORING_ID)]


def test_stage_without_reviewed_drive_fails_closed() -> None:
    brain = make_brain()
    state = blocked_state(stage="text", pages=("Hello.",))
    outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
    late = [a for step in outcomes[GRIND_DIALOGUE_BLOCK_BUDGET:] for a in step]
    assert late == []  # no invented sends, no attacks through an active UI


# -- regression guards -------------------------------------------------------


def test_non_grind_goal_keeps_strict_dialogue_handling() -> None:
    for goal in (Goal.IDLE_TOWN, Goal.QUEST, Goal.SOCIAL):
        brain = make_brain()
        state = blocked_state(stage="next", goal=goal)
        outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
        flat = [a for step in outcomes for a in step]
        assert flat == [NpcNext(NPC_ID)] * (GRIND_DIALOGUE_BLOCK_BUDGET + 12)
        assert not any(isinstance(a, Attack) for a in flat)


def test_dialogue_memory_retention_unchanged_across_clear() -> None:
    memory = FakeMemory()
    brain = make_brain(memory=memory)
    state = blocked_state(stage="next", pages=("Welcome,", "Choose."))
    step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET + 12)
    remembered = [e for e in memory.entries if e.startswith("npc_dialogue:")]
    assert len(remembered) == 2  # each received page once, never re-remembered
    assert any("page=1" in e for e in remembered)
    assert any("page=2" in e for e in remembered)


def test_new_dialogue_session_gets_its_own_budget() -> None:
    brain = make_brain()
    step_many(brain, blocked_state(stage="next"), GRIND_DIALOGUE_BLOCK_BUDGET + 4)
    dialogue = blocked_state().npc_dialogue
    assert dialogue is not None
    state = replace(
        blocked_state(), npc_dialogue=replace(dialogue, opened_sequence=OPENED_SEQUENCE + 7)
    )
    outcomes = step_many(brain, state, GRIND_DIALOGUE_BLOCK_BUDGET)
    flat = [a for step in outcomes for a in step]
    assert flat == [NpcNext(NPC_ID)] * GRIND_DIALOGUE_BLOCK_BUDGET  # strict again
