"""Chat-generation adapters: local llama-server first, remote API compatible."""

from robots.adapters.chat.chat_local import LocalChatServer
from robots.adapters.chat.chat_remote import ChatRemote
from robots.adapters.chat.stub import StaticChatGenerator

__all__ = ["ChatRemote", "LocalChatServer", "StaticChatGenerator"]
