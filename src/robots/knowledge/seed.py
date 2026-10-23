"""Memory-journal-ready base game-knowledge lines for seeding new agents.

The coordinator renders these once into a fresh agent's memory journal; the
CALLER owns any persistence — this module only returns lines and never
writes to a live memory directory. The guild lines carry the project-verified
facts (the charter packet path proven in the e2e world); the leveling lines
point at the wiki guides and the established economy loop; the build lines
are rendered from the tracked per-class sidecars under
``run/knowledge/builds/pre-re/``.
"""

import json
from pathlib import Path
from typing import Any

from robots.knowledge import corpora

DEFAULT_BUILDS_DIR = Path("run/knowledge/builds/pre-re")
MAX_LINE_CHARS = corpora.MAX_LINE_CHARS
MAX_BUILD_LINES = 40

GUILD_LINES: tuple[str, ...] = (
    (
        "guild know-how: creating a guild needs an Emperium (item 714) on the leader; "
        "create the guild by name, then invite members (join by accepting)"
    ),
    (
        "guild wire facts (verified live): charter CZ_REQ_MAKE_GUILD 0x0165, "
        "reply ZC_RESULT_MAKE_GUILD 0x0167"
    ),
)

LEVELING_LINES: tuple[str, ...] = (
    "leveling pointers: wiki 'Leveling Spots' maps level ranges to fields and dungeons",
    "established early loop: grind prt_fild08 (Poring/Fabre/Pupa/Rocker), sell loot in Prontera",
)


def seed_knowledge_lines(builds_dir: Path | None = None) -> tuple[str, ...]:
    """The base game-knowledge journal lines (guild, leveling, builds)."""
    directory = builds_dir if builds_dir is not None else DEFAULT_BUILDS_DIR
    lines = [*GUILD_LINES, *LEVELING_LINES, *_build_lines(directory)]
    return tuple(line[:MAX_LINE_CHARS] for line in lines)


def _build_lines(directory: Path) -> list[str]:
    """One line per build sidecar (class + playstyle + summary), sorted by stem."""
    if not directory.is_dir():
        return []
    lines: list[str] = []
    for path in sorted(directory.glob("*.json")):
        payload = _sidecar(path)
        if payload is None:
            continue
        klass = str(payload.get("class", "")).strip()
        if not klass:
            continue
        playstyle = str(payload.get("playstyle", "")).strip()
        summary = str(payload.get("summary", "")).strip()
        lines.append(f"build {klass} ({playstyle}): {summary}")
        if len(lines) >= MAX_BUILD_LINES:
            break
    return lines


def _sidecar(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return payload if isinstance(payload, dict) else None
