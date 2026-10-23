"""Bounded query lines over the local iRO corpora and rathena declarations.

The query surface the decide context and the seed renderer draw from:

- ``mobs_dropping(item)``: who drops an item, best rate first,
- ``mob_drops(mob)``: one mob's drop table,
- ``mob_spawns(mob)``: declared spawn maps (+ counts) from the pinned
  rathena ``npc/pre-re/mobs`` declarations (the same ground truth the
  spawn-species adapter indexes),
- ``route_hint(map)``: one prontera-centered navigation line from the
  rathena warp declarations,
- ``quest_lines(term)``: bounded wiki quest/guide lines from the iro-wiki FTS.

Every function returns a bounded tuple of short lines (each capped at
``corpora.MAX_LINE_CHARS``); unknown inputs resolve to ``()`` — never an
error — and absent corpora/tree degrade the same way. All access is
read-only and local (sqlite FTS/parse + declaration text); nothing here
touches the network. Names resolve case-insensitively by exact match then
prefix, mirroring ``corpora.monster_fields``.
"""

import json
import os
import re
import sqlite3
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from robots.knowledge import corpora
from robots.knowledge.calculators import leading_int

DEFAULT_RATHENA = Path("rathena")
MAX_ROWS = 8
DEFAULT_ROWS = 8
DEFAULT_MENTION_LINES = 3
MAX_MENTION_LINES = 4
MAX_LINE_CHARS = corpora.MAX_LINE_CHARS


def rathena_path() -> Path:
    """Effective rathena tree location (spawn/warp declaration ground truth)."""
    override = os.environ.get("RO_BOTS_RATHENA")
    return Path(override) if override else DEFAULT_RATHENA


def _loads_object(raw: Any) -> dict[str, Any] | None:
    try:
        payload = json.loads(raw)
    except TypeError, ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _int_or_none(raw: Any) -> int | None:
    try:
        return int(raw)
    except TypeError, ValueError:
        return None


def _effective_rows(limit: int, maximum: int = MAX_ROWS) -> int:
    return max(0, min(limit, maximum))


def _drop_dicts(fields: dict[str, Any]) -> list[dict[str, Any]]:
    drops = fields.get("drops")
    if not isinstance(drops, list):
        return []
    return [drop for drop in drops if isinstance(drop, dict)]


def _entity_fields(section: str, subject: str | int) -> tuple[int, str, dict[str, Any]] | None:
    """(id, name, parsed fields) for one entity row, or None (mirrors corpora)."""
    if isinstance(subject, str) and not subject.strip():
        return None
    con = corpora._connect_readonly(corpora.iro_db_path())
    if con is None:
        return None
    row: Any = None
    try:
        row = _select_entity_row(con, section, subject)
    except sqlite3.Error:
        row = None
    finally:
        con.close()
    if row is None:
        return None
    fields = _loads_object(row[2])
    if fields is None:
        return None
    return int(row[0]), str(row[1]), fields


def _select_entity_row(con: sqlite3.Connection, section: str, subject: str | int) -> Any:
    """Exact id/name hit first, then a name-prefix hit (corpora's order)."""
    if isinstance(subject, int):
        return con.execute(
            "SELECT id, name, fields_json FROM entities WHERE section = ? AND id = ?",
            (section, subject),
        ).fetchone()
    exact = con.execute(
        "SELECT id, name, fields_json FROM entities WHERE section = ? AND name = ?",
        (section, subject),
    ).fetchone()
    if exact is not None:
        return exact
    return con.execute(
        "SELECT id, name, fields_json FROM entities "
        "WHERE section = ? AND name LIKE ? ORDER BY id LIMIT 1",
        (section, f"{subject}%"),
    ).fetchone()


