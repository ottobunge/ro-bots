"""Decisions: translate a BotState into a Clef (SystemOne) request schema.

The domain owns the *question schema* — the technology-agnostic description of
what the brain wants to know each tick. Adapters render/serialize it for a
specific decision-model backend (llama.cpp Clef, Workers AI Clef, or a stub).
"""

from typing import TYPE_CHECKING, Any

from robots.domain.model import Goal

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


def _goal_criterion(goal: Goal) -> str:
    return {
        Goal.GRIND: "Level up by fighting monsters suited to my level.",
        Goal.FARM_ITEM: "Farm for the specific item I am assigned.",
        Goal.IDLE_TOWN: "Relax in town, maybe chat with passers-by.",
        Goal.QUEST: "Work on a level-appropriate quest.",
        Goal.SOCIAL: "Find and join other players, party or guild.",
    }[goal]


def build_decision_request(state: BotState) -> dict[str, Any]:
    """Build the SystemOne question schema for one tick of a bot's brain."""
    nearby_desc = ", ".join(f"{a.name}({a.kind}, d={a.distance:.0f})" for a in state.nearby[:10])
    chat_desc = " | ".join(f"[{c.channel}] {c.sender}: {c.text}" for c in state.recent_chat[-3:])
    invites = ", ".join(i.from_name for i in state.pending_invites) or "none"
    inv_items = ", ".join(f"{k}x{v}" for k, v in sorted(state.inventory.items())) or "empty"

    json_state: dict[str, Any] = {
        "bot": {
            "name": state.name,
            "job": state.job,
            "level": state.base_level,
            "hp_ratio": round(state.hp_ratio, 2),
            "sp_ratio": round(state.sp / state.max_sp, 2) if state.max_sp else 0.0,
            "map": state.map_name,
            "pos": [state.x, state.y],
            "goal": str(state.goal),
            "in_party": state.in_party,
        },
        "nearby_actors": nearby_desc,
        "inventory": inv_items,
        "pending_party_invites": invites,
        "recent_chat": chat_desc,
    }

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

    return {
        "model": "clef",
        "state": json_state,
        "questions": questions,
        "goal_criterion_grind": _goal_criterion(Goal.GRIND),
    }


def goal_summary(goal: Goal) -> str:
    """Human-readable goal summary (used in escalation prompts and logs)."""
    return _goal_criterion(goal)
