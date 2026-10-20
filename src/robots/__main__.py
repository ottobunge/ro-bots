"""ro-bots agent host: run N scheduled agents against the live rAthena server.

Usage (from the repo root):

  uv run python -m robots --manifest run/test-world-manifest.json \
      --tick-seconds 2 [--clef-url http://127.0.0.1:8300/v1/systemone] \
      [--worldfeed-port 8400] [--max-agents 4]

Ctrl-C disconnects every online agent gracefully (each writes its session
memory note) and shuts the WorldFeed server down.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import random
import sys

from robots.app.agent_runtime import DEFAULT_TICK_SECONDS, AgentHost, PersonaClock
from robots.app.host_memory_factory import validate_summary_cache
from robots.society.society import SocietyRoster

logger = logging.getLogger("robots.runner")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m robots",
        description="AgentHost: scheduled agents on the live server + WorldFeed",
    )
    parser.add_argument(
        "--manifest",
        default="run/test-world-manifest.json",
        help="persona->account/char manifest (default: run/test-world-manifest.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="society seed for SocietyRoster.build (default: 42)",
    )
    parser.add_argument(
        "--n-groups",
        type=int,
        default=3,
        help="groups for SocietyRoster.build; must match the manifest (default: 3)",
    )
    parser.add_argument(
        "--tick-seconds",
        type=float,
        default=DEFAULT_TICK_SECONDS,
        help="agent loop tick period in seconds (default: 2)",
    )
    parser.add_argument(
        "--clef-url",
        default=None,
        help="SystemOne endpoint; unset = ScriptedDecisionModel stub",
    )
    parser.add_argument(
        "--worldfeed-port",
        type=int,
        default=8400,
        help="WorldFeed API port (default: 8400)",
    )
    parser.add_argument(
        "--max-agents",
        type=int,
        default=0,
        help="cap on concurrently scheduled-on agents (0 = all scheduled-on)",
    )
    parser.add_argument(
        "--memory-root",
        type=pathlib.Path,
        default=None,
        help="opt-in private journals in an explicitly world-specific directory",
    )
    parser.add_argument(
        "--summary-cache-world",
        default=None,
        help="explicit literal cache world ID; requires --memory-root and --summary-cache-policy",
    )
    parser.add_argument(
        "--summary-cache-policy",
        default=None,
        help="opaque literal cache policy ID; summary backend remains the 120-character stub",
    )
    args = parser.parse_args(argv)
    try:
        validate_summary_cache(
            args.memory_root, args.summary_cache_world, args.summary_cache_policy
        )
    except ValueError as exc:
        parser.error(str(exc))
    return args


def build_host(args: argparse.Namespace) -> AgentHost:
    """Construct the host from CLI args (also the seam tests use)."""
    validate_summary_cache(args.memory_root, args.summary_cache_world, args.summary_cache_policy)
    roster = SocietyRoster.build(random.Random(args.seed), n_groups=args.n_groups)
    return AgentHost(
        roster,
        pathlib.Path(args.manifest),
        clef_url=args.clef_url,
        worldfeed_port=args.worldfeed_port,
        tick_seconds=args.tick_seconds,
        clock=PersonaClock(),
        memory_root=args.memory_root,
        summary_cache_world=args.summary_cache_world,
        summary_cache_policy=args.summary_cache_policy,
        max_agents=args.max_agents,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = parse_args(argv)
    host = build_host(args)
    scheduled = ", ".join(host.agents) or "(none)"
    decision = "Clef" if args.clef_url else "ScriptedDecisionModel (stub)"
    logger.info(
        "agent host: agents=[%s] decision=%s tick=%.1fs worldfeed=:%d",
        scheduled,
        decision,
        args.tick_seconds,
        args.worldfeed_port,
    )
    try:
        host.run()
    except KeyboardInterrupt:
        logger.info("Ctrl-C: disconnecting all agents (session notes written)")
    finally:
        host.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
