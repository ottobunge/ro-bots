"""Tests for the escalation policy (Clef -> LLM hand-off rules)."""

from robots.app.escalation import EscalationPolicy


def test_no_escalation_when_confident_and_quiet() -> None:
    policy = EscalationPolicy()
    answers = {"next_action": {"confidence": 0.9}}
    escalate, reason = policy.needs_escalation(answers, chat_directed_at_bot=False)
    assert escalate is False
    assert reason == ""


def test_escalate_on_low_confidence() -> None:
    policy = EscalationPolicy(confidence_floor=0.6)
    answers = {"next_action": {"confidence": 0.4}}
    escalate, reason = policy.needs_escalation(answers, chat_directed_at_bot=False)
    assert escalate is True
    assert reason == "low_confidence"


def test_escalate_on_directed_chat() -> None:
    policy = EscalationPolicy()
    answers = {"next_action": {"confidence": 0.99}}
    escalate, reason = policy.needs_escalation(answers, chat_directed_at_bot=True)
    assert escalate is True
    assert reason == "chat_reply"


def test_chat_escalation_can_be_disabled() -> None:
    policy = EscalationPolicy(reply_chat_always=False)
    answers = {"next_action": {"confidence": 0.99}}
    escalate, _ = policy.needs_escalation(answers, chat_directed_at_bot=True)
    assert escalate is False
