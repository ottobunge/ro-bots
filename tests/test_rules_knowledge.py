"""Offline advisory lookup; fixture requests are not live bot acceptance."""

import importlib.util
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from robots.adapters.rules_knowledge import RulesKnowledge, serialize_cards

SEED = Path(__file__).resolve().parents[1] / "knowledge" / "iro-rules-seed.json"


def test_loads_real_seed_as_frozen_advisory_cards():
    assert importlib.util.find_spec("robots.adapters.rules_knowledge") is not None
    catalog = RulesKnowledge.load(SEED)
    cards = catalog.select("pre-re", topics=("stats",))
    assert len(cards) == 2
    assert all(card.authority == "advice" for card in cards)
    assert all(card.mechanically_verified is False for card in cards)
    assert all(card.private_context is False for card in cards)


def test_rulesets_never_substitute_and_unknown_ruleset_is_rejected():
    catalog = RulesKnowledge.load(SEED)
    assert all(card.ruleset == "renewal" for card in catalog.select("renewal"))
    assert catalog.select("pre-re", topics=("equipment",)) == ()
    with pytest.raises(ValueError, match="ruleset"):
        catalog.select("classic")


def test_count_and_utf8_budget_include_whole_provenance(tmp_path):
    data = json.loads(SEED.read_text())
    data["cards"][0]["text"] = "弓の知識 — advisory"
    path = tmp_path / "synthetic-unicode.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    catalog = RulesKnowledge.load(path)
    first = catalog.select("pre-re", max_cards=1)
    encoded = serialize_cards(first)
    assert "弓".encode() in encoded
    assert data["cards"][0]["source_url"].encode() in encoded
    assert catalog.select("pre-re", max_utf8_bytes=len(encoded)) == first
    assert catalog.select("pre-re", max_utf8_bytes=len(encoded) - 1) == ()
    assert catalog.select("pre-re", max_cards=0) == ()
    assert catalog.select("pre-re", max_utf8_bytes=0) == ()
    for bad in (True, -1, 1.5, "2", 9):
        with pytest.raises(ValueError, match=r".+"):
            catalog.select("pre-re", max_cards=cast(int, bad))
    for bad in (True, -1, 1.5, "2"):
        with pytest.raises(ValueError, match=r".+"):
            catalog.select("pre-re", max_utf8_bytes=cast(int, bad))


@pytest.mark.parametrize(
    "mutation",
    [
        "authority",
        "mechanically_verified",
        "source_url",
        "revision",
        "content_sha256",
        "retrieved_on",
        "ruleset",
        "topic",
        "text",
        "duplicate_id",
        "too_many",
        "schema",
        "unknown_root",
        "source_id",
        "cross_source",
        "null_card",
        "empty_id",
    ],
)
def test_untrusted_metadata_is_rejected(tmp_path, mutation):
    data = json.loads(SEED.read_text())
    row = data["cards"][0]
    if mutation in ("authority", "mechanically_verified"):
        row[mutation] = True
    elif mutation == "duplicate_id":
        data["cards"].append(row.copy())
    elif mutation == "too_many":
        data["cards"] = [row.copy() for _ in range(33)]
    elif mutation == "schema":
        data["schema_version"] = True
    elif mutation == "unknown_root":
        data["private_memory"] = []
    elif mutation == "text":
        row[mutation] = "x" * 1025
    elif mutation == "cross_source":
        row["ruleset"] = "renewal"
    elif mutation == "null_card":
        data["cards"][0] = None
    elif mutation == "empty_id":
        row["card_id"] = ""
    else:
        row[mutation] = "untrusted"
    path = tmp_path / "synthetic-invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r".+"):
        RulesKnowledge.load(path)


@pytest.mark.parametrize(
    "payload",
    [
        '{"schema_version":1,"schema_version":1,"cards":[]}',
        " " * 262145 + '{"schema_version":1,"cards":[]}',
        "[]",
        '{"schema_version":1,"cards":null}',
    ],
    ids=("duplicate-key", "oversize", "list-root", "null-cards"),
)
def test_bounded_json_rejects_duplicate_keys_and_invalid_root(tmp_path, payload):
    path = tmp_path / "synthetic-invalid-root.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=r".+"):
        RulesKnowledge.load(path)


@pytest.mark.parametrize("topics", ["stats", ("private_memory",), (True,)])
def test_invalid_topic_requests_fail_closed(topics):
    with pytest.raises(ValueError, match="topic"):
        RulesKnowledge.load(SEED).select("pre-re", topics=topics)


def test_maximum_card_limit_preserves_stable_order_and_frozen_values(tmp_path):
    data = json.loads(SEED.read_text())
    row = data["cards"][0]
    data["cards"] = [dict(row, card_id=f"synthetic-{index}") for index in range(32)]
    path = tmp_path / "synthetic-count.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    catalog = RulesKnowledge.load(path)
    cards = catalog.select("pre-re", max_cards=8, max_utf8_bytes=65536)
    assert tuple(card.card_id for card in cards) == tuple(f"synthetic-{i}" for i in range(8))
    assert cards == catalog.select("pre-re", max_cards=8, max_utf8_bytes=65536)
    with pytest.raises(FrozenInstanceError, match="cannot assign"):
        cards[0].text = "changed"  # type: ignore[misc]  # deliberate mutation rejection
