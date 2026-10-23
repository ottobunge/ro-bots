"""Bounded query surface over the local iRO corpora + rathena declarations.

Query functions (mobs_dropping / mob_drops / mob_spawns / route_hint /
quest_lines), the decide-context mention wiring, and the seed-knowledge
renderer. The fake fixtures below are SMALL transcribed snapshots of the
real rows/declarations (fixture literals, never the corpora themselves);
real-corpus and real-rathena smoke tests skip cleanly when the data is
absent, so CI without the data stays green.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from robots.domain.model import ChatLine
from robots.knowledge import game_context, queries
from tests.conftest import make_state

# --- SMALL fixture snapshots (transcribed from the live corpora, 2026-10-23) ---

EMPERIUM_FIELDS: dict[str, Any] = {
    "type": "Misc",
    "subtype": "General",
    "weight": "100",
    "buying_price": "--",
    "selling_price": "1 Z (1 Z)",
    "dropped_by": [],  # the item page lists no droppers; the mob tables do
}
JELLOPY_FIELDS: dict[str, Any] = {
    "type": "Etc",
    "weight": "1",
    "selling_price": "3 Z (2 Z)",
}
RED_POTION_FIELDS: dict[str, Any] = {
    "type": "Healing",
    "weight": "7",
    "buying_price": "50 Z",
    "selling_price": "10 Z (10 Z)",
}
PORING_FIELDS: dict[str, Any] = {
    "level": "1",
    "hp": "60",
    "base_exp": "27",
    "job_exp": "20",
    "drops": [
        {"id": 909, "name": "Jellopy", "rate": "70.00%"},
        {"id": 512, "name": "Apple", "rate": "10.00%"},
        {"id": 938, "name": "Sticky Mucus", "rate": "4.00%"},
    ],
}
LUNATIC_FIELDS: dict[str, Any] = {
    "level": "3",
    "hp": "75",
    "drops": [{"id": 909, "name": "Jellopy", "rate": "30.00%"}],
}
# Emperium droppers transcribed from the real monster rows: a 5% tie that the
# name tie-break must order deterministically (Baphomet before Solid Mineral),
# plus a rarer best-case-ordered rare dropper.
BAPHOMET_FIELDS: dict[str, Any] = {
    "level": "53",
    "hp": "8136",
    "drops": [{"id": 714, "name": "Emperium", "rate": "5.00%"}],
}
SOLID_MINERAL_FIELDS: dict[str, Any] = {
    "level": "31",
    "hp": "1450",
    "drops": [{"id": 714, "name": "Emperium", "rate": "5.00%"}],
}
ANGELING_FIELDS: dict[str, Any] = {
    "level": "19",
    "hp": "2220",
    "drops": [{"id": 714, "name": "Emperium", "rate": "0.41%"}],
}
# The real corpus also carries a monster named 'Emperium' (the WoE statue,
# id 1288): a name collision the mention scan must resolve to the item.
EMPERIUM_MOB_FIELDS: dict[str, Any] = {"level": "1", "hp": "100"}


def _build_iro_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE entities (
          section TEXT NOT NULL, id INTEGER NOT NULL, name TEXT, url TEXT,
          fetched_at TEXT, sections TEXT, fields_json TEXT, raw_html TEXT,
          PRIMARY KEY (section, id));
        CREATE VIRTUAL TABLE fts_pages USING fts5(
          title, body, section UNINDEXED, ref_id UNINDEXED, url UNINDEXED);
        """)
    rows = [
        ("items", 714, "Emperium", EMPERIUM_FIELDS),
        ("items", 909, "Jellopy", JELLOPY_FIELDS),
        ("items", 501, "Red Potion", RED_POTION_FIELDS),
        ("monsters", 1002, "Poring", PORING_FIELDS),
        ("monsters", 1063, "Lunatic", LUNATIC_FIELDS),
        ("monsters", 1039, "Baphomet", BAPHOMET_FIELDS),
        ("monsters", 2750, "Solid Mineral", SOLID_MINERAL_FIELDS),
        ("monsters", 1096, "Angeling", ANGELING_FIELDS),
        ("monsters", 1288, "Emperium", EMPERIUM_MOB_FIELDS),
    ]
    for section, ident, name, fields in rows:
        con.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?)",
            (section, ident, name, "", "", "", json.dumps(fields), ""),
        )
        con.execute(
            "INSERT INTO fts_pages (title, body, section, ref_id, url) VALUES (?,?,?,?,?)",
            (name, json.dumps(fields), section, ident, ""),
        )
    con.commit()
    con.close()


