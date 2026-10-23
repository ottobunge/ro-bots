"""Unit tests for the read-only JSONL trace reader (fixtures, not live traces)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard_webapp.traces import (
    InvalidHistoryQuery,
    TraceHistory,
    clamp_limit,
    parse_before,
    parse_kinds,
    summarize,
)

T1 = "2026-10-22T10:00:00+00:00"
T2 = "2026-10-22T10:01:00+00:00"
T3 = "2026-10-22T10:02:00+00:00"
T4 = "2026-10-22T10:03:00+00:00"
T5 = "2026-10-22T10:04:00+00:00"
T6 = "2026-10-22T10:05:00+00:00"
T7 = "2026-10-22T10:06:00+00:00"
T8 = "2026-10-22T10:07:00+00:00"
T9 = "2026-10-22T10:08:00+00:00"
T10 = "2026-10-22T10:09:00+00:00"

# Chronological fixture: two encounters with Poring, one with Lunatic.
FIXTURE_LINES = [
    {
        "t": T1,
        "persona": "pop_test_m0",
        "kind": "goal_review",
        "goal": "grind",
        "previous_goal": "idle_town",
        "trigger": "heartbeat",
    },
    {
        "t": T2,
        "persona": "pop_test_m0",
        "kind": "plan_authored",
        "goal": "farm_item",
        "targets": ["Poring"],
        "map": "prt_fild08",
        "duration_s": 900.0,
        "trigger": "heartbeat",
    },
    {
        "t": T3,
        "persona": "pop_test_m0",
        "kind": "world_event",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "event": "MonsterSpotted",
        "monster": "Poring",
        "monster_id": 1001,
        "monster_x": 174,
        "monster_y": 358,
    },
    {
        "t": T3,
        "persona": "pop_test_m0",
        "kind": "action_executed",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "action": "Attack",
        "params": {"target_id": 1001},
    },
    {
        "t": T4,
        "persona": "pop_test_m0",
        "kind": "world_event",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "event": "DamageTaken",
        "amount": 6,
        "from_id": 1001,
    },
    {
        "t": T5,
        "persona": "pop_test_m0",
        "kind": "action_executed",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "action": "Attack",
        "params": {"target_id": 1001},
    },
    {
        "t": T6,
        "persona": "pop_test_m0",
        "kind": "chat_sent",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "channel": "party",
        "message": "poring train",
        "action": "PartyChat",
    },
    {
        "t": T6,
        "persona": "pop_test_m0",
        "kind": "chat_heard",
        "map": "prt_fild08",
        "x": 170,
        "y": 372,
        "speaker": "RinceNyan",
        "message": "gg",
        "channel": "public",
    },
    {
        "t": T6,
        "persona": "pop_test_m0",
        "kind": "decide_response",
        "answers": {"next_action": {"type": "choice", "choice": "grind", "confidence": 0.4}},
        "duration_s": 1.75,
    },
    {
        "t": T6,
        "persona": "pop_test_m0",
        "kind": "state_tick",
        "map": "prt_fild08",
        "hp": 80,
        "hp_max": 86,
    },
    # ~10 minutes later: a fresh Poring encounter (beyond the 300s gap) + Lunatic
    {
        "t": "2026-10-22T10:17:00+00:00",
        "persona": "pop_test_m0",
        "kind": "world_event",
        "map": "prt_fild08",
        "x": 175,
        "y": 360,
        "event": "MonsterSpotted",
        "monster": "Poring",
        "monster_id": 1001,
        "monster_x": 176,
        "monster_y": 361,
    },
    {
        "t": "2026-10-22T10:17:02+00:00",
        "persona": "pop_test_m0",
        "kind": "action_executed",
        "map": "prt_fild08",
        "x": 175,
        "y": 360,
        "action": "Attack",
        "params": {"target_id": 1001},
    },
    {
        "t": "2026-10-22T10:17:10+00:00",
        "persona": "pop_test_m0",
        "kind": "world_event",
        "map": "prt_fild08",
        "x": 175,
        "y": 360,
        "event": "MonsterSpotted",
        "monster": "Lunatic",
        "monster_id": 1002,
        "monster_x": 178,
        "monster_y": 363,
    },
    {
        "t": "2026-10-22T10:17:11+00:00",
        "persona": "pop_test_m0",
        "kind": "action_executed",
        "map": "prt_fild08",
        "x": 175,
        "y": 360,
        "action": "MoveTo",
        "params": {"x": 178, "y": 363},
    },
    # malformed line: skipped, never blanks the history
    "NOT JSON AT ALL",
]


@pytest.fixture
def traces(tmp_path: Path) -> TraceHistory:
    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()
    lines = [json.dumps(line) if isinstance(line, dict) else line for line in FIXTURE_LINES]
    (traces_dir / "pop_test_m0.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "accounts": [
            {"persona_id": "pop_test_m0", "char_name": "NyxTest", "account": "acct0"},
            {"persona_id": "pop_test_m1", "char_name": "RinceTest", "account": "acct1"},
        ]
    }
    (tmp_path / "host-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return TraceHistory(traces_dir, tmp_path / "host-manifest.json")


class TestPersonaResolution:
    def test_manifest_maps_char_name_and_persona_directly(self, traces: TraceHistory) -> None:
        assert traces.resolve_persona("NyxTest") == "pop_test_m0"
        assert traces.resolve_persona("pop_test_m0") == "pop_test_m0"
        assert traces.resolve_persona("RinceTest") == "pop_test_m1"

    def test_char_id_resolves_through_lookup_callback(self, traces: TraceHistory) -> None:
        resolve = traces.resolve_persona("150001", char_lookup=lambda _ref: "NyxTest")
        assert resolve == "pop_test_m0"

    def test_lookup_failure_is_swallowed_and_returns_none(self, traces: TraceHistory) -> None:
        def boom(_ref: str) -> str:
            raise RuntimeError("db down")

        assert traces.resolve_persona("150001", char_lookup=boom) is None

    def test_unknown_ref_is_none(self, traces: TraceHistory) -> None:
        assert traces.resolve_persona("ghost") is None
        assert traces.resolve_persona("150009", char_lookup=lambda _r: None) is None

    def test_missing_manifest_still_resolves_direct_persona_file(self, tmp_path: Path) -> None:
        traces_dir = tmp_path / "traces"
        traces_dir.mkdir()
        (traces_dir / "pop_solo.jsonl").write_text("", encoding="utf-8")
        bare = TraceHistory(traces_dir, tmp_path / "absent-manifest.json")
        assert bare.resolve_persona("pop_solo") == "pop_solo"
        assert bare.resolve_persona("NyxTest") is None


class TestQueryParsing:
    def test_clamp_limit_bounds(self) -> None:
        assert clamp_limit(-5) == 1
        assert clamp_limit(0) == 1
        assert clamp_limit(5000) == 2000
        assert clamp_limit("junk") == 200

    def test_parse_kinds_default_and_explicit(self) -> None:
        assert parse_kinds(None) == parse_kinds("") == parse_kinds("  ")
        assert parse_kinds("chat_sent,state_tick") == ("chat_sent", "state_tick")

    def test_parse_kinds_unknown_kind_is_invalid(self) -> None:
        with pytest.raises(InvalidHistoryQuery):
            parse_kinds("chat_sent,telemetry")

    def test_parse_before_accepts_z_and_naive_utc(self) -> None:
        assert parse_before("2026-10-22T10:00:00Z") == datetime(2026, 10, 22, 10, tzinfo=UTC)
        assert parse_before("2026-10-22T10:00:00") == datetime(2026, 10, 22, 10, tzinfo=UTC)
        assert parse_before(None) is None

    def test_parse_before_rejects_garbage(self) -> None:
        with pytest.raises(InvalidHistoryQuery):
            parse_before("yesterday")


class TestHistory:
    def test_newest_first_default_kinds_exclude_bulk_kinds(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m0")
        kinds = [e["kind"] for e in body["events"]]
        assert "state_tick" not in kinds  # bulk kind excluded by default
        stamps = [e["t"] for e in body["events"]]
        assert stamps == sorted(stamps, reverse=True)  # newest first
        assert body["count"] == 13
        assert body["events"][0]["kind"] == "action_executed"  # MoveTo at 10:17:11

    def test_rows_are_compact_projections(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m0", kinds=("chat_sent", "chat_heard"))
        sent = next(e for e in body["events"] if e["kind"] == "chat_sent")
        assert sent == {
            "t": T6,
            "kind": "chat_sent",
            "map": "prt_fild08",
            "x": 170,
            "y": 372,
            "summary": "[party] poring train",
            "channel": "party",
        }

    def test_kind_filtering(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m0", kinds=("goal_review",))
        assert [e["goal"] for e in body["events"]] == ["grind"]
        assert body["events"][0]["summary"] == "idle_town → grind (heartbeat)"

    def test_limit_keeps_the_newest_tail(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m0", kinds=("action_executed",), limit=2)
        assert body["count"] == 2
        assert body["events"][0]["summary"].startswith("MoveTo")  # newest action

    def test_before_cursor_pages_strictly_older(self, traces: TraceHistory) -> None:
        first = traces.history("pop_test_m0", kinds=("action_executed", "world_event"), limit=3)
        assert first["next_before"] == "2026-10-22T10:17:02+00:00"  # oldest of the page
        second = traces.history(
            "pop_test_m0",
            kinds=("action_executed", "world_event"),
            limit=3,
            before=parse_before(first["next_before"]),
        )
        assert second["count"] == 3
        oldest_new = second["events"][-1]
        assert oldest_new["t"] < first["events"][-1]["t"]
        # whole page strictly older than the cursor
        assert all(e["t"] < first["next_before"] for e in second["events"])

    def test_missing_persona_file_is_empty_never_error(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m1")
        assert body == {"events": [], "count": 0, "limit": 200, "next_before": None}

    def test_action_and_world_event_summaries(self, traces: TraceHistory) -> None:
        body = traces.history("pop_test_m0", kinds=("action_executed", "world_event"))
        summaries = {e["summary"] for e in body["events"]}
        assert "Attack target 1001" in summaries
        assert "MoveTo prt_fild08 178,363" in summaries
        assert "spotted Poring (#1001) at 174,358" in summaries
        assert "took 6 damage from #1001" in summaries

    def test_decide_response_summary_names_the_picks(self) -> None:
        row = summarize(
            {
                "t": T1,
                "kind": "decide_response",
                "answers": {"next_action": {"choice": "grind"}},
                "duration_s": 2.5,
            }
        )
        assert row["summary"] == "next_action=grind (2.5s)"


class TestCombat:
    def test_per_monster_aggregation(self, traces: TraceHistory) -> None:
        body = traces.combat("pop_test_m0")
        by_name = {m["name"]: m for m in body["monsters"]}
        assert set(by_name) == {"Poring", "Lunatic"}
        poring = by_name["Poring"]
        assert poring["encounters"] == 2  # two visits, >300s apart
        assert poring["attacks"] == 3
        assert poring["damage_taken"] == 6
        assert poring["first_seen"] == T3
        assert poring["last_seen"] == "2026-10-22T10:17:02+00:00"
        lunatic = by_name["Lunatic"]
        assert lunatic["encounters"] == 1
        assert lunatic["attacks"] == 0
        assert body["attacks_total"] == 3
        assert body["damage_taken_total"] == 6

    def test_attacks_before_first_spot_bucket_under_unknown(self, tmp_path: Path) -> None:
        traces_dir = tmp_path / "traces"
        traces_dir.mkdir()
        (traces_dir / "pop_x.jsonl").write_text(
            json.dumps(
                {
                    "t": T1,
                    "persona": "pop_x",
                    "kind": "action_executed",
                    "map": "m",
                    "action": "Attack",
                    "params": {"target_id": 77},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        body = TraceHistory(traces_dir, tmp_path / "no-manifest.json").combat("pop_x")
        assert body["monsters"][0]["name"] == "unknown #77"
        assert body["monsters"][0]["attacks"] == 1

    def test_empty_persona_is_empty_aggregation(self, traces: TraceHistory) -> None:
        assert traces.combat("pop_test_m1")["monsters"] == []


class TestPlans:
    def test_goal_and_plan_timeline_newest_first(self, traces: TraceHistory) -> None:
        body = traces.plans("pop_test_m0")
        kinds = [p["kind"] for p in body["plans"]]
        assert kinds == ["plan_authored", "goal_review"]
        plan = body["plans"][0]
        assert plan["goal"] == "farm_item"
        assert plan["targets"] == ["Poring"]
        assert plan["trigger"] == "heartbeat"
        review = body["plans"][1]
        assert review["previous_goal"] == "idle_town"

    def test_limit_applies_to_plans(self, traces: TraceHistory) -> None:
        body = traces.plans("pop_test_m0", limit=1)
        assert body["count"] == 1
        assert body["limit"] == 1
