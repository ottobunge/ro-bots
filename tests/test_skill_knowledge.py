"""Public meanings through real offline native receipt consumers."""

import hashlib
import json
import struct
import zlib
from collections import deque
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from robots import playing as cli
from robots.adapters.native_navigation import ENTRY, HEADER
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.adapters.skill_knowledge import load_skill_knowledge
from robots.app import agent_runtime
from robots.app.playing_runtime import PlayingClient
from robots.domain.decisions import build_decision_request
from robots.domain.model import Goal
from robots.domain.skill_knowledge import PublicSkillKnowledge, serialized_advice
from robots.domain.skills import EffectiveSkill, ReceivedSkillContextReadOnly
from tests.test_native_skill_context import dispatch, row, setup, skill_list

ASSET = Path(__file__).resolve().parents[1] / "knowledge/skill-meaning-seed.json"


def test_received_basic9_meaning_reaches_clef_without_rewriting_facts():
    bot, playing, sent = setup()
    playing = PlayingClient(bot, public_skill_knowledge=load_skill_knowledge(ASSET, "pre-re"))
    dispatch(bot, skill_list(row()))
    state = playing.build_native_state(Goal.GRIND)
    request = build_decision_request(state, ["private memory unchanged"])
    advice = request["state"].get("skill_rules_knowledge")
    assert advice is not None, "received Basic Skill needs separate public meaning in Clef state"
    card = advice["cards"][0]
    assert card["id"] == 1
    assert card["name"] == "Basic Skill"
    assert card["aegis_name"] == "NV_BASIC"
    assert card["ruleset"] == "pre-re"
    assert "trade" in card["meaning"].lower()
    assert "basic_skill_check" in card["meaning"]
    assert card["revision"] == "e985006171d2eb320ee512a653f4c83aea3d81b6"
    assert card["db_sha256"]
    assert card["meaning_source_sha256"]
    assert advice["authority"] == "public_advice"
    facts = request["state"]["observed_effective_skills"]
    assert facts["rows"][0]["level"] == 9
    assert facts["ownership"] == facts["casting_legality"] == "UNKNOWN"
    assert request["state"]["memory_view"] == "private memory unchanged"
    assert not sent


@pytest.mark.parametrize("ruleset", ["pre-re", "renewal"])
def test_ruleset_catalog_only_describes_received_rows(ruleset):
    catalog = load_skill_knowledge(ASSET, ruleset)
    for context in (ReceivedSkillContextReadOnly(), ReceivedSkillContextReadOnly((), 1, 0)):
        assert catalog.decision_advice(context)["cards"] == []
    context = ReceivedSkillContextReadOnly(
        (EffectiveSkill(2, 9, 0, 0, 0), EffectiveSkill(1, 0, 0, 0, 0)), 1, 1
    )
    advice = catalog.decision_advice(context)
    assert advice["uncovered_count"] == 1
    assert advice["coverage"] == "PARTIAL"
    assert [card["id"] for card in advice["cards"]] == [1]
    assert advice["cards"][0]["ruleset"] == ruleset
    assert advice["cards"][0]["declared_type"] is None
    card = advice["cards"][0]
    root = ASSET.parent.parent / "rathena"
    assert hashlib.sha256((root / card["db_path"]).read_bytes()).hexdigest() == card["db_sha256"]
    assert (
        hashlib.sha256((root / card["meaning_source_path"]).read_bytes()).hexdigest()
        == card["meaning_source_sha256"]
    )
    field = "ruleset"
    with pytest.raises(FrozenInstanceError):
        setattr(catalog, field, "other")


@pytest.mark.parametrize(
    "mutation",
    ["meaning", "source", "bool-id", "unknown-id", "duplicate-id", "bool-version", "count"],
)
def test_catalog_denies_unreviewed_input(tmp_path, mutation):
    document = json.loads(ASSET.read_text())
    if mutation == "meaning":
        document["cards"][0]["meaning"] = "Casting always legal"
    elif mutation == "source":
        document["cards"][0]["meaning_source_sha256"] = "0" * 64
    elif mutation == "bool-id":
        document["cards"][0]["id"] = True
    elif mutation == "unknown-id":
        document["cards"][0]["id"] = 2
    elif mutation == "duplicate-id":
        document["cards"].append(document["cards"][0])
    elif mutation == "bool-version":
        document["schema_version"] = True
    else:
        document["cards"] *= 17
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="public skill"):
        load_skill_knowledge(path, "pre-re")


def test_duplicate_json_keys_and_oversized_files_denied(tmp_path):
    path = tmp_path / "catalog.json"
    for raw in ('{"schema_version":1,"schema_version":1,"cards":[]}', " " * 262145):
        path.write_text(raw)
        with pytest.raises(ValueError, match="public skill"):
            load_skill_knowledge(path, "pre-re")
    with pytest.raises(ValueError, match="public skill"):
        load_skill_knowledge(ASSET, "classic")


@pytest.mark.parametrize(
    "budget", [{"max_cards": True}, {"max_utf8_bytes": True}, {"max_cards": 9}]
)
def test_budget_booleans_and_excess_card_limits_denied(budget):
    with pytest.raises(ValueError, match="public skill"):
        load_skill_knowledge(ASSET, "pre-re").decision_advice(
            ReceivedSkillContextReadOnly(), **budget
        )


