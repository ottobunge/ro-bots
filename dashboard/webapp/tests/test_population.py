"""Population generation endpoints + the popgen-backed store (real generator)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.commands import JsonlCommandQueue
from dashboard_webapp.config import AppConfig
from dashboard_webapp.population import (
    InvalidPopulationSpec,
    PopgenStore,
    PopulationArtifact,
    PopulationNotFound,
    PopulationRequest,
)
from tests.conftest import FakeAgentSource, FakeRunSource

WORLD = "w1"


def _artifact(request: PopulationRequest) -> PopulationArtifact:
    return PopulationArtifact(
        population_id="pop-deadbeef0001",
        world=request.world,
        counts={"personas": 5, "friend_groups": 2, "solo_agents": 1},
        paths={"fixture": "/tmp/w1/population/pop-deadbeef0001/fixture.sql"},
        fixture_sql="USE `ragnarok`;\n",
    )


def _worlds_root(tmp_path: Path) -> Path:
    root = tmp_path / "worlds"
    (root / WORLD).mkdir(parents=True)
    return root


def _client(store: object | None = None) -> TestClient:
    return TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            population=store,  # type: ignore[arg-type]
            config=AppConfig(),
        )
    )


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "world": WORLD,
        "friend_groups": 2,
        "friends_per_group": [2, 3],
        "solo_agents": 1,
        "seed": 7,
    }
    body.update(overrides)
    return body


# --------------------------------------------------------- endpoint contract


class FakeStore:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requests: list[PopulationRequest] = []

    def generate(self, request: PopulationRequest) -> PopulationArtifact:
        self.requests.append(request)
        if isinstance(self.error, Exception):
            raise self.error
        return _artifact(request)


def test_post_population_returns_201_with_counts_paths_and_fixture() -> None:
    store = FakeStore()

    res = _client(store).post("/api/population", json=_payload())

    assert res.status_code == 201
    body = res.json()
    assert body["population_id"] == "pop-deadbeef0001"
    assert body["counts"] == {"personas": 5, "friend_groups": 2, "solo_agents": 1}
    assert body["fixture_sql"].startswith("USE `ragnarok`;")
    assert store.requests[0].friend_groups == 2
    assert store.requests[0].friends_per_group == (2, 3)


def test_post_population_invalid_spec_is_422() -> None:
    """A spec the request model accepts but the generator rejects."""
    store = FakeStore(error=InvalidPopulationSpec("no free weekly slot run"))

    res = _client(store).post("/api/population", json=_payload())

    assert res.status_code == 422
    assert "no free weekly slot run" in res.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        _payload(friend_groups=-1),
        _payload(friends_per_group=[5, 2]),
        _payload(friends_per_group=[1, 4]),
        _payload(friends_per_group=[2, 13]),
        _payload(friend_groups=0, solo_agents=0),
        _payload(seed=-3),
        _payload(world="../escape"),
        _payload(world="a/b"),
        _payload(world=""),
    ],
)
def test_post_population_request_validation_is_422(payload: dict[str, object]) -> None:
    res = _client(FakeStore()).post("/api/population", json=payload)

    assert res.status_code == 422


def test_post_population_empty_population_message_is_included() -> None:
    res = _client(FakeStore()).post(
        "/api/population", json=_payload(friend_groups=0, solo_agents=0)
    )

    assert res.status_code == 422
    assert "empty population" in str(res.json()["detail"])


def test_post_population_without_store_is_503() -> None:
    res = _client(None).post("/api/population", json=_payload())

    assert res.status_code == 503
    assert "population" in res.json()["detail"]


# ------------------------------------------------------------------- applier


class FakeApplier:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def apply(self, world: str, population_id: str) -> dict[str, object]:
        self.calls.append((world, population_id))
        if isinstance(self.error, Exception):
            raise self.error
        return {"accounts": 3, "characters": 3, "statements": 9}


def test_post_apply_returns_applier_result() -> None:
    applier = FakeApplier()

    res = TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            population=FakeStore(),
            applier=applier,
            config=AppConfig(),
        )
    ).post("/api/population/pop-deadbeef0001/apply", json={"world": WORLD})

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "applied"
    assert body["accounts"] == 3
    assert applier.calls == [(WORLD, "pop-deadbeef0001")]


def test_post_apply_population_not_found_is_404() -> None:
    res = TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            population=FakeStore(),
            applier=FakeApplier(error=PopulationNotFound("unknown population")),
            config=AppConfig(),
        )
    ).post("/api/population/pop-missing0001/apply", json={"world": WORLD})

    assert res.status_code == 404
    assert "unknown population" in res.json()["detail"]


def test_post_apply_refused_sql_is_403() -> None:
    from dashboard_webapp.db_applier import SqlNotAllowed

    res = TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            population=FakeStore(),
            applier=FakeApplier(error=SqlNotAllowed("non-allowlisted statement refused: drop")),
            config=AppConfig(),
        )
    ).post("/api/population/pop-x/apply", json={"world": WORLD})

    assert res.status_code == 403
    assert "non-allowlisted" in res.json()["detail"]


def test_post_apply_without_applier_is_503() -> None:
    res = TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            population=FakeStore(),
            applier=None,
            config=AppConfig(),
        )
    ).post("/api/population/pop-x/apply", json={"world": WORLD})

    assert res.status_code == 503
    assert "applier" in res.json()["detail"]


# -------------------------------------------- PopgenStore (real robots.popgen)


def test_store_generates_and_writes_world_artifacts(tmp_path: Path, repo_src: Path) -> None:
    store = PopgenStore(_worlds_root(tmp_path))

    artifact = store.generate(
        PopulationRequest(
            world=WORLD, friend_groups=1, friends_per_group=(2, 2), solo_agents=1, seed=11
        )
    )

    assert artifact.population_id.startswith("pop-")
    assert artifact.counts["friend_groups"] == 1
    assert artifact.counts["solo_agents"] == 1
    assert artifact.counts["personas"] == 3
    manifest = json.loads(Path(artifact.paths["manifest"]).read_text(encoding="utf-8"))
    assert len(manifest["accounts"]) == 3
    summary = json.loads(Path(artifact.paths["population"]).read_text(encoding="utf-8"))
    assert summary["schema"] == 1
    assert summary["counts"] == artifact.counts
    fixture_text = Path(artifact.paths["fixture"]).read_text(encoding="utf-8")
    assert fixture_text == artifact.fixture_sql
    assert "INSERT INTO `login`" in artifact.fixture_sql
    assert "INSERT INTO `char`" in artifact.fixture_sql
    assert "INSERT INTO `skill`" in artifact.fixture_sql


def test_store_is_deterministic_for_same_seed(tmp_path: Path, repo_src: Path) -> None:
    store = PopgenStore(_worlds_root(tmp_path))
    request = PopulationRequest(
        world=WORLD, friend_groups=2, friends_per_group=(2, 3), solo_agents=0, seed=42
    )

    first = store.generate(request)
    second = store.generate(request)

    assert first.fixture_sql == second.fixture_sql
    assert first.population_id != second.population_id  # distinct output dirs


def test_store_unknown_world_is_population_not_found(tmp_path: Path, repo_src: Path) -> None:
    store = PopgenStore(_worlds_root(tmp_path))

    with pytest.raises(PopulationNotFound):
        store.generate(
            PopulationRequest(
                world="nope", friend_groups=1, friends_per_group=(2, 2), solo_agents=0, seed=1
            )
        )


def test_store_endpoint_round_trip_against_real_generator(tmp_path: Path, repo_src: Path) -> None:
    client = TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=None,
            commands=JsonlCommandQueue(tmp_path / "commands"),
            goals=None,
            memory=None,
            population=PopgenStore(_worlds_root(tmp_path)),
            applier=None,
            config=AppConfig(),
        )
    )

    res = client.post("/api/population", json=_payload(seed=5))

    assert res.status_code == 201
    body = res.json()
    assert Path(body["paths"]["fixture"]).is_file()
    # the fixture application stays an explicit operator step: no applier wired
    apply_res = client.post(f"/api/population/{body['population_id']}/apply", json={"world": WORLD})
    assert apply_res.status_code == 503
