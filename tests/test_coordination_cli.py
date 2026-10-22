"""CLI forwarding: --population-file through parse_args/build_host/runner.

Mirrors tests/test_playing_runtime.py's synthetic runtime-root recipe (tiny
map cache + mob db) so build_host constructs offline, no sockets, no
inference — the wiring claim is about what the host RECEIVES.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path

from robots import playing
from robots.adapters.native_navigation import ENTRY, HEADER
from robots.popgen import PopulationSpec, generate_population
from robots.society.objectives import BoundCoordinator

WIRED_SPEC = PopulationSpec(friend_groups=1, friends_per_group=(2, 2), solo_agents=0, seed=11)


def synthetic_runtime_root(tmp_path: Path) -> None:
    """The offline map cache + mob db that build_host loads at construction."""
    (tmp_path / "db/pre-re").mkdir(parents=True, exist_ok=True)
    for relative in ("db/map_cache.dat", "db/pre-re/map_cache.dat"):
        body = zlib.compress(bytes(4))
        data = ENTRY.pack(b"prontera", 2, 2, len(body)) + body
        (tmp_path / relative).write_bytes(HEADER.pack(HEADER.size + len(data), 1) + data)
    (tmp_path / "db/pre-re/mob_db.yml").write_text("Body: []\n")


def write_population_files(tmp_path: Path) -> tuple[Path, Path]:
    population = generate_population(WIRED_SPEC)
    summary_path = tmp_path / "population.json"
    summary_path.write_text(json.dumps(population.summary(), indent=1) + "\n")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(population.manifest))
    return summary_path, manifest_path


def base_argv(tmp_path: Path, manifest_path: Path) -> list[str]:
    return [
        "--manifest",
        str(manifest_path),
        "--runtime-root",
        str(tmp_path),
        "--memory-root",
        str(tmp_path / "memory"),
        "--decision-url",
        "http://127.0.0.1:8091/v1/systemone",
    ]


def test_parse_args_population_file_defaults_to_none() -> None:
    args = playing.parse_args(
        ["--manifest", "m", "--runtime-root", "r", "--memory-root", "mem", "--decision-url", "d"]
    )
    assert args.population_file is None


def test_parse_args_accepts_the_population_file(tmp_path: Path) -> None:
    summary_path, manifest_path = write_population_files(tmp_path)
    argv = [*base_argv(tmp_path, manifest_path), "--population-file", str(summary_path)]
    args = playing.parse_args(argv)
    assert args.population_file == summary_path


def test_build_host_wires_coordination_from_the_population_file(
    tmp_path: Path,
) -> None:
    synthetic_runtime_root(tmp_path)
    summary_path, manifest_path = write_population_files(tmp_path)
    argv = [*base_argv(tmp_path, manifest_path), "--population-file", str(summary_path)]
    args = playing.parse_args(argv)
    host = playing.build_host(args)
    try:
        assert host.agents
        for agent in host.agents.values():
            brain = getattr(agent, "brain", None)
            assert brain is not None
            assert isinstance(brain._coordination, BoundCoordinator)
        ledger_files = {p.name for p in (tmp_path / "memory" / "relations").glob("*.json")}
        assert ledger_files == {f"{pid}.json" for pid in host.agents}
    finally:
        host.stop()


def test_build_host_without_the_flag_keeps_coordination_none(
    tmp_path: Path,
) -> None:
    synthetic_runtime_root(tmp_path)
    _summary_path, manifest_path = write_population_files(tmp_path)
    args = playing.parse_args(base_argv(tmp_path, manifest_path))
    host = playing.build_host(args)
    try:
        for agent in host.agents.values():
            brain = getattr(agent, "brain", None)
            assert brain is not None
            assert brain._coordination is None
    finally:
        host.stop()
