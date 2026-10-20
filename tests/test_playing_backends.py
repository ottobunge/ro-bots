"""Offline provider contracts; no network or native game connections."""

import importlib
from typing import Any

import httpx
import pytest

from robots.adapters import playing_backends as backend


@pytest.mark.parametrize("fault", ["http", "timeout", "invalid-json", "failure", "missing"])
def test_workers_failure_is_sanitized_and_has_no_fallback(monkeypatch, caplog, fault):
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        request = httpx.Request("POST", url)
        if fault == "timeout":
            msg = "private-token sensitive-url"
            raise httpx.ReadTimeout(msg, request=request)
        if fault == "http":
            return httpx.Response(429, text="private-token", request=request)
        if fault == "invalid-json":
            return httpx.Response(200, text="private-token", request=request)
        body = {"success": False, "errors": ["private-token"]} if fault == "failure" else {}
        return httpx.Response(200, json=body, request=request)

    monkeypatch.setattr(httpx, "post", post)
    provider = backend.make_workers_decision("a" * 32, "private-token", timeout=7.0)
    with pytest.raises(backend.PlayingBackendError) as caught:
        provider.decide({"state": {}, "questions": {}})
    assert len(calls) == 1
    assert calls[0]["timeout"] == 7.0
    assert "private-token" not in str(caught.value)
    assert "a" * 32 not in str(caught.value)
    assert caught.value.__suppress_context__
    assert "private-token" not in caplog.text


def test_local_chat_uses_real_completion_contract(monkeypatch):
    seen: dict[str, Any] = {}

    def post(url, **kwargs):
        seen.update(url=url, **kwargs)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Let's explore."}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    chat = backend.make_local_chat("http://127.0.0.1:8300/v1/chat/completions", timeout=9)
    assert chat.generate_chat("Say hello") == "Let's explore."
    assert seen["json"]["messages"][-1] == {"role": "user", "content": "Say hello"}
    assert seen["json"]["max_tokens"] == 60
    assert seen["timeout"] == 9
    assert not seen["headers"]


@pytest.mark.parametrize("content", [None, "", 42])
def test_chat_rejects_nontext_or_empty_content(monkeypatch, content):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **_kwargs: httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
            request=httpx.Request("POST", url),
        ),
    )
    with pytest.raises(backend.PlayingBackendError):
        backend.make_local_chat("http://127.0.0.1:8300/v1/chat/completions").generate_chat("Hi")


def test_local_decision_preserves_answers_without_workers_envelope(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **_kwargs: httpx.Response(
            200,
            json={"answers": {"action": {"choice": "rest", "confidence": 0.8}}},
            request=httpx.Request("POST", url),
        ),
    )
    provider = backend.make_local_decision("http://127.0.0.1:8302/v1/systemone", timeout=90)
    assert provider.decide({"questions": {"action": {"type": "choice"}}}) == {
        "answers": {"action": {"choice": "rest", "confidence": 0.8}}
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"account_id": "invalid", "api_token": "token"},
        {"account_id": "a" * 32, "api_token": ""},
        {"account_id": "a" * 32, "api_token": "token", "model": "clef-27b"},
        {"account_id": "a" * 32, "api_token": "token", "timeout": 0},
    ],
)
def test_workers_rejects_invalid_config_without_network(monkeypatch, kwargs):
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *args, **_kw: calls.append(args))
    with pytest.raises(ValueError, match=r"required|must"):
        backend.make_workers_decision(**kwargs)
    assert not calls


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/v1/chat/completions",
        "http://user:pass@127.0.0.1:8300/v1/chat/completions",
    ],
)
def test_local_chat_rejects_remote_or_credentialed_url(url):
    with pytest.raises(ValueError, match=r"required|must"):
        backend.make_local_chat(url)


def test_private_decision_requires_explicit_plain_endpoint(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **_kwargs: httpx.Response(
            200,
            json={"answers": {"action": {"choice": "rest"}}},
            request=httpx.Request("POST", url),
        ),
    )
    provider = backend.make_private_decision("http://192.168.1.156:8091/v1/systemone")
    assert provider.decide({}) == {"answers": {"action": {"choice": "rest"}}}
    with pytest.raises(ValueError, match=r"required|must"):
        backend.make_private_decision("https://example.com/v1/systemone")


def test_workers_flash_url_matches_model_and_unwraps_answers(monkeypatch):
    module = importlib.import_module("robots.adapters.playing_backends")
    observed: dict[str, Any] = {}

    def post(url, **kwargs):
        observed.update(url=url, **kwargs)
        return httpx.Response(
            200,
            json={"success": True, "result": {"answers": {"safe": {"probability": 0.9}}}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", post)
    provider = module.make_workers_decision("a" * 32, "private-token", model="clef-flash")
    request = {"state": {"hp": 80}, "questions": {"safe": {"type": "noul"}}}
    assert provider.decide(request) == {"answers": {"safe": {"probability": 0.9}}}
    assert observed["url"].endswith("/ai/run/@cf/cloudflare/clef-flash")
    assert observed["json"]["model"] == "clef-flash"
    assert "model" not in request
