"""Adapters: concrete technologies wired to the ports.

Provider classes are loaded only when explicitly requested, so importing pure
protocol decoders does not require optional HTTP or YAML dependencies.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from robots.adapters.chat import ChatRemote, LocalChatServer, StaticChatGenerator
    from robots.adapters.decision import ClefLocal, ClefRemote, ScriptedDecisionModel
    from robots.adapters.mechanics_stub import StubMechanics, YamlMechanics

__all__ = [
    "ChatRemote",
    "ClefLocal",
    "ClefRemote",
    "LocalChatServer",
    "ScriptedDecisionModel",
    "StaticChatGenerator",
    "StubMechanics",
    "YamlMechanics",
]

_EXPORT_MODULES = {
    "ChatRemote": "robots.adapters.chat",
    "ClefLocal": "robots.adapters.decision",
    "ClefRemote": "robots.adapters.decision",
    "LocalChatServer": "robots.adapters.chat",
    "ScriptedDecisionModel": "robots.adapters.decision",
    "StaticChatGenerator": "robots.adapters.chat",
    "StubMechanics": "robots.adapters.mechanics_stub",
    "YamlMechanics": "robots.adapters.mechanics_stub",
}


def __getattr__(name: str) -> Any:
    """Resolve and cache only the explicitly listed public adapter classes."""
    if name not in _EXPORT_MODULES:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message)
    value = getattr(import_module(_EXPORT_MODULES[name]), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Advertise public classes without eagerly importing their providers."""
    return sorted(set(globals()) | set(__all__))
