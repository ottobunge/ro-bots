"""Port conformance + adapter unit tests (offline; HTTP mocked at boundary)."""

import httpx
import pytest

from robots.adapters.chat._http import ChatError, post_chat
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision._http import SystemOneError, post_systemone
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.ports import (
    ActionAdvisor,
    ChatGenerator,
    DecisionModel,
    GameClient,
    TickClock,
)


class FakeModel:
    def decide(self, request: dict) -> dict:
        return {"answers": {}}


class FakeChat:
    def generate_chat(self, prompt: str) -> str:
        return "hi"


class FakeClient:
    def poll_state(self) -> object:
        return None

    def act(self, action: object) -> None:
        return None


class FakeClock:
    def sleep(self, seconds: float) -> None:
        return None

    def monotonic(self) -> float:
        return 0.0


class FakeAdvisor:
    def advise(self, state: object, question: str, options: list[str]) -> int | None:
        return None


def test_stubs_satisfy_ports() -> None:
    assert isinstance(ScriptedDecisionModel(), DecisionModel)
    assert isinstance(StaticChatGenerator(), ChatGenerator)
    assert isinstance(FakeClient(), GameClient)
    assert isinstance(FakeClock(), TickClock)
    assert isinstance(FakeAdvisor(), ActionAdvisor)
    assert isinstance(FakeModel(), DecisionModel)
    assert isinstance(FakeChat(), ChatGenerator)


def test_scripted_model_queue_then_fixed() -> None:
    model = ScriptedDecisionModel(answers={"a": 1}, queue=[{"a": 2}, {"a": 3}])
    assert model.decide({})["answers"] == {"a": 2}
    assert model.decide({})["answers"] == {"a": 3}
    assert model.decide({})["answers"] == {"a": 1}
    assert model.calls == 3


def test_static_chat_cycles() -> None:
    chat = StaticChatGenerator(["x", "y"])
    assert chat.generate_chat("p") == "x"
    assert chat.generate_chat("p") == "y"
    assert chat.generate_chat("p") == "x"


def _mock_httpx(monkeypatch: pytest.MonkeyPatch, payload: object, status: int = 200) -> list[dict]:
    calls: list[dict] = []

    def fake_post(
        url: str,
        json: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> object:
        calls.append({"url": url, "json": json, "headers": headers})
        return _Response(payload, status)

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


class _Response:
    def __init__(self, payload: object, status: int) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            msg = f"HTTP {self.status_code}"
            raise httpx.HTTPError(msg)

    def json(self) -> object:
        return self._payload


def test_post_systemone_validates_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_httpx(monkeypatch, {"answers": {"q": {"noul": 0.9}}})
    body = post_systemone("http://x/v1/systemone", {"state": {}})
    assert body["answers"]["q"]["noul"] == 0.9


def test_post_systemone_rejects_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_httpx(monkeypatch, {"unexpected": True})
    with pytest.raises(SystemOneError, match="answers"):
        post_systemone("http://x/v1/systemone", {"state": {}})


def test_post_systemone_wraps_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_httpx(monkeypatch, {}, status=500)
    with pytest.raises(SystemOneError, match="failed"):
        post_systemone("http://x/v1/systemone", {"state": {}})


def test_post_chat_extracts_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_httpx(monkeypatch, {"choices": [{"message": {"content": "hello"}}]})
    assert post_chat("http://x/v1/chat/completions", {}) == "hello"


def test_post_chat_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_httpx(monkeypatch, {"nope": 1})
    with pytest.raises(ChatError, match="malformed"):
        post_chat("http://x/v1/chat/completions", {})
