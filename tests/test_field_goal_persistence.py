"""Leg 124: chat cannot reclaim a recently routed field goal."""

import json
from dataclasses import replace

import pytest

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.scripts import FarmScript
from robots.app.trace_log import TraceLog
from robots.domain.events import Heartbeat, PlanExpired
from robots.domain.model import Goal
from tests.conftest import make_state
from tests.test_brain import base_answers
from tests.test_city_field_travel import _brain


@pytest.mark.parametrize("choice", ["social", "town", "bad_review"])
def test_routed_goal_holds_for_ten_minutes_then_releases(choice, monkeypatch, tmp_path, caplog):
    now = [100.0]
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: now[0])
    brain = _brain()
    answers = base_answers()
    brain._model = ScriptedDecisionModel(answers)
    trace = TraceLog(tmp_path, "persistence")
    brain._trace = trace
    city = make_state(map_name="prontera", nearby=(), in_party=True)
    brain.start(city)
    answers["change_goal"]["choice"] = choice if choice != "bad_review" else "unknown"
    answers["goal_review"]["score"] = 0.1
    answers["next_action"]["choice"] = "chat"
    # Hundreds of reviews, chat choices and plan renewals never extend the lease.
    for seq in range(1, 201):
        now[0] = 100 + seq * 2.99
        result = brain.handle_event(city, Heartbeat(seq=seq))
        assert isinstance(brain.current_script(), FarmScript)
        assert not any("->social" in note or "->idle_town" in note for note in result.notes)
    now[0] = 700
    result = brain.handle_event(city, Heartbeat(seq=201))
    assert brain.current_plan is None
    assert not isinstance(brain.current_script(), FarmScript)
    assert any("goal " in note for note in result.notes)
    trace.close()
    kinds = [json.loads(line)["kind"] for line in trace.path.read_text().splitlines()]
    assert "goal_persistence_held" in kinds
    assert kinds.count("goal_persistence_expired") == 1
    assert "goal_persistence_held" in caplog.text
    assert "goal_persistence_expired" in caplog.text


def test_persistence_survives_arrival_and_short_plan_expiry(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: now[0])
    brain = _brain()
    answers = base_answers()
    brain._model = ScriptedDecisionModel(answers)
    answers["farm_duration"]["score"] = 0
    city = make_state(map_name="prontera", nearby=(), in_party=True)
    brain.start(city)
    field = replace(city, map_name="prt_fild08")
    now[0] = 401
    assert brain.current_plan is not None
    brain.handle_event(field, PlanExpired(plan_id=brain.current_plan.plan_id))
    answers["change_goal"]["choice"] = "social"
    brain.handle_event(field, Heartbeat(seq=1))
    assert isinstance(brain.current_script(), FarmScript)
    assert brain.current_plan is not None
    assert brain.current_plan.map_name == "prt_fild08"
    now[0] = 700
    brain.handle_event(field, Heartbeat(seq=2))
    assert brain.current_plan is None


@pytest.mark.parametrize("boundary", ["epoch", "reverse"])
def test_invalid_session_or_clock_cannot_hold_goal(boundary, monkeypatch):
    now = [100.0]
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: now[0])
    brain = _brain()
    answers = base_answers()
    brain._model = ScriptedDecisionModel(answers)
    city = make_state(map_name="prontera", nearby=(), in_party=True, native_epoch=1)
    brain.start(city)
    answers["change_goal"]["choice"] = "social"
    if boundary == "epoch":
        city = replace(city, native_epoch=2)
    else:
        now[0] = 99
    brain.handle_event(city, Heartbeat(seq=1))
    assert brain.current_plan is None


def test_local_farm_has_no_field_persistence(monkeypatch):
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: 100)
    brain = _brain()
    answers = base_answers()
    brain._model = ScriptedDecisionModel(answers)
    field = make_state(nearby=(), goal=Goal.GRIND, in_party=True)
    brain.start(field)
    answers["change_goal"]["choice"] = "social"
    brain.handle_event(field, Heartbeat(seq=1))
    assert brain.current_plan is None
