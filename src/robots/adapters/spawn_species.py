"""Known map species from the pinned rAthena spawn declarations.

Criterion-10 knowledge: a bot should know what LIVES on its map before it
sees one — plan authoring must not depend on having already observed a
mob (the circular dependency that left agents standing in mobless login
patches, w59). Source: rathena npc/pre-re/mobs/fields/<map>.txt lines

    <map>,<x>,<y>\tmonster\t<Name>\t<id>,<count>

Authority note: this is spawn DECLARATION knowledge, not a live census.
"""

from pathlib import Path


def spawn_species(path: Path, map_name: str) -> tuple[str, ...]:
    """Declared monster species names for one map, deduplicated in file order."""
    species: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 3 or fields[1] != "monster":
            continue
        if fields[0].split(",")[0] != map_name:
            continue
        name = fields[2].strip()
        if name and name not in species:
            species.append(name)
    return tuple(species)


def spawn_species_index(directory: Path) -> dict[str, tuple[str, ...]]:
    """Scan every spawn declaration file once; group species by map.

    File names are town-oriented (prt_fild08 lives in prontera.txt), so the
    map -> file assumption is invalid; the index is the honest shape.
    """
    index: dict[str, list[str]] = {}
    directory = Path(directory)
    if not directory.is_dir():
        return {}
    for path in sorted(directory.glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) < 3 or fields[1] != "monster":
                continue
            map_name = fields[0].split(",")[0]
            name = fields[2].strip()
            bucket = index.setdefault(map_name, [])
            if name and name not in bucket:
                bucket.append(name)
    return {map_name: tuple(names) for map_name, names in index.items()}


def spawn_cluster_index(directory: Path) -> dict[str, tuple[tuple[int, int], ...]]:
    """Fixed declared regions only: (0,0) means random across the map."""
    index: dict[str, list[tuple[int, int]]] = {}
    for path in sorted(Path(directory).glob("*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            cluster = _declared_cluster(line)
            if cluster is None:
                continue
            map_name, cell = cluster
            bucket = index.setdefault(map_name, [])
            if cell not in bucket:
                bucket.append(cell)
    return {map_name: tuple(cells) for map_name, cells in index.items()}


def _declared_cluster(line: str) -> tuple[str, tuple[int, int]] | None:
    fields = line.split("\t")
    if len(fields) < 3 or fields[1] != "monster":
        return None
    location = fields[0].split(",")
    if len(location) < 3:
        return None
    try:
        x, y = int(location[1]), int(location[2])
    except ValueError:
        return None
    return (location[0], (x, y)) if x > 0 and y > 0 else None