def test_multibyte_budget_includes_names_and_complete_provenance():
    catalog = load_skill_knowledge(ASSET, "pre-re")
    card = replace(catalog.cards[0], meaning="知" * 1000)
    large = PublicSkillKnowledge("pre-re", (card,))
    context = ReceivedSkillContextReadOnly((EffectiveSkill(1, 9, 0, 0, 0),), 1, 1)
    advice = large.decision_advice(context)
    assert advice["cards"] == []
    assert advice["truncated"] is True
    fitted = catalog.decision_advice(context)
    assert len(serialized_advice(fitted)) <= 2048
    assert fitted["cards"][0]["meaning_source_lines"]
    assert catalog.decision_advice(context, max_cards=0)["truncated"] is True
    base = replace(card, meaning="知" * 100)
    sized = PublicSkillKnowledge("pre-re", (base,))
    padding = 2048 - len(serialized_advice(sized.decision_advice(context)))
    exact = PublicSkillKnowledge("pre-re", (replace(base, meaning=base.meaning + "x" * padding),))
    rows = tuple(EffectiveSkill(i, 9, 0, 0, 0) for i in range(1, 257))
    many = exact.decision_advice(ReceivedSkillContextReadOnly(rows, 1, 1))
    assert len(serialized_advice(many)) <= 2048


@pytest.mark.parametrize("fault", ["health", "map", "client"])
def test_received_annotation_is_not_retained_after_invalidation(fault):
    bot, _, sent = setup()
    client = PlayingClient(bot, public_skill_knowledge=load_skill_knowledge(ASSET, "pre-re"))
    dispatch(bot, skill_list(row()))
    assert build_decision_request(client.build_native_state(Goal.GRIND))["state"][
        "skill_rules_knowledge"
    ]["cards"]
    if fault == "health":
        bot.running = False
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
        bot.running = True
    elif fault == "map":
        dispatch(bot, struct.pack("<H16sHH", 0x0091, b"prontera", 50, 50))
    else:
        new, _, _ = setup()
        client.wire = new
    advice = build_decision_request(client.build_native_state(Goal.GRIND))["state"][
        "skill_rules_knowledge"
    ]
    assert advice["cards"] == []
    assert advice["coverage"] == "UNKNOWN"
    assert not sent or sent == [b"\x7d\x00"]


def test_cli_opt_in_constructs_shared_public_catalog(tmp_path, monkeypatch):
    (tmp_path / "db/pre-re").mkdir(parents=True)
    body = zlib.compress(bytes(4))
    data = ENTRY.pack(b"prontera", 2, 2, len(body)) + body
    for relative in ("db/map_cache.dat", "db/pre-re/map_cache.dat"):
        (tmp_path / relative).write_bytes(HEADER.pack(HEADER.size + len(data), 1) + data)
    (tmp_path / "db/pre-re/mob_db.yml").write_text("Body: []\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "persona_id": "one",
                        "account": "offline",
                        "password": "unused",
                        "char_name": "WireNovice",
                    }
                ]
            }
        )
    )
    flags = [
        "--manifest",
        str(manifest),
        "--runtime-root",
        str(tmp_path),
        "--memory-root",
        str(tmp_path / "memory"),
        "--decision-url",
        "http://127.0.0.1:8091/v1/systemone",
    ]
    assert getattr(cli.parse_args(flags), "skill_knowledge", "MISSING") is None
    args = cli.parse_args([*flags, "--skill-knowledge", str(ASSET)])
    monkeypatch.setattr(cli, "make_local_chat", lambda _: object())
    monkeypatch.setattr(cli, "make_private_decision", lambda _: object())
    bot, _, _ = setup()
    monkeypatch.setattr(agent_runtime, "_BotClient", lambda *_a, **_k: bot)
    host = cli.build_host(args)
    try:
        assert host.client_factory is not None
        first = host.client_factory(host.manifest["one"])
        second = host.client_factory(host.manifest["one"])
        assert first.public_skill_knowledge is second.public_skill_knowledge
        assert first.public_skill_knowledge.ruleset == "pre-re"
        dispatch(bot, skill_list(row()))
        assert (
            build_decision_request(first.build_native_state(Goal.GRIND))["state"][
                "skill_rules_knowledge"
            ]["cards"][0]["name"]
            == "Basic Skill"
        )
    finally:
        host.stop()


@pytest.mark.parametrize("fault", ["bool-id", "duplicate", "mutable", "overfull", "bad-ruleset"])
def test_domain_catalog_rejects_malformed_injected_cards(fault):
    catalog = load_skill_knowledge(ASSET, "pre-re")
    card = catalog.cards[0]
    cards: Any = (card,)
    ruleset = "pre-re"
    if fault == "bool-id":
        cards = (replace(card, id=True),)
    elif fault == "duplicate":
        cards = (card, card)
    elif fault == "mutable":
        cards = [card]
    elif fault == "overfull":
        cards = (card,) * 33
    else:
        ruleset = "unknown"
    with pytest.raises(ValueError, match="public skill"):
        PublicSkillKnowledge(ruleset, cards)


def test_received_gap_removes_public_annotation():
    bot, _, sent = setup()
    knowledge = load_skill_knowledge(ASSET, "pre-re")
    client = PlayingClient(bot, public_skill_knowledge=knowledge)
    dispatch(bot, skill_list(row()))
    state = client.build_native_state(Goal.GRIND)
    assert state.received_skills is not None
    assert state.received_skills.rows
    bot._native_frames = deque(bot._native_frames, maxlen=2)
    for value in (1, 2, 3):
        dispatch(bot, struct.pack("<HHi", 0x00B0, 12, value))
    with pytest.raises(NativeTelemetryUnavailable, match="continuity"):
        client.build_native_state(Goal.GRIND)
    advice = knowledge.decision_advice(client.received_skills)
    assert advice["cards"] == []
    assert advice["coverage"] == "UNKNOWN"
    assert not sent
