"""Fail-closed default entry for the fixed received Bard NEXT pilot."""

import sys

from pilot_inputs import (
    Inputs,
    Lock,
    assemble_native,
    read_inputs,
    read_private,
    reviewed_lock,
    validate_private,
    validate_row,
)
from probe import Pilot

__all__ = [
    "Inputs",
    "Lock",
    "assemble_native",
    "read_inputs",
    "read_private",
    "reviewed_lock",
    "validate_private",
    "validate_row",
]


def main() -> int:
    try:
        pilot = Pilot(assemble_native())
        report = pilot.run()
        return 0 if report["passed"] else 1
    except Exception:
        return 2


if __name__ == "__main__":
    sys.exit(main())
