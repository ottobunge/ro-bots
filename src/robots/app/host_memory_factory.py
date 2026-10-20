"""Pure preflight for explicit host summary-cache namespaces (no I/O)."""

import re
from pathlib import Path


def validate_summary_cache(memory_root: Path | None, world: str | None, policy: str | None) -> None:
    """Require a root and two literal IDs; labels confer no world authority."""
    if world is None and policy is None:
        return
    if memory_root is None or world is None or policy is None:
        msg = "summary cache requires memory_root, summary_cache_world and summary_cache_policy"
        raise ValueError(msg)
    for identifier in (world, policy):
        if (
            type(identifier) is not str
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identifier) is None
        ):
            msg = "summary cache IDs must be literal safe ASCII identifiers (1-128 characters)"
            raise ValueError(msg)
