"""Exact already-perceived vitals in the real SystemOne request builder."""

from robots.domain.decisions import build_decision_request
from tests.conftest import make_state


def test_request_preserves_exact_vitals_including_zero_sp() -> None:
    state = make_state(hp=42, max_hp=86, sp=0, max_sp=20)
    bot = build_decision_request(state)["state"]["bot"]
    assert {key: bot.get(key) for key in ("hp", "max_hp", "sp", "max_sp")} == {
        "hp": 42,
        "max_hp": 86,
        "sp": 0,
        "max_sp": 20,
    }


def test_identical_ratios_do_not_hide_different_vitals_capacity() -> None:
    small = build_decision_request(make_state(hp=10, max_hp=20, sp=5, max_sp=10))
    large = build_decision_request(make_state(hp=100, max_hp=200, sp=50, max_sp=100))
    small_bot, large_bot = small["state"]["bot"], large["state"]["bot"]
    assert small_bot["hp_ratio"] == large_bot["hp_ratio"] == 0.5
    assert small_bot["sp_ratio"] == large_bot["sp_ratio"] == 0.5
    assert small_bot["hp"] == 10
    assert large_bot["hp"] == 100
    assert small_bot["max_sp"] == 10
    assert large_bot["max_sp"] == 100
    assert small["questions"] == large["questions"]


def test_vitals_projection_preserves_envelope_without_fabricating_other_stats() -> None:
    request = build_decision_request(make_state(hp=0, max_hp=0, sp=0, max_sp=0))
    assert set(request) == {"model", "state", "questions"}
    assert request["model"] == "clef"
    bot = request["state"]["bot"]
    assert all(bot[key] == 0 for key in ("hp", "max_hp", "sp", "max_sp"))
    assert bot["hp_ratio"] == bot["sp_ratio"] == 0.0
    assert not {"stats", "skills", "equipment", "bonuses", "encounter_history"} & bot.keys()
