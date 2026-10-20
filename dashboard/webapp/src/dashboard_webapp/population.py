"""Population generation over ``robots.popgen``: spec -> world artifacts.

The dashboard never touches the database here: :class:`PopgenStore` runs the
deterministic generator and writes ``manifest.json`` + ``population.json`` +
``fixture.sql`` into a fresh ``population/<id>`` directory under the world
dir (never over existing world files). Applying the fixture to the world's
MariaDB is the separate, explicit :mod:`dashboard_webapp.db_applier` step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from dashboard_webapp.repository import DataSourceError

WORLD_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,63}$"
DEFAULT_WORLDS_ROOT = Path("run/worlds")


class InvalidPopulationSpec(ValueError):
    """The spec is rejected by the generator (mapped to HTTP 422)."""


class PopulationNotFound(Exception):
    """Unknown world or population id (mapped to HTTP 404)."""


class PopulationRequest(BaseModel):
    """The PopulationSpec fields plus the target world name."""

    world: str = Field(pattern=WORLD_PATTERN)
    friend_groups: int = Field(ge=0, le=64)
    friends_per_group: tuple[int, int] = Field(default=(2, 4))
    solo_agents: int = Field(ge=0, le=512)
    seed: int = Field(ge=0, le=2**31 - 1)

    @model_validator(mode="after")
    def _valid_spec(self) -> PopulationRequest:
        low, high = self.friends_per_group
        if not 2 <= low <= high <= 12:
            raise ValueError("friends_per_group must be 2 <= min <= max <= 12")
        if self.friend_groups == 0 and self.solo_agents == 0:
            raise ValueError("empty population: friend_groups or solo_agents required")
        return self


@dataclass(frozen=True)
class PopulationArtifact:
    population_id: str
    world: str
    counts: dict[str, int]
    paths: dict[str, str]
    fixture_sql: str


class PopulationStore(Protocol):
    def generate(self, request: PopulationRequest) -> PopulationArtifact: ...


class PopgenStore:
    """Generates with the real popgen and writes the world-ready artifacts."""

    def __init__(self, worlds_root: Path) -> None:
        self._worlds_root = Path(worlds_root)

    def generate(self, request: PopulationRequest) -> PopulationArtifact:
        world_dir = self._worlds_root / request.world
        if not world_dir.is_dir():
            raise PopulationNotFound(f"unknown world: {request.world}")
        population = self._run_generator(request)
        summary = population.summary()
        population_id = f"pop-{uuid4().hex[:12]}"
        out_dir = world_dir / "population" / population_id
        out_dir.mkdir(parents=True)
        manifest_path = out_dir / "manifest.json"
        summary_path = out_dir / "population.json"
        fixture_path = out_dir / "fixture.sql"
        manifest_path.write_text(json.dumps(population.manifest, indent=1) + "\n", encoding="utf-8")
        summary_path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        fixture_path.write_text(population.fixture_sql, encoding="utf-8")
        return PopulationArtifact(
            population_id=population_id,
            world=request.world,
            counts={str(key): int(value) for key, value in summary["counts"].items()},
            paths={
                "dir": str(out_dir),
                "manifest": str(manifest_path),
                "population": str(summary_path),
                "fixture": str(fixture_path),
            },
            fixture_sql=population.fixture_sql,
        )

    @staticmethod
    def _run_generator(request: PopulationRequest) -> Any:
        """The real ``robots.popgen`` call (stdlib-only; imported lazily)."""
        try:
            from robots.popgen import PopulationSpec, generate_population
        except ImportError as exc:  # pragma: no cover - deployment wiring
            raise DataSourceError(
                "population generator unavailable: robots.popgen is not importable"
            ) from exc
        spec = PopulationSpec(
            friend_groups=request.friend_groups,
            friends_per_group=tuple(request.friends_per_group),
            solo_agents=request.solo_agents,
            seed=request.seed,
        )
        try:
            return generate_population(spec)
        except ValueError as exc:
            raise InvalidPopulationSpec(str(exc)) from exc
