"""The private-network chat constructor (heavengraph LLM)."""

from robots.adapters.playing_backends import make_private_chat


def test_private_chat_accepts_the_private_network_host() -> None:
    chat = make_private_chat("http://192.168.1.156:8092/v1/chat/completions")
    assert chat is not None
