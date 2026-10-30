"""Run scheduled native players with explicitly selected real model providers.

Example: python -m robots.playing --manifest ... --runtime-root ...
--memory-root ... --decision-url http://127.0.0.1:8091/v1/systemone
Add --playground --duration 120 for a bounded current-window session.
"""

import argparse
import json
import math
import random
import time
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from robots.adapters.native_navigation import MapCache
from robots.adapters.planning_llm import LocalPlanningModel
from robots.adapters.playing_backends import (
    make_local_chat,
    make_private_chat,
    make_private_decision,
)
from robots.adapters.skill_knowledge import load_skill_knowledge
from robots.app import agent_runtime, command_poller
from robots.app.agent_runtime import AgentHost, ManifestEntry, PersonaClock
from robots.app.planning_brain import PlannedBrain
from robots.app.playing_runtime import ObservedMobDatabase, PlayingClient
from robots.app.scripts import MERCHANT_ROUTE, MERCHANT_ROUTE_RETURN
from robots.domain.planning import PlanningIdentity
from robots.society.models import (
    Attitude,
    FriendGroup,
    Playstyle,
    Schedule,
    ScheduleFactory,
    SocietyPersona,
)
from robots.society.society import ReputationStore, SocialGraph, SocietyRoster


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scheduled native players; no fake fallback")
    for name in ("manifest", "runtime-root", "memory-root"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--decision-url", required=True)
    parser.add_argument("--chat-url", default="http://127.0.0.1:8300/v1/chat/completions")
    parser.add_argument("--worldfeed-port", type=int, default=8400)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--playground", action="store_true")
    parser.add_argument("--schedule-file", type=Path)
    parser.add_argument(
        "--heartbeat-min-s",
        type=float,
        default=None,
        help="Override the decide heartbeat lower bound (default 300s).",
    )
    parser.add_argument(
        "--heartbeat-max-s",
        type=float,
        default=None,
        help="Override the decide heartbeat upper bound (default 1200s).",
    )
    parser.add_argument("--command-root", type=Path, default=None)
    parser.add_argument("--skill-knowledge", type=Path, default=None)
    parser.add_argument("--solo", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--llm-planning", action="store_true")
    parser.add_argument("--planning-world")
    parser.add_argument(
        "--population-file",
        type=Path,
        default=None,
        help=(
            "population.json produced by robots.popgen: wires the social "
            "coordination layer (per-agent ledgers, group objectives, in-game "
            "party formation). Absent keeps today's uncoordinated behavior."
        ),
    )
    parser.add_argument(
        "--seed-zeny-file",
        type=Path,
        default=None,
        help=(
            "JSON {persona_id: balance} seeding each agent's wallet (e2e-43: "
            "the map server sends SP_ZENY on changes only, pc.cpp:5810/5844, "
            "so a clientless client never sees its login balance). Values are "
            "the fixture DB's char.zeny read back before launch."
        ),
    )
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=None,
        help=(
            "Directory for per-agent full-trace JSONL files (<persona>.jsonl: "
            "chats, decides, LLM calls, events, actions, state snapshots). "
            "Default: no tracing."
        ),
    )
    args = parser.parse_args(argv)
    if args.llm_planning:
        try:
            PlanningIdentity("validation", args.planning_world, "validation", 0, "pre-re")
        except ValueError, TypeError:
            parser.error("llm-planning requires an explicit valid planning-world")
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
        parser.error("duration must be finite and positive")
    if args.playground and args.duration is None:
        parser.error("playground requires a bounded duration")
    if not 1 <= args.worldfeed_port <= 65535:
        parser.error("worldfeed port out of range")
    return args


def build_roster(entries: dict[str, ManifestEntry], args: argparse.Namespace) -> SocietyRoster:
    personas = {
        pid: SocietyPersona(
            pid,
            entry.char_name,
            Playstyle.MELEE,
            Attitude.SOLO if args.solo else Attitude.HELPFUL_NEWBIE,
            0.5,
            (1, 99),
        )
        for pid, entry in entries.items()
    }
    rng = random.Random(args.seed)
    ids = sorted(entries)
    members = (
        [(pid,) for pid in ids]
        if args.solo
        else [tuple(ids[i : i + 2]) for i in range(0, len(ids), 2)]
    )
    configured: Any = json.loads(args.schedule_file.read_text()) if args.schedule_file else None
    groups = []
    graph = SocialGraph()
    for index, group_members in enumerate(members):
        schedule = _schedule(args, rng, configured, group_members[0])
        group = FriendGroup(
            f"playing-{index}",
            group_members,
            Attitude.SOLO if len(group_members) == 1 else Attitude.HELPFUL_NEWBIE,
            schedule,
        )
        groups.append(group)
        graph.seed_group(group)
    return SocietyRoster(groups, personas, graph, ReputationStore())


def load_seed_zeny(path: Path | None) -> dict[str, int] | None:
    """Read the --seed-zeny-file mapping ({persona_id: balance}).

    The shepherd writes it from the fixture DB's char.zeny readback before
    launch (e2e-43: the map server sends SP_ZENY on changes only, so the
    login wallet must be seeded). None keeps today's unseeded behavior."""
    if path is None:
        return None
    raw = json.loads(path.read_text())
    return {str(persona): int(balance) for persona, balance in raw.items()}


def build_host(args: argparse.Namespace) -> AgentHost:
    """Construct only; no sockets/model inference before host lifecycle starts."""
    public_skill_knowledge = (
        load_skill_knowledge(args.skill_knowledge, "pre-re") if args.skill_knowledge else None
    )
    entries = agent_runtime.load_manifest(args.manifest)
    root = args.runtime_root
    cache = MapCache.load(root / "db/map_cache.dat", root / "db/pre-re/map_cache.dat")
    # Ground-correct the cited warp/dealer cells: the map-cache tool marks
    # rathena warp cells blocked, but the live server walks players into
    # them (the merchant trip's field leg is cited prtf004 at (170,378)).
    # rathena e985006171d2: npc/pre-re/warps/fields/prontera_fild.txt:65,
    # npc/warps/cities/prontera.txt:25/:40, npc/merchants/shops.txt:255.
    for map_name, (x, y) in {**MERCHANT_ROUTE, **MERCHANT_ROUTE_RETURN}.items():
        cache.mark_walkable(map_name, (x, y))
    catalog = ObservedMobDatabase.load(root / "db/pre-re/mob_db.yml")
    databases = {pid: ObservedMobDatabase(catalog.catalog.values()) for pid in entries}

    from robots.adapters.spawn_species import spawn_species_index  # noqa: PLC0415

    _spawn_index = spawn_species_index(Path("rathena/npc/pre-re/mobs/fields"))

    def spawn_species_for(map_name: str) -> tuple[str, ...]:
        """Declared species for the map (criterion-10 knowledge; w59)."""
        return _spawn_index.get(map_name, ())

    # The travel route, resolved by REACHABILITY from the agent's own cell
    # (leg 37: prt_in is 26 disconnected interiors, each with its own door,
    # so the route table keyed by MAP NAME hands every agent the same door -
    # and for the agent in another interior that door cannot be reached at
    # all). The router needs the client grid, which the composition owns.
    from robots.app.travel_routing import plan_factory, travel_router  # noqa: PLC0415

    _travel_plan_factory = plan_factory(travel_router(cache))

    if urlsplit(args.chat_url).hostname in {"127.0.0.1", "::1"}:
        chat = make_local_chat(args.chat_url)
    else:
        chat = make_private_chat(args.chat_url)
    decision = make_private_decision(args.decision_url)

    # e2e-45: the population runners override the runtime's default client
    # factory, so the wallet seed must ride THIS factory -- the seed-aware
    # default in agent_runtime (_BotClient factory) never runs when a
    # client_factory is supplied, and the leg-45 launch proved it live
    # (state_tick zeny null with the seed file loaded).
    seed_zeny_by_persona = load_seed_zeny(getattr(args, "seed_zeny_file", None)) or {}

    def client_factory(entry: ManifestEntry) -> PlayingClient:
        native = vars(agent_runtime)["_BotClient"]
        if native is None:
            message = "native client unavailable; refusing fake fallback"
            raise RuntimeError(message)
        wire = native(
            entry.account,
            entry.password,
            char_name=entry.char_name,
            verbose=False,
            login_ip=entry.login_host,
            login_port=entry.login_port,
            pincode=entry.pincode,
            create_char=False,
        )
        return PlayingClient(
            wire,
            databases[entry.persona_id],
            cache=cache,
            public_skill_knowledge=public_skill_knowledge,
            seed_zeny=seed_zeny_by_persona.get(entry.persona_id),
        )

    return AgentHost(
        build_roster(entries, args),
        args.manifest,
        heartbeat_min_s=getattr(args, "heartbeat_min_s", None) or 300.0,
        heartbeat_max_s=getattr(args, "heartbeat_max_s", None) or 1200.0,
        decision_factory=lambda: decision,
        chat_generator=chat,
        client_factory=client_factory,
        mob_db_factory=databases.__getitem__,
        spawn_species_factory=spawn_species_for,
        travel_plan_factory=_travel_plan_factory,
        memory_root=args.memory_root,
        worldfeed_port=args.worldfeed_port,
        population_file=getattr(args, "population_file", None),
        seed_zeny_by_persona=seed_zeny_by_persona or None,
        trace_dir=getattr(args, "trace_dir", None),
        brain_factory=(
            (
                lambda persona, entry, memory: PlannedBrain(
                    PlanningIdentity(
                        persona.persona_id, args.planning_world, entry.char_name, 0, "pre-re"
                    ),
                    memory,
                    decision,
                    lambda: LocalPlanningModel(
                        "http://127.0.0.1:8300", "local", 30, 512, token_ceiling=4096
                    ),
                )
            )
            if args.llm_planning
            else None
        ),
    )


def run_host(host: AgentHost, duration: float | None, command_root: Path | None = None) -> None:
    """Run the scheduling loop; with ``command_root``, poll dashboard commands."""
    deadline = time.monotonic() + duration if duration is not None else None
    try:
        host.start_worldfeed()
        while deadline is None or time.monotonic() < deadline:
            host.step()
            if command_root is not None:
                command_poller.poll_once(host, command_root)
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())) if deadline else 1.0)
    except BaseException as origin:
        try:
            host.stop()
        except BaseException as cleanup:
            # Shutdown diagnostics must not expose provider or manifest values.
            with suppress(BaseException):
                origin.add_note(
                    f"host shutdown failed ({type(cleanup).__name__}); release unconfirmed"
                )
        raise
    else:
        host.stop()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_host(build_host(args), args.duration, getattr(args, "command_root", None))
    except KeyboardInterrupt:
        return 0
    except Exception:
        # Model endpoints/manifest values must not enter exception logs.
        return 1
    return 0


def _schedule(
    args: argparse.Namespace, rng: random.Random, configured: Any, persona_id: str
) -> Schedule:
    schedule = ScheduleFactory.make_group_schedule(rng)
    if configured is not None:
        schedule = Schedule(tuple(tuple(row) for row in configured[persona_id]))
    if args.playground:
        day, hour = PersonaClock().local_now()
        end = hour + args.duration / 3600 + 1 / 60
        schedule = Schedule(((day, hour, min(end, 24.0)),))
        if end > 24:
            schedule = Schedule(((day, hour, 24.0), ((day + 1) % 7, 0.0, end - 24)))
    return schedule


if __name__ == "__main__":
    raise SystemExit(main())
