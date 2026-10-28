"""Decisions: translate a BotState into a Clef (SystemOne) request schema.

The domain owns the *question schema* — the technology-agnostic description of
what the brain wants to know each tick. Adapters render/serialize it for a
specific decision-model backend (llama.cpp Clef, Workers AI Clef, or a stub).
"""

from typing import TYPE_CHECKING, Any

from robots.domain.inventory_context import inventory_capacity_facts
from robots.domain.model import Goal
from robots.domain.skills import ReceivedSkillContextReadOnly

if TYPE_CHECKING:
    from robots.domain.model import BotState

# Premade chat lives here, as choice options: zero LLM cost to emit one.
PREMADE_CHAT: dict[str, str] = {
    "lfp": "Looking for party! %job lvl %level",
    "need_buffs": "Buffs please!",
    "thanks": "Thanks!",
    "greet": "Hi all",
    "sell_wts": "WTS %item, PM me",
}


def _add_skill_context(json_state: dict[str, Any], state: BotState) -> None:
    context = state.received_skills or ReceivedSkillContextReadOnly()
    json_state["observed_effective_skills"] = context.decision_facts()
    if state.public_skill_knowledge is not None:
        json_state["skill_rules_knowledge"] = state.public_skill_knowledge.decision_advice(context)


def _goal_criterion(goal: Goal) -> str:
    return {
        Goal.GRIND: "Level up by fighting monsters suited to my level.",
        Goal.FARM_ITEM: "Farm for the specific item I am assigned.",
        Goal.IDLE_TOWN: "Relax in town, maybe chat with passers-by.",
        Goal.QUEST: "Work on a level-appropriate quest.",
        Goal.SOCIAL: "Find and join other players, party or guild.",
    }[goal]


def _drop_moot_options(questions: dict[str, Any], state: BotState) -> None:
    """The facts gate the options: party_join is moot for a member of a
    persisted party (leg 16: 339 party_join picks starved grinding to zero
    attacks), so the schema drops what the state makes impossible. Leg 31's
    starvation is the same shape one hop over: a partied agent with no
    nearby outsider kept choosing party_invite (p=0.45 every heartbeat) and
    the social action path dispatched nothing for two hours — an inviter
    needs a candidate, so without one the option is moot too."""
    if state.in_party:
        del questions["next_action"]["criteria"]["party_join"]
        nearby_players = [
            a
            for a in state.nearby
            if getattr(a, "kind", "") == "player" and getattr(a, "name", "") != state.name
        ]
        if not nearby_players:
            del questions["next_action"]["criteria"]["party_invite"]


