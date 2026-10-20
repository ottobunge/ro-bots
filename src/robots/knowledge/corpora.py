"""Read-only access to the git-ignored iRO knowledge corpora.

Corpora (built and refreshed by ``run/knowledge/iro-db/build_iro_db.py`` and
``run/knowledge/iro-wiki/ingest_iro_wiki.py``):

- ``run/knowledge/iro-db/iro-db.db``: ``entities(section, id, name, ...,
  fields_json)`` with parsed monster/item stat fields, plus an FTS5 mirror.
- ``run/knowledge/iro-wiki/iro-wiki.db``: ``fts_pages(section, title, body)``.

Every reader is graceful: an absent corpus (fresh clone, CI) yields ``None``
or ``[]`` instead of raising. Connections open read-only; nothing here writes.
Paths default to the repo-relative locations and can be overridden with the
``RO_BOTS_IRO_DB`` / ``RO_BOTS_IRO_WIKI`` environment variables (tests use
this to mount fake corpora).
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from robots.knowledge.calculators import equip_projection, leading_int

DEFAULT_IRO_DB = Path("run/knowledge/iro-db/iro-db.db")
DEFAULT_IRO_WIKI = Path("run/knowledge/iro-wiki/iro-wiki.db")
MAX_LINE_CHARS = 160


def iro_db_path() -> Path:
    """Effective iro-db corpus location."""
    override = os.environ.get("RO_BOTS_IRO_DB")
    return Path(override) if override else DEFAULT_IRO_DB


def iro_wiki_path() -> Path:
    """Effective iro-wiki corpus location."""
    override = os.environ.get("RO_BOTS_IRO_WIKI")
    return Path(override) if override else DEFAULT_IRO_WIKI


def _connect_readonly(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


def item_fields(item_id: int) -> dict[str, Any] | None:
    """Parsed fields for one iro-db item row (items section only)."""
    con = _connect_readonly(iro_db_path())
    if con is None:
        return None
    try:
        row = con.execute(
            "SELECT name, fields_json FROM entities WHERE section = 'items' AND id = ?",
            (item_id,),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if row is None:
        return None
    fields: dict[str, Any] = json.loads(row[1])
    fields.setdefault("name", row[0])
    fields.setdefault("id", item_id)
    return fields


def monster_fields(monster: str | int) -> dict[str, Any] | None:
    """Parsed fields for one iro-db monster row, by name (or monster id)."""
    con = _connect_readonly(iro_db_path())
    if con is None:
        return None
    try:
        if isinstance(monster, int):
            row = con.execute(
                "SELECT name, fields_json FROM entities WHERE section = 'monsters' AND id = ?",
                (monster,),
            ).fetchone()
        else:
            row = con.execute(
                "SELECT name, fields_json FROM entities WHERE section = 'monsters' AND name = ?",
                (monster,),
            ).fetchone()
            if row is None:
                row = con.execute(
                    "SELECT name, fields_json FROM entities "
                    "WHERE section = 'monsters' AND name LIKE ? ORDER BY id LIMIT 1",
                    (f"{monster}%",),
                ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if row is None:
        return None
    fields: dict[str, Any] = json.loads(row[1])
    fields.setdefault("name", row[0])
    return fields


def item_weapon_attack(fields: dict[str, Any]) -> int | None:
    """The parsed weapon attack from an iro-db item row (``atk``/``attack``)."""
    for key in ("atk", "attack", "Attack", "ATK"):
        if key in fields:
            value = leading_int(fields[key])
            if value is not None:
                return value
    return None


def _pct_value(drop: dict[str, Any]) -> float:
    raw = str(drop.get("rate", "0"))
    text = ""
    for char in raw:
        if char.isdigit() or char == ".":
            text += char
        elif text:
            break
    return float(text) if text else 0.0


def monster_context_line(fields: dict[str, Any]) -> str:
    """One bounded knowledge line for a monster, e.g.

    ``"Poring: HP 60, exp 27/20, drops Jellopy 70%, Apple 10%, Sticky Mucus 4%…"``.
    """
    name = str(fields.get("name", "?"))
    hp = leading_int(fields.get("hp"))
    base_exp = leading_int(fields.get("base_exp"))
    job_exp = leading_int(fields.get("job_exp"))
    parts: list[str] = []
    if hp is not None:
        parts.append(f"HP {hp}")
    if base_exp is not None and job_exp is not None:
        parts.append(f"exp {base_exp}/{job_exp}")
    drops = sorted(
        (drop for drop in fields.get("drops", []) if isinstance(drop, dict)),
        key=_pct_value,
        reverse=True,
    )[:3]
    if drops:
        rendered = ", ".join(f"{drop.get('name', '?')} {_pct_value(drop):g}%" for drop in drops)
        parts.append(f"drops {rendered}…")
    return (f"{name}: " + ", ".join(parts))[:MAX_LINE_CHARS]


def item_projection_line(item_id: int, stats: dict[str, int] | None = None) -> str | None:
    """The criterion-4 decide line for one inventory item id, or None."""
    fields = item_fields(item_id)
    if fields is None:
        return None
    projection = equip_projection(fields, stats=stats)
    return str(projection["line"])[:MAX_LINE_CHARS]


def wiki_snippets(query: str, *, section: str | None = None, limit: int = 2) -> list[str]:
    """Bounded FTS snippets from the iro-wiki corpus (absent corpus -> [])."""
    con = _connect_readonly(iro_wiki_path())
    if con is None:
        return []
    sql = "SELECT snippet(fts_pages, 2, '', '', ' … ', 10) FROM fts_pages WHERE fts_pages MATCH ?"
    params: list[Any] = [f'"{query}"']
    if section:
        sql += " AND section = ?"
        params.append(section)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    try:
        rows = con.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()
    return [str(row[0]).strip()[:MAX_LINE_CHARS] for row in rows if row and row[0]]
