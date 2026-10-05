"""Application layer: event-driven bot brains, scripts, escalation, runner.

Depends ONLY on ports + domain. Swapping Clef-local for Clef-remote, or the
local Qwen for a hosted API, never touches this code.
"""

from robots.app.brain import EventDrivenBrain, TickResult
from robots.app.builds import BuildAuthor, decide_item_action, note_build_progress
from robots.app.escalation import EscalationPolicy
from robots.app.runner import BotRunner
from robots.app.scripts import GrindScript, IdleTownScript, ScriptStatus, TravelScript

__all__ = [
    "BotRunner",
    "BuildAuthor",
    "EscalationPolicy",
    "EventDrivenBrain",
    "GrindScript",
    "IdleTownScript",
    "ScriptStatus",
    "TickResult",
    "TravelScript",
    "decide_item_action",
    "note_build_progress",
]