def _build_iro_wiki(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE VIRTUAL TABLE fts_pages USING fts5(
          section, title, body, tokenize='unicode61');
        """)
    rows = [
        (
            "all_pages",
            "Guild System",
            (
                "The guild system allows players to form a guild. Creating a guild "
                "requires an Emperium."
            ),
        ),
        (
            "all_pages",
            "Leveling Spots",
            (
                "This page lists recommended leveling spots, with the maps and monsters "
                "for each level range."
            ),
        ),
        (
            "maps",
            "Prontera South Gate",
            "prt_fild08 connects Prontera to the fields. Monsters: Poring, Drops, Lunatic.",
        ),
    ]
    for section, title, body in rows:
        con.execute("INSERT INTO fts_pages VALUES (?,?,?)", (section, title, body))
    con.commit()
    con.close()


@pytest.fixture
def fake_corpora(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the corpus env overrides at tmp_path-built fake corpora."""
    iro_db = tmp_path / "iro-db.db"
    iro_wiki = tmp_path / "iro-wiki.db"
    _build_iro_db(iro_db)
    _build_iro_wiki(iro_wiki)
    monkeypatch.setenv("RO_BOTS_IRO_DB", str(iro_db))
    monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(iro_wiki))
    return tmp_path


def _build_rathena(root: Path) -> None:
    """A fake rathena tree with the REAL declaration line shapes (tab-split)."""
    mobs_fields = root / "npc" / "pre-re" / "mobs" / "fields"
    mobs_fields.mkdir(parents=True)
    # A commented-out declaration must be skipped; counts ride the id field.
    (mobs_fields / "prontera.txt").write_text(
        "//prt_fild09,0,0\tmonster\tPoring\t1002,7\n"
        "prt_fild08,0,0\tmonster\tPoring\t1002,70\n"
        "prt_fild08,0,0\tmonster\tLunatic\t1063,40\n",
        encoding="utf-8",
    )
    mobs_cities = root / "npc" / "pre-re" / "mobs" / "cities"
    mobs_cities.mkdir(parents=True)
    (mobs_cities / "prontera.txt").write_text(
        "prontera,0,0\tmonster\tPoring\t1002,5\n",
        encoding="utf-8",
    )
    warps_cities = root / "npc" / "pre-re" / "warps" / "cities"
    warps_cities.mkdir(parents=True)
    (warps_cities / "prontera.txt").write_text(
        "prontera,156,22,0\twarp\tprt001\t3,2,prt_fild08,170,375\n"
        "prontera,177,221,0\twarp\tprt05\t4,2,prt_in,168,124\n"
        "prontera,156,360,0\twarp\tprt005\t4,2,prt_castle,102,20\n",
        encoding="utf-8",
    )
    warps_fields = root / "npc" / "pre-re" / "warps" / "fields"
    warps_fields.mkdir(parents=True)
    (warps_fields / "prontera_fild.txt").write_text(
        "prt_fild08,383,239,0\twarp\tprtf081\t3,20,izlude,196,208\n",
        encoding="utf-8",
    )


