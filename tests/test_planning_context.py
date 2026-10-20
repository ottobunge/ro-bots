"""Offline received-context investigation, with no native or model effects."""

from dataclasses import replace
from typing import Any

import pytest

from robots.adapters.skill_knowledge import load_skill_knowledge
from robots.app.planning_context import (
    InvestigationReader,
    ObservationSnapshot,
    serialized_response,
)
from robots.domain.model import Goal
from robots.domain.planning import Capabilities, PlanningIdentity
from robots.society.memory import ExperienceNote, MemoryLog, StubSummarizer
from tests.test_native_skill_context import dispatch, row, setup, skill_list
from tests.test_skill_knowledge import ASSET

IDENTITY = PlanningIdentity("agent-a", "world-a", "opaque-77", 1, "pre-re")
CAPABILITIES = Capabilities(frozenset(), frozenset({"prontera"}), frozenset({"skill-points:0"}))


def fixture_reader() -> tuple[InvestigationReader, Any, list[bytes]]:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    state = playing.build_native_state(Goal.GRIND)
    reader = InvestigationReader(
        IDENTITY,
        lambda: ObservationSnapshot(IDENTITY, state, CAPABILITIES, free_skill_points=0),
        load_skill_knowledge(ASSET, "pre-re"),
        MemoryLog(StubSummarizer()),
    )
    return reader, state, sent


def test_real_basic_receipt_reaches_character_lookup_and_separate_public_meaning() -> None:
    reader, _, sent = fixture_reader()
    character = reader.read(IDENTITY, "character")
    assert character["data"]["received_effective_skills"]["rows"][0]["level"] == 9
    assert character["data"]["free_skill_points"] == 0
    skill = reader.read(IDENTITY, "received_skill", skill_id=1)
    assert skill["data"]["row"]["level"] == 9
    assert skill["data"]["ownership"] == "UNKNOWN"
    rule = reader.public_rule(IDENTITY, "skill:1")
    assert rule is not None
    assert "Basic Skill" in rule
    assert "trade" in rule.lower()
    assert reader.observed_capabilities(IDENTITY) == CAPABILITIES
    assert not sent


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("agent", "b"),
        ("world", "b"),
        ("character", "b"),
        ("session_epoch", 2),
        ("ruleset", "renewal"),
    ],
)
def test_foreign_identity_denied_before_any_provider(field: str, value: Any) -> None:
    reader, _, _ = fixture_reader()

    def forbidden() -> ObservationSnapshot:
        pytest.fail("foreign identity reached provider")

    reader.provider = forbidden
    identity = replace(IDENTITY, **{field: value})
    assert reader.read(identity, "memory_search")["status"] == "DENIED"
    assert reader.public_rule(identity, "skill:1") is None
    assert reader.observed_capabilities(identity).fresh_facts == frozenset()


@pytest.mark.parametrize("drift", ["identity", "epoch", "unknown"])
def test_current_provider_binding_drift_denies_even_public(drift: str) -> None:
    reader, state, _ = fixture_reader()
    owner: PlanningIdentity | None = (
        replace(IDENTITY, character="other") if drift == "identity" else IDENTITY
    )
    if drift == "unknown":
        owner = None
    if drift == "epoch":
        state = replace(state, native_epoch=2)
    reader.provider = lambda: ObservationSnapshot(owner, state, CAPABILITIES)
    assert reader.read(IDENTITY, "character")["status"] == "DENIED"
    assert reader.public_rule(IDENTITY, "skill:1") is None


def test_current_missing_state_keeps_public_but_no_character_facts() -> None:
    reader, _, _ = fixture_reader()
    reader.provider = lambda: ObservationSnapshot(IDENTITY, None, CAPABILITIES)
    assert reader.read(IDENTITY, "character")["status"] == "UNKNOWN"
    assert reader.public_rule(IDENTITY, "skill:1") is not None


def test_facts_copied_unknowns_life_and_perceived_map_only() -> None:
    reader, state, _ = fixture_reader()
    state = replace(state, inventory={"Apple": 3}, alive_known=False, alive=None)
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, CAPABILITIES)
    data = reader.read(IDENTITY, "character")["data"]
    assert data["stats"] == data["equipment"] == "UNKNOWN"
    assert data["alive_known"] is False
    assert data["alive"] is None
    data["inventory"]["rows"][0]["quantity"] = 9
    assert state.inventory == {"Apple": 3}
    assert reader.read(IDENTITY, "map")["data"]["geometry"] == "UNKNOWN"
    assert reader.read(IDENTITY, "received_skill", skill_id=99)["data"]["row"] is None


