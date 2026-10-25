"""The brain builds the grind script with the travel plan on a routed map."""

from __future__ import annotations

from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.model import Goal
from tests.conftest import make_state
from tests.test_host_memory import memory_host  # the fixture hosts the brain


def _brain(tmp_path) -> EventDrivenBrain:

    host = memory_host(tmp_path)
    try:
        agent = next(iter(host.agents.values()))
        brain = agent.brain
        assert brain is not None
        assert isinstance(brain, EventDrivenBrain)
        return brain
    finally:
        host.stop()


def test_grind_on_a_routed_map_gets_the_travel_plan(tmp_path) -> None:
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.GRIND, make_state(map_name="prontera"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == (
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )


def test_grind_on_an_unrouted_map_keeps_the_plain_script(tmp_path) -> None:
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.GRIND, make_state(map_name="prt_fild08"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == ()
