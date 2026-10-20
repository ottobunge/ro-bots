"""Corpus readers + bounded decide-context composition (criteria 4 and 10).

The fake corpora below are built in tmp_path from SMALL transcribed snapshots
of the real git-ignored iro-db/iro-wiki rows (fixture literals, never the
corpus itself). Real-corpus smoke tests skip when the corpora are absent.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from robots.domain.decisions import build_decision_request
from robots.knowledge import corpora, game_context
from tests.conftest import make_state

# --- SMALL fixture snapshots (transcribed from the live corpus, 2026-10-15) ----

PORING_FIELDS: dict[str, Any] = {
    "level": "1",
    "def": "2 + 1 0.45%",
    "hp": "60",
    "mdef": "5 4.29%",
    "base_exp": "27",
    "job_exp": "20",
    "size": "Medium",
    "race": "Plant",
    "element": "Water 1",
    "drops": [
        {"id": 909, "name": "Jellopy", "rate": "70.00%"},
        {"id": 512, "name": "Apple", "rate": "10.00%"},
        {"id": 938, "name": "Sticky Mucus", "rate": "4.00%"},
    ],
}
CHRYSLIS_FIELDS: dict[str, Any] = {
    "type": "Misc",
    "subtype": "General",
    "weight": "1",
    "buying_price": "--",
    "selling_price": "4 Z (4 Z)",
}
KNIFE_FIELDS: dict[str, Any] = {"type": "Weapon", "subtype": "Dagger", "attack": "17"}


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
        ("monsters", 1002, "Poring", PORING_FIELDS),
        ("items", 915, "Chrysalis", CHRYSLIS_FIELDS),
        ("items", 1201, "Knife [3]", KNIFE_FIELDS),
    ]
    for section, ident, name, fields in rows:
        con.execute(
            "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?)",
            (section, ident, name, "", "", "", json.dumps(fields), ""),
        )
        body = json.dumps(fields)
        con.execute(
            "INSERT INTO fts_pages (title, body, section, ref_id, url) VALUES (?,?,?,?,?)",
            (name, body, section, ident, ""),
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
    con.execute(
        "INSERT INTO fts_pages VALUES (?,?,?)",
        (
            "maps",
            "Prontera South Gate",
            ("prt_fild08 connects Prontera to the fields. Monsters: Poring, Drops, "
            "Lunatic, Pupa. A classic newbie grinding field."),
        ),
    )
    con.commit()
    con.close()


@pytest.fixture
def fake_corpora(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the corpus env overrides at tmp_path-built fake corpora."""
    iro_db = tmp_path / "iro-db.db"
    iro_wiki = tmp_path / "iro-wiki.db"
    _build_iro_db(iro_db)
    _build_iro_wiki(iro_wiki)
    monkeypatch.setenv("RO_BOTS_IRO_DB", str(iro_db))
    monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(iro_wiki))
    return tmp_path


class TestCorporaReaders:
    def test_item_fields_by_id(self, fake_corpora: None) -> None:
        fields = corpora.item_fields(915)
        assert fields is not None
        assert fields["type"] == "Misc"
        assert fields["selling_price"] == "4 Z (4 Z)"

    def test_item_fields_unknown_id_is_none(self, fake_corpora: None) -> None:
        assert corpora.item_fields(404404) is None

    def test_item_fields_items_section_only(self, fake_corpora: None) -> None:
        # id 1201 is Knife among items AND Rybio among monsters; section filter wins.
        assert corpora.item_fields(1201)["type"] == "Weapon"

    def test_monster_fields_by_name(self, fake_corpora: None) -> None:
        fields = corpora.monster_fields("Poring")
        assert fields is not None
        assert fields["hp"] == "60"
        assert fields["drops"][0]["name"] == "Jellopy"

    def test_monster_context_line_shape(self, fake_corpora: None) -> None:
        line = corpora.monster_context_line(corpora.monster_fields("Poring"))
        assert line.startswith("Poring:")
        assert "HP 60" in line
        assert "exp 27/20" in line
        assert "Jellopy 70%" in line
        assert len(line) <= 160

    def test_wiki_snippets_bounded(self, fake_corpora: None) -> None:
        snippets = corpora.wiki_snippets("prt_fild08", section="maps")
        assert snippets
        assert all(len(s) <= 200 for s in snippets)
        assert "prt_fild08" in snippets[0].lower()

    def test_wiki_snippets_absent_corpus_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(tmp_path / "missing.db"))
        assert corpora.wiki_snippets("anything") == []


class TestDecideKnowledgeLines:
    def test_lines_for_inventory_stats_and_target(self, fake_corpora: None) -> None:
        state = make_state(
            base_level=10,
            received_stats=(9, 1, 1, 1, 9, 1),  # str agi vit int dex luk
            inventory={"915": 2, "1201": 1},  # production keys are str(item_id)
        )
        lines = game_context.decide_knowledge_lines(state)
        assert lines, "corpora present: lines must compose"
        assert len(lines) <= game_context.MAX_DECIDE_LINES
        assert any("Chrysalis" in line and "sellable 4z" in line for line in lines)
        assert any("no bonus" in line for line in lines)
        assert any("Poring" in line and "HP 60" in line for line in lines)
        assert any("atk 27" in line for line in lines)  # novice batk 10 + knife 17
        assert all(len(line) <= game_context.MAX_LINE_CHARS for line in lines)

    def test_named_inventory_keys_resolve_via_fts(self, fake_corpora: None) -> None:
        state = make_state(inventory={"Jellopy": 23})
        lines = game_context.decide_knowledge_lines(state)
        # Jellopy is not an entity row: no line, but no crash either.
        assert all("Jellopy" not in line or "sellable" not in line for line in lines)

    def test_absent_corpus_gives_no_lines(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("RO_BOTS_IRO_DB", str(tmp_path / "missing.db"))
        monkeypatch.setenv("RO_BOTS_IRO_WIKI", str(tmp_path / "missing.db"))
        state = make_state(inventory={"915": 1})
        assert game_context.decide_knowledge_lines(state) == []

    def test_line_count_capped(self, fake_corpora: None) -> None:
        state = make_state(inventory={str(i): 1 for i in range(900, 940)})
        lines = game_context.decide_knowledge_lines(state)
        assert len(lines) <= game_context.MAX_DECIDE_LINES


class TestDecideRequestHook:
    def test_request_carries_game_knowledge(self, fake_corpora: None) -> None:
        state = make_state(received_stats=(9, 1, 1, 1, 9, 1), inventory={"915": 2})
        lines = game_context.decide_knowledge_lines(state)
        request = build_decision_request(state, knowledge_lines=lines)
        assert request["state"]["game_knowledge"] == lines

    def test_request_without_lines_has_no_key(self, fake_corpora: None) -> None:
        request = build_decision_request(make_state())
        assert "game_knowledge" not in request["state"]


class TestRealCorpusSmoke:
    def test_real_corpus_poring_line(self) -> None:
        corpus = Path.cwd() / "run/knowledge/iro-db/iro-db.db"
        if not corpus.exists():
            pytest.skip("iro-db corpus absent")
        state = make_state(
            base_level=10,
            received_stats=(9, 1, 1, 1, 9, 1),
            inventory={"915": 2, "1201": 1},
        )
        lines = game_context.decide_knowledge_lines(state)
        assert any(line.startswith("Poring:") and "HP" in line for line in lines)
        assert any("Chrysalis" in line for line in lines)