def test_unreceived_public_basic_ruleset_filter_and_capability_non_authority() -> None:
    reader, state, _ = fixture_reader()
    reader.provider = lambda: ObservationSnapshot(
        IDENTITY, replace(state, received_skills=None), CAPABILITIES
    )
    assert reader.read(IDENTITY, "received_skill", skill_id=1)["data"]["row"] is None
    result = reader.read(IDENTITY, "public_rule", rule_topic="skill:1")
    assert result["source"] == "public_advice"
    assert result["data"]["card"]["ruleset"] == "pre-re"
    assert result["data"]["ownership"] == "UNKNOWN"
    assert "mechanically_verified" not in str(result)
    assert reader.public_rule(IDENTITY, "skill:01") is None
    assert reader.public_rule(IDENTITY, "guide:foo") is None
    assert reader.observed_capabilities(IDENTITY) == CAPABILITIES


def test_constructor_no_reads_and_control_flow_propagates() -> None:
    reader, _, _ = fixture_reader()

    def interrupted() -> ObservationSnapshot:
        raise KeyboardInterrupt

    copy = InvestigationReader(IDENTITY, interrupted, reader.public, reader.memory)
    with pytest.raises(KeyboardInterrupt):
        copy.read(IDENTITY, "character")


def test_private_search_bounded_pages_and_no_summaries_or_writes() -> None:
    reader, _, _ = fixture_reader()
    for i in range(140):
        reader.memory.append(ExperienceNote(float(i), "chat", f"mine {i}"))
    before = reader.memory.notes()
    cursor = 0
    found: list[int] = []
    while True:
        result = reader.read(IDENTITY, "memory_search", query="mine", cursor=cursor)
        assert result["status"] == "OK"
        data = result["data"]
        assert len(data["rows"]) <= 8
        assert data["scanned"] <= 64
        found.extend(r["note_id"] for r in data["rows"])
        cursor = data["next_cursor"]
        if not data["has_more"]:
            break
    assert found == list(range(140))
    assert reader.memory.notes() == before
    assert reader.memory.dirty_upto == 0
    assert reader.memory.node_summary(0, 0) is None


def test_long_utf8_raw_read_roundtrips_stored_experience_text() -> None:
    reader, _, _ = fixture_reader()
    text = '雨🙂\\"\n' * 5000 + "THE END"
    reader.memory.append(ExperienceNote(1.0, "chat", text))
    offset = 0
    pieces = []
    while True:
        result = reader.read(IDENTITY, "memory_read", note_id=0, offset=offset, max_utf8_bytes=512)

        assert len(serialized_response(result)) <= 512
        data = result["data"]
        pieces.append(data["text"])
        if not data["has_more"]:
            break
        assert data["next_offset"] > offset
        offset = data["next_offset"]
    assert "".join(pieces) == text
    assert reader.memory.notes()[0].text == text


@pytest.mark.parametrize(
    "options",
    [
        {"cursor": True},
        {"cursor": -1},
        {"note_id": -1},
        {"offset": True},
        {"max_utf8_bytes": True},
        {"max_utf8_bytes": 255},
        {"max_utf8_bytes": 8193},
        {"query": "🙂" * 65},
    ],
)
def test_malformed_cursor_budget_query_rejected(options: dict[str, Any]) -> None:
    reader, _, _ = fixture_reader()
    with pytest.raises(ValueError, match="invalid investigation"):
        reader.read(IDENTITY, "memory_search", **options)


def test_budget_truncation_and_unknown_inventory_are_explicit() -> None:
    reader, state, _ = fixture_reader()
    state = replace(state, inventory={f"item-{i}": i for i in range(30)}, inventory_known=False)
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, CAPABILITIES)
    result = reader.read(IDENTITY, "inventory", cursor=8)
    assert result["data"]["rows"][0]["item"] == "item-8"
    assert all(r["quantity"] is None for r in result["data"]["rows"])
    assert result["data"]["has_more"]
    result = reader.read(IDENTITY, "character", max_utf8_bytes=256)

    assert len(serialized_response(result)) <= 256
    assert result["truncated"]


def test_private_owner_isolation_unknown_state_and_plain_substring() -> None:
    reader, _, _ = fixture_reader()
    reader.memory.append(ExperienceNote(1.0, "chat", "A secret [.*]"))
    other_memory = MemoryLog(StubSummarizer())
    other_memory.append(ExperienceNote(2.0, "chat", "B secret"))
    owner_b = replace(IDENTITY, agent="agent-b")
    other = InvestigationReader(
        owner_b,
        lambda: ObservationSnapshot(owner_b, None, CAPABILITIES),
        reader.public,
        other_memory,
    )
    assert other.read(owner_b, "memory_search", query="A secret")["data"]["rows"] == []
    assert reader.read(IDENTITY, "memory_search", query="[.*]")["data"]["rows"][0]["note_id"] == 0
    assert other.read(owner_b, "memory_read", note_id=0)["data"]["text"] == "B secret"


def test_boolean_skill_id_cannot_alias_basic_and_page_cursor_cannot_rewind() -> None:
    reader, _, _ = fixture_reader()
    with pytest.raises(ValueError, match="invalid investigation"):
        reader.read(IDENTITY, "received_skill", skill_id=True)
    with pytest.raises(ValueError, match="invalid investigation"):
        reader.read(IDENTITY, "inventory", cursor=1000)
