"""Read-only listing of per-agent memory files.

v1 lists files (path, size, mtime) whose relative path contains the agent's
name; it never reads file contents and never follows symlinks out of the root.
"""

from __future__ import annotations

import os

from dashboard_webapp.models import MemoryFile

DEFAULT_CAP = 50
MAX_DEPTH = 6


class MemoryViewer:
    def __init__(self, root: str | None, cap: int = DEFAULT_CAP) -> None:
        self.root = root
        self._cap = cap

    def list(self, needle: str) -> list[MemoryFile]:
        """Memory files matching ``needle`` (case-insensitive), newest first."""
        if not self.root or not needle:
            return []
        base = os.path.realpath(self.root)
        if not os.path.isdir(base):
            return []
        found: list[MemoryFile] = []
        lowered = needle.lower()
        for current, dirs, files in os.walk(base):
            depth = os.path.relpath(current, base).count(os.sep)
            if depth >= MAX_DEPTH:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
            for name in files:
                full = os.path.join(current, name)
                if os.path.islink(full):
                    continue
                rel = os.path.relpath(full, base)
                if lowered not in rel.lower():
                    continue
                try:
                    info = os.stat(full)
                except OSError:
                    continue
                found.append(
                    MemoryFile(
                        path=rel,
                        size_bytes=info.st_size,
                        modified_ts=float(info.st_mtime),
                    )
                )
        found.sort(key=lambda f: f.modified_ts, reverse=True)
        return found[: self._cap]
