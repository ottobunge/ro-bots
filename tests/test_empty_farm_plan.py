"""Empty knowledge must not create an unexecutable farming plan."""

from dataclasses import replace

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.actions import Attack
from robots.domain.model import ActorRef


def test_no_catalog_falls_back_to_executable_grind(state):

    state = replace(state, nearby=(ActorRef(42, "unknown monster", "monster", 2.0),))
    brain = EventDrivenBrain(ScriptedDecisionModel(answers={}), StaticChatGenerator())
    brain.start(state)
    assert brain.current_plan is None
    assert isinstance(brain.current_script(), GrindScript)
    assert brain.step_script(state).actions == (Attack(42),)
