"""The integration seam: calculator/projection/wiki lines reach the decide
state through the real brain request builder, under the payload budget."""

import json
from pathlib import Path

import pytest

from robots.domain.decisions import build_decision_request
from robots.domain.events import Heartbeat
from robots.domain.model import Goal
from robots.knowledge import game_context
from tests.conftest import make_state
from tests.test_brain import make_brain
from tests.test_game_context import _build_iro_db, _build_iro_wiki
from tests.test_native_shop_selection import actual_clients
from tests.test_native_stat_setup import DEX, STR, status_table


@pytest.fixture
def fake_corpora(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    iro_db = tmp_path / "iro-db.db"
    iro_wiki = tmp_path / "iro-wiki.db"
    _build_iro_db(iro_db)
    _build_iro_wiki(iro_wiki)
    monkeypatch.setenv("RO_BOTS_IRO_DB", str(iro_db))
    monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(iro_wiki))
    return tmp_path


def test_received_stats_flow_into_the_decide_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """The 0x00BD six-stat table lands on BotState.received_stats (w64 wire)."""
    monkeypatch.delenv("RO_BOTS_IRO_DB", raising=False)
    monkeypatch.delenv("RO_BOTS_IRO_WIKI", raising=False)
    _wire, client, receive, _sent = actual_clients(monkeypatch)
    receive(status_table(9, {STR: 9, 14: 1, 15: 1, 16: 1, DEX: 9, 18: 1}))
    state = client.build_native_state(Goal.GRIND)
    assert state.received_stats == (9, 1, 1, 1, 9, 1)


def test_brain_request_carries_game_knowledge(fake_corpora: Path) -> None:
    brain = make_brain(answers={"next_action": {"type": "choice", "choice": "grind"}})
    state = make_state(
        base_level=10,
        received_stats=(9, 1, 1, 1, 9, 1),
        inventory={"915": 2, "1201": 1},
    )
    request = brain._decision_request(state, Heartbeat(1))
    lines = request["state"]["game_knowledge"]
    assert any("Chrysalis" in line and "sellable 4z" in line for line in lines)
    assert any("Poring" in line for line in lines)
    assert len(lines) <= game_context.MAX_DECIDE_LINES


def test_brain_request_without_corpora_has_no_game_knowledge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RO_BOTS_IRO_DB", str(tmp_path / "missing.db"))
    monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(tmp_path / "missing.db"))
    brain = make_brain(answers={"next_action": {"type": "choice", "choice": "grind"}})
    state = make_state()
    request = brain._decision_request(state, Heartbeat(1))
    assert "game_knowledge" not in request["state"]


class TestPayloadBudget:
    """The decide payload stays under ~2600 tokens with the knowledge lines on.

    Token estimate: 4 characters per token (the usual conservative English
    JSON ratio used for the ~2200-token baseline payload).
    """

    TOKENS = 4  # chars per token

    def _payload(self, with_corpora: bool, monkeypatch=None):
        state = make_state(
            base_level=10,
            received_stats=(9, 1, 1, 1, 9, 1),
            inventory={"915": 2, "1201": 1, "938": 4},
            recent_chat=(),
        )
        lines = game_context.decide_knowledge_lines(state) if with_corpora else None
        return build_decision_request(state, knowledge_lines=lines)

    def test_budget_holds_with_lines_on(self, fake_corpora: Path) -> None:
        request = self._payload(with_corpora=True)
        chars = len(json.dumps(request))
        assert chars / self.TOKENS < 2600, f"decide payload too big: {chars} chars"

    def test_lines_add_bounded_headroom(self, fake_corpora: Path) -> None:
        on = len(json.dumps(self._payload(with_corpora=True))) / self.TOKENS
        off = len(json.dumps(self._payload(with_corpora=False))) / self.TOKENS
        assert on - off <= 150, f"knowledge lines added {on - off:.0f} tokens"
