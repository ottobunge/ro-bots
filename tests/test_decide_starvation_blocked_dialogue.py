"""The dealer-adjacent decide starvation (population legs 24/25).

Live shape (leg 25, prt_in shop interior, pop_0003_g00m00/g00m01): the parked
agents decided once at window-open, executed TalkToNpc -> NpcShopSellOpen ->
NpcShopBuySelection, and never decided again (decide_request frozen at 1 for
19+ minutes) while state ticks continued and the field agents decided at full
cadence. The buy selection's answer (the shop list) is not an NPC-dialogue
frame, so the retained dialogue expires into the denied "blocked" stage —
deliberately non-terminal, pending the runtime's budget-capped fresh begin
(leg 24 receipt: npc_stage 'blocked' for the whole remaining window).

The starvation lives in the brain's event routing: handle_event sent every
later event — every heartbeat, every chat line — into _handle_npc_event,
which only ever answers a received menu and silently swallows the rest. A
denied dialogue can never reach the menu lane (receipts are ignored while
failed until a fresh begin), so the swallow was permanent. These tests pin
the routing contract: a denied dialogue keeps the decide lane alive; live
stages keep the strict NPC lane unchanged.
"""

from typing import TYPE_CHECKING, cast

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.domain.events import ChatHeard, Heartbeat
from robots.domain.model import ActorRef, BotState, ChatLine, Goal
from robots.domain.npc import NpcDialogue

if TYPE_CHECKING:
    from robots.ports import ChatGenerator, DecisionModel

DEALER_ID = 110001762
EPOCH = 1
OPENED_SEQUENCE = 72
PROMPT_SEQUENCE = 73


def dealer_state(stage: str = "blocked") -> BotState:
    """The leg-25 offline twin: parked at prt_in 172,129, the dealer-adjacent
    cell, with the retained dialogue in the post-shop-chain stage."""
    return BotState(
        name="NyxSong",
        job="Novice",
        base_level=10,
        hp=86,
        max_hp=86,
        sp=20,
        max_sp=20,
        map_name="prt_in",
        x=172,
        y=129,
        goal=Goal.GRIND,
        in_party=True,
        nearby=(ActorRef(id=DEALER_ID, name="Weapon Dealer#prt", kind="npc", distance=1.0),),
        inventory={"Emperium": 1, "Jellopy": 1},
        pending_invites=(),
        recent_chat=(),
        native_epoch=EPOCH,
        npc_dialogue=NpcDialogue(
            npc_id=DEALER_ID,
            epoch=EPOCH,
            map_name="prt_in",
            opened_sequence=OPENED_SEQUENCE,
            sequence=PROMPT_SEQUENCE,
            stage=stage,
        ),
    )


def make_brain() -> tuple[EventDrivenBrain, ScriptedDecisionModel]:
    model = ScriptedDecisionModel(answers={})
    brain = EventDrivenBrain(
        decision_model=cast("DecisionModel", model),
        chat=cast("ChatGenerator", StaticChatGenerator(["gg"])),
        memory=None,
    )
    return brain, model


def test_blocked_dialogue_heartbeats_keep_reaching_the_model() -> None:
    """Repeated idle_review/heartbeat fires must keep deciding across a denied
    dialogue: the barrier holds actuation, not the decision lane."""
    brain, model = make_brain()
    state = dealer_state(stage="blocked")
    brain.handle_event(state, Heartbeat(seq=1))
    brain.handle_event(state, Heartbeat(seq=2))
    brain.handle_event(state, Heartbeat(seq=3))
    assert model.calls == 3, (
        "every heartbeat must reach the decide path while the dialogue is "
        "denied; a frozen decide lane is the leg-24/25 starvation"
    )


def test_blocked_dialogue_chat_reaches_the_model() -> None:
    """A heard chat line during a denied dialogue must still be decided (the
    swallowed 09:01:05 party line in leg 25)."""
    brain, model = make_brain()
    state = dealer_state(stage="blocked")
    brain.handle_event(
        state,
        ChatHeard(
            line=ChatLine(channel="party", sender="zeny_wing", text="Looking for party!", at=1.0)
        ),
    )
    assert model.calls == 1, "chat during a denied dialogue must reach the decide path"


def test_live_dialogue_stage_keeps_strict_npc_lane() -> None:
    """A live (non-denied) dialogue keeps the strict NPC lane: a plain
    heartbeat must not decide over an open 'waiting' shop exchange."""
    brain, model = make_brain()
    state = dealer_state(stage="waiting")
    brain.handle_event(state, Heartbeat(seq=1))
    assert model.calls == 0, "live stages keep the strict NPC lane (no heartbeat decide)"