@pytest.fixture
def fake_rathena(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point RO_BOTS_RATHENA at a tmp_path-built fake declaration tree."""
    root = tmp_path / "rathena"
    _build_rathena(root)
    monkeypatch.setenv("RO_BOTS_RATHENA", str(root))
    return root


def _make_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RO_BOTS_IRO_DB", str(tmp_path / "missing.db"))
    monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(tmp_path / "missing.db"))
    monkeypatch.setenv("RO_BOTS_RATHENA", str(tmp_path / "missing-rathena"))


class TestMobsDropping:
    def test_droppers_best_first(self, fake_corpora: Path) -> None:
        lines = queries.mobs_dropping("Emperium")
        assert lines
        assert "Baphomet" in lines[0]
        assert "5%" in lines[0]
        # The 5%/5% tie orders deterministically by name.
        assert any("Solid Mineral" in line for line in lines)
        assert lines.index(next(line for line in lines if "Baphomet" in line)) < lines.index(
            next(line for line in lines if "Solid Mineral" in line)
        )

    def test_rare_dropper_after_common(self, fake_corpora: Path) -> None:
        lines = queries.mobs_dropping("Emperium")
        baphomet = next(i for i, line in enumerate(lines) if "Baphomet" in line)
        angeling = next(i for i, line in enumerate(lines) if "Angeling" in line)
        assert baphomet < angeling

    def test_lookup_by_item_id(self, fake_corpora: Path) -> None:
        by_name = queries.mobs_dropping("Emperium")
        by_id = queries.mobs_dropping(714)
        assert by_id == by_name

    def test_item_without_mob_droppers_gives_empty(self, fake_corpora: Path) -> None:
        # Red Potion exists as an item row but no fake monster drops it.
        assert queries.mobs_dropping("Red Potion") == ()

    def test_unknown_item_is_empty_not_error(self, fake_corpora: Path) -> None:
        assert queries.mobs_dropping("Notarealitem") == ()
        assert queries.mobs_dropping("") == ()

    def test_absent_corpus_is_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _make_missing(monkeypatch, tmp_path)
        assert queries.mobs_dropping("Emperium") == ()

    def test_bounded_lines(self, fake_corpora: Path) -> None:
        lines = queries.mobs_dropping("Emperium", limit=2)
        assert len(lines) == 2
        assert all(len(line) <= 160 for line in lines)


class TestMobDrops:
    def test_drop_table_lines(self, fake_corpora: Path) -> None:
        lines = queries.mob_drops("Poring")
        assert lines
        assert lines[0].startswith("Poring (1002)")
        assert "HP 60" in lines[0]
        assert any("Jellopy" in line and "70%" in line for line in lines)

    def test_drops_best_first(self, fake_corpora: Path) -> None:
        lines = queries.mob_drops("Poring")
        jellopy = next(i for i, line in enumerate(lines) if "Jellopy" in line)
        mucus = next(i for i, line in enumerate(lines) if "Sticky Mucus" in line)
        assert jellopy < mucus

    def test_lookup_by_mob_id(self, fake_corpora: Path) -> None:
        assert queries.mob_drops(1002) == queries.mob_drops("Poring")

    def test_unknown_mob_is_empty(self, fake_corpora: Path) -> None:
        assert queries.mob_drops("Notarealmob") == ()

    def test_absent_corpus_is_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _make_missing(monkeypatch, tmp_path)
        assert queries.mob_drops("Poring") == ()

    def test_bounded_lines(self, fake_corpora: Path) -> None:
        lines = queries.mob_drops("Poring", limit=2)
        assert len(lines) <= 2
        assert all(len(line) <= 160 for line in lines)


class TestMobSpawns:
    def test_maps_with_counts(self, fake_rathena: Path) -> None:
        lines = queries.mob_spawns("Poring")
        assert lines
        # Densest map first: prt_fild08 (70) outranks prontera (5).
        assert lines[0].startswith("Poring (1002) on prt_fild08")
        assert "70" in lines[0]
        assert any("prontera" in line and "5" in line for line in lines)

    def test_commented_declarations_skipped(self, fake_rathena: Path) -> None:
        lines = queries.mob_spawns("Poring")
        assert all("prt_fild09" not in line for line in lines)

    def test_lookup_by_mob_id(self, fake_rathena: Path) -> None:
        by_name = queries.mob_spawns("Poring")
        by_id = queries.mob_spawns(1002)
        assert by_id == by_name

    def test_unknown_mob_is_empty(self, fake_rathena: Path) -> None:
        assert queries.mob_spawns("Notarealmob") == ()

    def test_absent_rathena_is_empty(
        self, fake_corpora: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RO_BOTS_RATHENA", str(tmp_path / "missing-rathena"))
        assert queries.mob_spawns("Poring") == ()

    def test_bounded_lines(self, fake_rathena: Path) -> None:
        lines = queries.mob_spawns("Poring", limit=1)
        assert len(lines) <= 1
        assert all(len(line) <= 160 for line in lines)


class TestRouteHint:
    def test_direct_warp_line(self, fake_rathena: Path) -> None:
        lines = queries.route_hint("prt_fild08")
        assert len(lines) == 1
        assert "prontera,156,22" in lines[0]
        assert "prt001" in lines[0]
        assert "prt_fild08,170,375" in lines[0]

    def test_interior_warp_line(self, fake_rathena: Path) -> None:
        lines = queries.route_hint("prt_in")
        assert len(lines) == 1
        assert "prt05" in lines[0]
        assert "prt_in,168,124" in lines[0]

    def test_hub_self_lists_exits(self, fake_rathena: Path) -> None:
        lines = queries.route_hint("prontera")
        assert len(lines) == 1
        assert "prt001" in lines[0]
        assert "prt05" in lines[0]

    def test_two_hop_route(self, fake_rathena: Path) -> None:
        lines = queries.route_hint("izlude")
        assert len(lines) == 1
        assert "via prt_fild08" in lines[0]
        assert "izlude" in lines[0]

    def test_unknown_map_is_empty(self, fake_rathena: Path) -> None:
        assert queries.route_hint("not_a_map") == ()

    def test_absent_rathena_is_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RO_BOTS_RATHENA", str(tmp_path / "missing-rathena"))
        assert queries.route_hint("prt_in") == ()

    def test_line_bounded(self, fake_rathena: Path) -> None:
        for hint in (queries.route_hint("izlude"), queries.route_hint("prontera")):
            assert all(len(line) <= 160 for line in hint)


class TestQuestLines:
    def test_lines_carry_titles_and_snippets(self, fake_corpora: Path) -> None:
        lines = queries.quest_lines("Emperium")
        assert lines
        assert any(line.startswith("Guild System:") for line in lines)
        assert all(len(line) <= 160 for line in lines)

    def test_limit_respected(self, fake_corpora: Path) -> None:
        assert len(queries.quest_lines("leveling", limit=1)) <= 1

    def test_unknown_term_is_empty(self, fake_corpora: Path) -> None:
        assert queries.quest_lines("zzzznotaterm") == ()
        assert queries.quest_lines("") == ()

    def test_absent_corpus_is_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _make_missing(monkeypatch, tmp_path)
        assert queries.quest_lines("Emperium") == ()


class TestMentionLines:
    def test_item_and_mob_mentions_become_query_lines(self, fake_corpora: Path) -> None:
        lines = queries.mention_lines(("bring the Emperium to the guild spot",))
        assert lines
        assert any("Emperium" in line for line in lines)

    def test_item_wins_name_collision(self, fake_corpora: Path) -> None:
        # 'Emperium' resolves to the item (droppers), not the WoE statue mob.
        lines = queries.mention_lines(("need the Emperium",))
        assert any("<- " in line and "Baphomet" in line for line in lines)
        assert not any(line.startswith("Emperium: HP") for line in lines)

    def test_mob_mention_gets_context_line(self, fake_corpora: Path) -> None:
        lines = queries.mention_lines(("porings are cute", "watch that Lunatic"))
        assert any(line.startswith("Poring:") for line in lines)
        assert any(line.startswith("Lunatic:") for line in lines)

    def test_bounded_by_max_lines(self, fake_corpora: Path) -> None:
        lines = queries.mention_lines(
            ("Emperium Poring Lunatic Baphomet Angeling Solid Mineral",), max_lines=2
        )
        assert len(lines) <= 2

    def test_no_mentions_gives_empty(self, fake_corpora: Path) -> None:
        assert queries.mention_lines(("nothing relevant here",)) == ()
        assert queries.mention_lines(()) == ()

    def test_absent_corpus_gives_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_missing(monkeypatch, tmp_path)
        assert queries.mention_lines(("Emperium",)) == ()


class TestDecideWiring:
    """Mention lines ride along inside the existing decide-line cap."""

    def test_topics_produce_mention_lines(self, fake_corpora: Path) -> None:
        state = make_state()
        lines = game_context.decide_knowledge_lines(
            state, topics=("objective: create a guild, need an Emperium",)
        )
        assert any("Emperium" in line for line in lines)
        assert len(lines) <= game_context.MAX_DECIDE_LINES

    def test_recent_chat_derives_mentions_by_default(self, fake_corpora: Path) -> None:
        state = make_state(
            recent_chat=(ChatLine("public", "Ada", "anyone farming emperium?", 1.0),)
        )
        lines = game_context.decide_knowledge_lines(state)
        assert any("Emperium" in line for line in lines)
        assert len(lines) <= game_context.MAX_DECIDE_LINES

    def test_cap_never_grows(self, fake_corpora: Path) -> None:
        state = make_state(
            base_level=10,
            received_stats=(9, 1, 1, 1, 9, 1),
            inventory={str(i): 1 for i in range(900, 940)},
            recent_chat=(ChatLine("public", "Bo", "emperium poring lunatic", 1.0),),
        )
        lines = game_context.decide_knowledge_lines(state, topics=("Emperium", "Poring"))
        assert len(lines) <= game_context.MAX_DECIDE_LINES

    def test_absent_corpora_still_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_missing(monkeypatch, tmp_path)
        state = make_state(recent_chat=(ChatLine("public", "Ada", "emperium?", 1.0),))
        assert game_context.decide_knowledge_lines(state) == []


class TestRealCorpusSmoke:
    """Real-data smokes: skip cleanly on a fresh clone / CI without data."""

    def test_real_emperium_droppers(self) -> None:
        if not (Path.cwd() / "run/knowledge/iro-db/iro-db.db").is_file():
            pytest.skip("iro-db corpus absent")
        lines = queries.mobs_dropping("Emperium")
        assert lines
        assert all("Emperium" in line for line in lines)
        assert any("Baphomet" in line for line in lines)

    def test_real_poring_drops_and_spawns(self) -> None:
        if not (Path.cwd() / "run/knowledge/iro-db/iro-db.db").is_file():
            pytest.skip("iro-db corpus absent")
        drops = queries.mob_drops("Poring")
        assert any("Jellopy" in line for line in drops)
        if not (Path.cwd() / "rathena/npc/pre-re/mobs").is_dir():
            pytest.skip("rathena declarations absent")
        spawns = queries.mob_spawns("Poring")
        assert any(line.startswith("Poring (1002) on prt_fild08:") for line in spawns)

    def test_real_route_hint(self) -> None:
        if not (Path.cwd() / "rathena/npc/pre-re/warps").is_dir():
            pytest.skip("rathena declarations absent")
        hint = queries.route_hint("prt_in")
        assert hint
        assert "prontera" in hint[0]
        assert "prt_in" in hint[0]

    def test_real_quest_lines(self) -> None:
        if not (Path.cwd() / "run/knowledge/iro-wiki/iro-wiki.db").is_file():
            pytest.skip("iro-wiki corpus absent")
        lines = queries.quest_lines("Guild System")
        assert lines