def build_decision_request(
    state: BotState,
    memory_lines: list[str] | None = None,
    *,
    knowledge_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Build the SystemOne question schema for one tick of a bot's brain.

    ``memory_lines`` (ADR-004): the OptChat-style memory view; when provided
    it is injected as ``state['memory_view']`` so the decision model sees the
    agent's whole past at bounded size. Absent key otherwise.

    ``knowledge_lines``: bounded game-knowledge lines (stat projections, item
    equip/sell projections, wiki context) composed by
    ``robots.knowledge.game_context``; injected as ``state['game_knowledge']``
    (capped, keeping the decide payload under its token budget). Absent key
    otherwise.
    """
    nearby_desc = ", ".join(f"{a.name}({a.kind}, d={a.distance:.0f})" for a in state.nearby[:10])
    chat_desc = " | ".join(f"[{c.channel}] {c.sender}: {c.text}" for c in state.recent_chat[-3:])
    invites = ", ".join(i.from_name for i in state.pending_invites) or "none"
    inv_items = (
        (", ".join(f"{k}x{v}" for k, v in sorted(state.inventory.items())) or "empty")
        if state.inventory_known
        else "unknown"
    )

    json_state: dict[str, Any] = {
        "bot": {
            "name": state.name,
            "job": state.job,
            "level": state.base_level,
            "hp": state.hp,
            "max_hp": state.max_hp,
            "sp": state.sp,
            "max_sp": state.max_sp,
            "hp_ratio": round(state.hp_ratio, 2),
            "sp_ratio": round(state.sp / state.max_sp, 2) if state.max_sp else 0.0,
            "map": state.map_name,
            "pos": [state.x, state.y],
            "goal": str(state.goal),
            "in_party": state.in_party,
        },
        "nearby_actors": nearby_desc,
        "inventory": inv_items,
        "inventory_capacity": inventory_capacity_facts(state),
        "pending_party_invites": invites,
        "recent_chat": chat_desc,
    }
    _add_encounters(json_state, state)
    _add_npc_context(json_state, state)
    _add_skill_context(json_state, state)
    _add_game_knowledge(json_state, knowledge_lines)

    if memory_lines is not None:
        json_state["memory_view"] = "\n".join(memory_lines[:40])

    questions: dict[str, dict[str, Any]] = {
        "next_action": {
            "type": "choice",
            "instructions": "What should I do right now?",
            "criteria": {
                "grind": "Attack a nearby monster appropriate for my level.",
                "loot": "Pick up loot on the ground.",
                "travel": "Move toward my goal area or map.",
                "idle": "Stand still a moment.",
                "rest": "Sit to recover HP/SP.",
                "go_town": "Return to town.",
                "quest": "Advance my level-appropriate quest.",
                "party_join": "Accept or seek a party.",
                "party_invite": "Invite a nearby player to a party.",
                "chat": "Say something (see chat questions).",
            },
        },
        "target_choice": {
            "type": "choice",
            "instructions": "If fighting, which target is best?",
            "criteria": {
                "closest": "The closest monster.",
                "weakest": "The weakest monster for my level.",
                "none": "No fighting right now.",
            },
        },
        "should_reply": {
            "type": "noul",
            "instructions": "Is a chat message directed at me and does it deserve a reply?",
        },
        "hp_critical": {
            "type": "noul",
            "instructions": "Is my HP low enough that I must retreat or rest?",
        },
        "threat_near": {
            "type": "noul",
            "instructions": "Is there an aggressive monster close enough to be a threat?",
        },
        "accept_invite": {
            "type": "noul",
            "instructions": "Should I accept a pending party invitation right now?",
        },
        "use_premade": {
            "type": "noul",
            "instructions": "Is a premade phrase the right thing to say (vs. staying silent)?",
        },
        "premade_pick": {
            "type": "choice",
            "instructions": "Which premade phrase fits the situation?",
            "criteria": dict(PREMADE_CHAT.items()) | {"none": "No premade needed."},
        },
        "chat_urgency": {
            "type": "score",
            "instructions": "How urgent is bot chat/social activity for my current goal?",
            "criteria": ["Silence is fine", "Light chatter okay", "Should talk now"],
        },
        "goal_review": {
            "type": "score",
            "instructions": "How well is my current goal going?",
            "criteria": ["Badly, reconsider", "Going okay", "Going great"],
        },
    }

    _drop_moot_options(questions, state)

    return {
        "model": "clef",
        "state": json_state,
        "questions": questions,
    }


def _add_game_knowledge(json_state: dict[str, Any], knowledge_lines: list[str] | None) -> None:
    """Bounded game-knowledge lines (criterion 4/10); absent keeps legacy shape.

    game_context.MAX_DECIDE_LINES is the composition-side cap; re-capped here
    so no caller path can exceed the decide payload budget.
    """
    if knowledge_lines:
        json_state["game_knowledge"] = list(knowledge_lines[:6])


def _add_npc_context(json_state: dict[str, Any], state: BotState) -> None:
    npcs = [a for a in state.nearby if a.kind == "npc"]
    if npcs:
        json_state["nearby_npcs"] = [
            {"id": a.id, "name": a.name, "distance": a.distance} for a in npcs[:10]
        ]
    dialog = state.npc_dialogue
    if dialog is not None:
        json_state["npc_dialogue"] = {
            "npc_id": dialog.npc_id,
            "epoch": dialog.epoch,
            "map": dialog.map_name,
            "sequence": dialog.sequence,
            "stage": dialog.stage,
            "pages": list(dialog.pages),
            "options": [{"index": i, "text": text} for i, text in dialog.options],
        }


def _add_encounters(json_state: dict[str, Any], state: BotState) -> None:
    """Optional detached received history; absent leaves the legacy schema intact."""
    if state.recent_encounters:
        json_state["recent_encounters"] = [dict(fact) for fact in state.recent_encounters]


def goal_summary(goal: Goal) -> str:
    """Human-readable goal summary (used in escalation prompts and logs)."""
    return _goal_criterion(goal)
