"""Blocked gameplay E2E entrypoint with inert owned-test reset planning.

No native server fallback, TCP fallback, fake gameplay evidence or lifecycle
executor remains here. Unit-tested plans are not live isolation acceptance.
"""

from __future__ import annotations

import pathlib
import subprocess  # public side-effect spy seam
import sys

__all__ = ["main", "reset_plan", "subprocess"]

PROJ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))

from scripts.seed_test_agents import Data, require, validate_world  # noqa: E402


def reset_plan(config: Data, observed: Data) -> tuple[tuple[str, ...], ...]:
    """Return, never execute, commands for one exclusive stopped test volume.

    External volumes are NOT removed by compose down -v. Removal is explicit,
    names the exact test volume, and contains no force/prune/other-world command.
    A future executor must hold a world lock and re-inspect immediately before
    every mutation; JSON supplied by a caller cannot authorize these commands.
    """
    validate_world(config, observed)
    container = observed["db_container"]
    require(container.get("state") == "stopped")
    require(
        observed.get("volume_users")
        == [
            {
                "id": container["id"],
                "project": "ro-bots-test",
                "service": "mariadb",
                "state": "stopped",
            }
        ]
    )
    return (
        ("docker", "container", "rm", container["id"]),
        ("docker", "volume", "rm", "ro-bots-world-test"),
        (
            "docker",
            "volume",
            "create",
            "--label",
            "ro-bots.world=test",
            "--label",
            "ro-bots.project=ro-bots-test",
            "ro-bots-world-test",
        ),
    )


def main() -> int:
    print(  # noqa: T201
        "[e2e] blocked: isolated-world routing and owned test-volume reset are not verified; "
        "shared native fallback is disabled; gameplay acceptance is not implemented",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
