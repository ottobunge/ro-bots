"""Adapters: concrete technologies wired to the ports.

- ``clef_local``: Clef-Flash via a llama.cpp-backed SystemOne HTTP service.
- ``clef_remote``: Cloudflare Workers AI ``@cf/cloudflare/clef`` (same API shape).
- ``chat_local``: small local instruct model (llama.cpp OpenAI-compatible server).
- ``chat_remote``: any OpenAI-compatible chat-completions endpoint.
- ``stub``: deterministic doubles for tests and dry runs.
"""

from robots.adapters.chat import ChatRemote, LocalChatServer, StaticChatGenerator
from robots.adapters.decision import ClefLocal, ClefRemote, ScriptedDecisionModel

__all__ = [
    "ChatRemote",
    "ClefLocal",
    "ClefRemote",
    "LocalChatServer",
    "ScriptedDecisionModel",
    "StaticChatGenerator",
]