@lru_cache(maxsize=4)
def _dropper_index(path_text: str) -> dict[int, tuple[tuple[str, int, float], ...]]:
    """item id -> ((mob name, mob id, rate), ...) best rate first (per corpus)."""
    con = corpora._connect_readonly(Path(path_text))
    if con is None:
        return {}
    try:
        rows = con.execute(
            "SELECT id, name, fields_json FROM entities WHERE section = 'monsters'"
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    buckets: dict[int, list[tuple[str, int, float]]] = {}
    for mob_id, mob_name, fields_json in rows:
        fields = _loads_object(fields_json)
        if fields is None:
            continue
        for drop in _drop_dicts(fields):
            item_id = _int_or_none(drop.get("id"))
            if item_id is None:
                continue
            name = str(mob_name)
            entry = (name, int(mob_id), corpora._pct_value(drop))
            buckets.setdefault(item_id, []).append(entry)
    return {
        item_id: tuple(sorted(mobs, key=lambda entry: (-entry[2], entry[0], entry[1])))
        for item_id, mobs in buckets.items()
    }


def mobs_dropping(item: str | int, *, limit: int = DEFAULT_ROWS) -> tuple[str, ...]:
    """Droppers of one item, best rate first; one self-contained line per mob."""
    resolved = _entity_fields("items", item)
    if resolved is None:
        return ()
    item_id, item_name, _fields = resolved
    droppers = _dropper_index(str(corpora.iro_db_path())).get(item_id, ())
    return tuple(
        f"{item_name} ({item_id}) <- {name} ({mob_id}): {rate:g}%"
        for name, mob_id, rate in droppers[: _effective_rows(limit)]
    )


def mob_drops(mob: str | int, *, limit: int = DEFAULT_ROWS) -> tuple[str, ...]:
    """One mob's drop table: a header line, then one line per drop, best first."""
    resolved = _entity_fields("monsters", mob)
    if resolved is None:
        return ()
    mob_id, mob_name, fields = resolved
    drops = sorted(_drop_dicts(fields), key=corpora._pct_value, reverse=True)
    header = f"{mob_name} ({mob_id})"
    hp = leading_int(fields.get("hp"))
    if hp is not None:
        header = f"{header} HP {hp}"
    lines = [f"{header} drops:"]
    lines.extend(
        f"{drop.get('name', '?')} ({drop.get('id', '?')}): {corpora._pct_value(drop):g}%"
        for drop in drops
    )
    return tuple(line[:MAX_LINE_CHARS] for line in lines[: _effective_rows(limit)])


@lru_cache(maxsize=4)
def _spawn_index(root_text: str) -> tuple[
    dict[str, tuple[tuple[str, int], ...]],
    dict[int, tuple[tuple[str, int], ...]],
]:
    """Declared spawn maps per mob (by lowercase name and by id), counts summed.

    File names are town-oriented (prt_fild08's spawns live in prontera.txt),
    so the whole declaration tree is scanned once and indexed by the map each
    line declares — the honest shape per the spawn-species adapter.
    """
    by_name: dict[str, dict[str, int]] = {}
    by_id: dict[int, dict[str, int]] = {}
    root = Path(root_text)
    if not root.is_dir():
        return ({}, {})
    for path in sorted(root.rglob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            _absorb_spawn_line(line, by_name, by_id)
    return (
        {key: tuple(sorted(maps.items())) for key, maps in by_name.items()},
        {key: tuple(sorted(maps.items())) for key, maps in by_id.items()},
    )


def _absorb_spawn_line(
    line: str,
    by_name: dict[str, dict[str, int]],
    by_id: dict[int, dict[str, int]],
) -> None:
    """Fold one declaration line into the per-name/per-id spawn buckets."""
    parts = _spawn_parts(line)
    if parts is None:
        return
    map_name, declared_name, mob_id, count = parts
    if declared_name:
        _bump(by_name.setdefault(declared_name.lower(), {}), map_name, count)
    if mob_id is not None:
        _bump(by_id.setdefault(mob_id, {}), map_name, count)


def _spawn_parts(line: str) -> tuple[str, str, int | None, int] | None:
    """(map, declared name, mob id, count) for one valid declaration line."""
    fields = line.split("\t")
    if len(fields) < 4 or fields[1] != "monster" or line.startswith("//"):
        return None
    id_count = fields[3].split(",")
    count = _int_or_none(id_count[1]) if len(id_count) > 1 else None
    if count is None:
        count = 1
    map_name = fields[0].split(",")[0]
    if not map_name or count <= 0:
        return None
    mob_id = _int_or_none(id_count[0]) if id_count else None
    return (map_name, fields[2].strip(), mob_id, count)


def _bump(maps: dict[str, int], map_name: str, count: int) -> None:
    maps[map_name] = maps.get(map_name, 0) + count


def mob_spawns(mob: str | int, *, limit: int = DEFAULT_ROWS) -> tuple[str, ...]:
    """Declared spawn maps (+counts) for one mob, densest first; () without data."""
    resolved = _entity_fields("monsters", mob)
    if resolved is None:
        return ()
    mob_id, mob_name, _fields = resolved
    by_name, by_id = _spawn_index(str(rathena_path()))
    entries = by_id.get(mob_id) or by_name.get(mob_name.lower()) or ()
    ranked = sorted(entries, key=lambda entry: (-entry[1], entry[0]))
    return tuple(
        f"{mob_name} ({mob_id}) on {map_name}: {count}"
        for map_name, count in ranked[: _effective_rows(limit)]
    )


def route_hint(map_name: str, *, origin: str = "prontera") -> tuple[str, ...]:
    """One prontera-centered navigation line for a map, or () when unknown."""
    target = map_name.strip()
    if not target:
        return ()
    edges = _warp_edges(str(rathena_path()))
    if not edges:
        return ()
    if target == origin:
        return _hub_hint(edges, origin)
    direct = [edge for edge in edges if edge[0] == origin and edge[4] == target]
    if direct:
        return (_render_edge(direct[0]),)
    return _two_hop_hint(edges, origin, target)


def _render_edge(edge: tuple[str, int, int, str, str, int, int]) -> str:
    return f"{edge[0]},{edge[1]},{edge[2]} warp {edge[3]} -> {edge[4]},{edge[5]},{edge[6]}"


def _hub_hint(
    edges: tuple[tuple[str, int, int, str, str, int, int], ...], origin: str
) -> tuple[str, ...]:
    exits = [edge for edge in edges if edge[0] == origin][:3]
    if not exits:
        return ()
    rendered = ", ".join(f"{edge[3]} -> {edge[4]} ({edge[1]},{edge[2]})" for edge in exits)
    return (f"{origin} hub exits: {rendered}"[:MAX_LINE_CHARS],)


def _two_hop_hint(
    edges: tuple[tuple[str, int, int, str, str, int, int], ...], origin: str, target: str
) -> tuple[str, ...]:
    for first in (edge for edge in edges if edge[0] == origin):
        hops = [edge for edge in edges if edge[0] == first[4] and edge[4] == target]
        if not hops:
            continue
        second = hops[0]
        line = (
            f"via {first[4]}: {_render_edge(first)}; then {second[3]} "
            f"-> {second[4]},{second[5]},{second[6]}"
        )
        return (line[:MAX_LINE_CHARS],)
    return ()


@lru_cache(maxsize=4)
def _warp_edges(root_text: str) -> tuple[tuple[str, int, int, str, str, int, int], ...]:
    """Warp declarations (from map, x, y, name, to map, to x, to y), sorted."""
    root = Path(root_text)
    if not root.is_dir():
        return ()
    edges: list[tuple[str, int, int, str, str, int, int]] = []
    for path in sorted(root.rglob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            edge = _parse_warp_line(line)
            if edge is not None:
                edges.append(edge)
    # (from map, warp name, to map, ...) so equal-origin picks order by name.
    return tuple(sorted(edges, key=lambda e: (e[0], e[3], e[4], e[1], e[2])))


def _parse_warp_line(line: str) -> tuple[str, int, int, str, str, int, int] | None:
    line = line.strip()
    fields = line.split("\t")
    if len(fields) < 4 or fields[1] != "warp" or line.startswith("//"):
        return None
    origin = fields[0].split(",")
    target = fields[3].split(",")  # xs,ys,tomap,tx,ty
    if len(origin) < 3 or len(target) < 5:
        return None
    x, y = _int_or_none(origin[1]), _int_or_none(origin[2])
    to_x, to_y = _int_or_none(target[3]), _int_or_none(target[4])
    if x is None or y is None or to_x is None or to_y is None:
        return None
    return (
        origin[0],
        int(x),
        int(y),
        fields[2].strip(),
        target[2],
        int(to_x),
        int(to_y),
    )


def quest_lines(search_term: str, *, limit: int = 4) -> tuple[str, ...]:
    """Bounded wiki quest/guide lines ('<Title>: <snippet>') for one term."""
    term = search_term.strip()
    if not term:
        return ()
    con = corpora._connect_readonly(corpora.iro_wiki_path())
    if con is None:
        return ()
    sql = (
        "SELECT title, snippet(fts_pages, 2, '', '', ' … ', 10) FROM fts_pages "
        "WHERE fts_pages MATCH ? AND section = 'all_pages' ORDER BY rank LIMIT ?"
    )
    try:
        rows = con.execute(sql, (f'"{term}"', _effective_rows(limit))).fetchall()
    except sqlite3.Error:
        return ()
    finally:
        con.close()
    return tuple(f"{title}: {str(body).strip()}"[:MAX_LINE_CHARS] for title, body in rows if body)


@lru_cache(maxsize=4)
def _mention_universe(path_text: str) -> tuple[tuple[re.Pattern[str], str, str], ...]:
    """(word-boundary pattern, canonical name, section) per distinct name.

    Items win name collisions (the Emperium ITEM, not the WoE statue mob, is
    what an objective mentioning 'Emperium' needs) — the query orders items
    first and the first occurrence claims the name key.
    """
    con = corpora._connect_readonly(Path(path_text))
    if con is None:
        return ()
    try:
        rows = con.execute(
            "SELECT section, name FROM entities "
            "WHERE name IS NOT NULL ORDER BY section ASC, name"
        ).fetchall()
    except sqlite3.Error:
        return ()
    finally:
        con.close()
    universe: list[tuple[re.Pattern[str], str, str]] = []
    seen: set[str] = set()
    for section, name in rows:
        text = str(name).strip()
        core = text.split("[")[0].strip()
        key = core.lower()
        if len(key) < 3 or key in seen:
            continue
        seen.add(key)
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(key)}s?(?![A-Za-z0-9])")
        universe.append((pattern, text, str(section)))
    # Longest names first so 'Solid Mineral' wins a shared spot deterministically.
    universe.sort(key=lambda entry: (-len(entry[1]), entry[1]))
    return tuple(universe)


def mention_lines(
    texts: Iterable[str], *, max_lines: int = DEFAULT_MENTION_LINES
) -> tuple[str, ...]:
    """Query lines for the items/mobs literally named in the given texts.

    The decide-context seam: when goal/want/chat text names a corpus entity
    (e.g. the Emperium for a guild objective), 2-4 bounded query lines ride
    along. Position in the text orders the lines; unknown names are skipped.
    """
    universe = _mention_universe(str(corpora.iro_db_path()))
    joined = "\n".join(str(text) for text in texts).lower()
    if not universe or not joined.strip():
        return ()
    bound = max(0, min(max_lines, MAX_MENTION_LINES))
    lines: list[str] = []
    for _position, name, kind in _find_mentions(joined, universe):
        line = _mention_query_line(name, kind)
        if line is None:
            continue
        lines.append(line)
        if len(lines) >= bound:
            break
    return tuple(lines)


def _find_mentions(
    joined: str, universe: tuple[tuple[re.Pattern[str], str, str], ...]
) -> list[tuple[int, str, str]]:
    """Distinct (position, name, kind) mentions, ordered by position."""
    found: dict[str, tuple[int, str, str]] = {}
    for pattern, name, kind in universe:
        match = pattern.search(joined)
        if match is None:
            continue
        prior = found.get(name)
        if prior is None or match.start() < prior[0]:
            found[name] = (match.start(), name, kind)
    return sorted(found.values(), key=lambda entry: entry[0])


def _mention_query_line(name: str, kind: str) -> str | None:
    """The single most useful query line for one mentioned entity."""
    if kind == "monsters":
        fields = corpora.monster_fields(name)
        if fields is None:
            return None
        return corpora.monster_context_line(fields)
    resolved = _entity_fields("items", name)
    if resolved is None:
        return None
    item_id, item_name, fields = resolved
    droppers = _dropper_index(str(corpora.iro_db_path())).get(item_id, ())
    if droppers:
        drop_name, drop_id, rate = droppers[0]
        return f"{item_name} ({item_id}) <- {drop_name} ({drop_id}): {rate:g}%"
    parts = [str(fields.get("type", "?"))]
    weight = leading_int(fields.get("weight"))
    if weight is not None:
        parts.append(f"weight {weight}")
    return f"{item_name} ({item_id}): {', '.join(parts)}"[:MAX_LINE_CHARS]
