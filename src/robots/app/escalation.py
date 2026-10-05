"""Escalation policy: when does a decision leave Clef and reach the LLM?"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EscalationPolicy:
    """Thresholds governing Clef -> LLM hand-offs.

    The experiment's whole point is measuring this rate, so every escalation
    is a countable event with a reason.
    """

    confidence_floor: float = 0.55
    reply_chat_always: bool = True

    def needs_escalation(
        self, answers: dict[str, Any], *, chat_directed_at_bot: bool
    ) -> tuple[bool, str]:
        """Return (escalate?, reason) for one tick's answers."""
        next_action = answers.get("next_action", {})
        if float(next_action.get("confidence", 1.0)) < self.confidence_floor:
            return True, "low_confidence"
        if self.reply_chat_always and chat_directed_at_bot:
            return True, "chat_reply"
        return False, ""
