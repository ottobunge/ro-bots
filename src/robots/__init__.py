"""ro-bots: Clef-driven bot players for a private rAthena server.

Hexagonal architecture: the application core (``robots.app``) depends only on
ports (``robots.ports``); every concrete technology — llama.cpp, Cloudflare
Workers AI, the rAthena wire protocol — lives behind an adapter in
``robots.adapters``.
"""

__version__ = "0.1.0"
