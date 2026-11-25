"""Seed/respawn positions use the runtime's pinned GAT authority (leg 130)."""

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from robots import popgen, popgen_walkability
from robots.adapters.native_navigation import MapCache, WalkMap, nearest_walkable
from robots.popgen_walkability import INDEX_PATH, build_seed_index, seed_cache, seed_point

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def server_maps():
    return MapCache.load(
        REPO / "rathena/db/map_cache.dat", REPO / "rathena/db/pre-re/map_cache.dat"
    )


@pytest.mark.parametrize("seed", [3, 105, *range(20)])
def test_all_generated_saves_and_roster_last_positions_are_walkable(seed, server_maps):
    population = popgen.generate_population(popgen.PopulationSpec(2, (2, 4), 2, seed))
    population, _ = popgen.extend_roster(population, population.personas[0].persona_id)
    for persona in population.personas:
        assert server_maps.get(persona.save_map).walkable(persona.save_point), persona.persona_id
    positions = re.findall(
        r"11, 11, '([^']+)', (\d+), (\d+), '([^']+)', (\d+), (\d+),",
        population.fixture_sql,
    )
    assert len(positions) == sum(len(p.characters) for p in population.personas)
    for last_map, lx, ly, save_map, sx, sy in positions:
        assert server_maps.get(last_map).walkable((int(lx), int(ly)))
        assert server_maps.get(save_map).walkable((int(sx), int(sy)))


def test_known_pockets_use_bounded_nearest_and_name_the_relocation(server_maps, caplog):
    grid = server_maps.get("pay_fild04")
    for point in ((163, 177), (204, 165)):
        assert not grid.walkable(point)
        result = seed_point("pay_fild04", point, owner="pop_0069_s01", role="save")
        assert result == nearest_walkable(grid, point, radius=32)
        assert grid.walkable(result)
    assert "popgen_seed_relocated" in caplog.text
    assert "pop_0069_s01" in caplog.text
    assert "role=save" in caplog.text


def test_index_is_exactly_regenerable_from_common_then_pre_re(server_maps):
    names = ("prontera", *(name for name, _, _ in popgen.FIELD_SAVES))
    assert INDEX_PATH.read_bytes() == build_seed_index(REPO / "rathena", names)
    assert set(seed_cache().maps) == set(names)
    for name in names:
        assert seed_cache().get(name) == server_maps.get(name)


@pytest.mark.parametrize(
    ("map_name", "point"), [("missing", (150, 150)), ("prontera", (-100, -100))]
)
def test_seed_fails_closed_without_a_walkable_cell_in_bound(map_name, point):
    with pytest.raises(ValueError, match="walkable seed"):
        seed_point(map_name, point, owner="bot", role="last")


def test_validate_reports_all_bad_saves_without_rewriting_or_regenerating(tmp_path, capsys):
    population = popgen.generate_population(popgen.PopulationSpec(0, (2, 2), 2, 105))
    personas = tuple(
        replace(p, save_map="pay_fild04", save_point=point)
        for p, point in zip(population.personas, ((163, 177), (204, 165)), strict=True)
    )
    population = replace(population, personas=personas)
    path = tmp_path / "population.json"
    original = json.dumps(population.summary())
    path.write_text(original)
    assert popgen.main(["--validate-save-points", str(path)]) == 1
    output = capsys.readouterr().out
    for persona in personas:
        assert persona.persona_id in output
        assert persona.name in output
    assert "163,177" in output
    assert "204,165" in output
    assert path.read_text() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["population.json"]


def test_validate_green_and_unknown_map(tmp_path, capsys):
    population = popgen.generate_population(popgen.PopulationSpec(1, (2, 2), 0, 7))
    path = tmp_path / "population.json"
    path.write_text(json.dumps(population.summary()))
    assert popgen.main(["--validate-save-points", str(path)]) == 0
    assert "2 save points checked; 0 unwalkable" in capsys.readouterr().out
    bad = replace(population.personas[0], save_map="missing")
    path.write_text(json.dumps(replace(population, personas=(bad,)).summary()))
    assert popgen.main(["--validate-save-points", str(path)]) == 1
    assert "unknown map" in capsys.readouterr().out


def test_seeded_last_position_is_repaired_even_for_extra_roster_slots(monkeypatch, caplog):
    population = popgen.generate_population(popgen.PopulationSpec(1, (2, 2), 0, 7))
    real = popgen_walkability.seed_cache()
    grid = real.get("prontera")
    tiles = bytearray(grid.tiles)
    for x in range(150, 159, 2):
        tiles[x + 150 * grid.width] = 1
    maps = MapCache(
        [
            *(g for name, g in real.maps.items() if name != "prontera"),
            WalkMap("prontera", grid.width, grid.height, bytes(tiles)),
        ]
    )
    monkeypatch.setattr(popgen_walkability, "seed_cache", lambda: maps)
    extended, _ = popgen.extend_roster(population, population.personas[0].persona_id)
    last_cells = re.findall(r"11, 11, 'prontera', (\d+), (\d+),", extended.fixture_sql)
    assert len(last_cells) == 3
    assert all(maps.get("prontera").walkable((int(x), int(y))) for x, y in last_cells)
    assert "role=last" in caplog.text


def test_index_build_cli_uses_the_pinned_source(tmp_path, monkeypatch):
    output = tmp_path / "index.dat"
    monkeypatch.setattr(popgen, "INDEX_PATH", output)
    assert popgen.main(["--build-walkability-index", str(REPO / "rathena")]) == 0
    assert output.read_bytes() == INDEX_PATH.read_bytes()


@pytest.mark.parametrize("contents", [None, b"broken index"])
def test_missing_or_corrupt_index_fails_closed(tmp_path, monkeypatch, contents):
    path = tmp_path / "index.dat"
    if contents is not None:
        path.write_bytes(contents)
    monkeypatch.setattr(popgen_walkability, "INDEX_PATH", path)
    popgen_walkability.seed_cache.cache_clear()
    try:
        with pytest.raises((OSError, ValueError)):
            popgen_walkability.seed_point("prontera", (150, 150), owner="bot", role="last")
    finally:
        popgen_walkability.seed_cache.cache_clear()
