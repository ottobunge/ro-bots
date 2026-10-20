"""Receipt store tests: glob -> newest-first summaries with headline counters,
curated detail projection (tails, gates, move-gate reasons), path safety, and
tolerance for schema drift between window receipts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_webapp.repository import UnknownRunError
from dashboard_webapp.runs_store import ReceiptRunStore


def _agent(
    *,
    passed: bool = True,
    decisions: int = 21,
    walks: int = 4,
    attacks: int | None = 2,
    xp: int | None = 130,
    floor: str = "met",
) -> dict:
    emission: dict = {
        "phases": {"authored": 25, "dispatched": 25},
        "gates": {},
        "xp_gain_total": xp,
        "move_gate_reasons": ["no_attackable_in_reach"],
        "decision_tail": [{"event": "Heartbeat"}],
        "script_tail": [{"step": "approach"}],
        "killcommit": {
            "attributed_attacks": attacks,
            "bot_dealt_damage": 55,
            "attacked_target_deaths": 1,
        },
    }
    if attacks is None:  # old receipts carry no killcommit at all
        emission.pop("killcommit")
        emission.pop("move_gate_reasons")
        emission.pop("decision_tail")
        emission.pop("script_tail")
        emission.pop("xp_gain_total")
    return {
        "passed": passed,
        "persona_id": "host_fixture_0",
        "counters_basis": "observed",
        "decision_calls": {"count": decisions, "verdict": "observed"},
        "frame_counters": {
            "own_position_ingests": 100,
            "walk_sends": walks,
            "attackable_actors_max": 3,
        },
        "engagement_floor": floor,
        "emission": emission,
        "diagnostic_samples": [{"t": 1.0, "bulk": "x" * 64}],
    }


def _write_receipt(dir_: Path, ts: int, agents: dict, **meta) -> str:
    run_id = f"receipt-{ts}"
    payload = {
        "passed": False,
        "scenario": "operator_controlled_grind",
        "operator": "playing-grind-emission",
        "elapsed_s": 1800.0,
        "agents": agents,
        **meta,
    }
    (dir_ / f"{run_id}.json").write_text(json.dumps(payload))
    return run_id


@pytest.fixture
def receipts_dir(tmp_path: Path) -> Path:
    return tmp_path / "evidence"


def test_list_newest_first_and_ignores_non_receipt_files(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    _write_receipt(receipts_dir, 100, {"a": _agent()})
    _write_receipt(receipts_dir, 300, {"a": _agent()})
    (receipts_dir / "not-a-receipt.json").write_text("{}")
    (receipts_dir / "notes.txt").write_text("ignore me")

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    runs = store.list_runs()

    assert [r.run_id for r in runs] == ["receipt-300", "receipt-100"]
    assert runs[0].file == "receipt-300.json"
    assert runs[0].started_ts == 300.0


def test_headline_counters_sum_across_agents(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    _write_receipt(
        receipts_dir,
        200,
        {
            "host_fixture_0": _agent(decisions=10, walks=2, attacks=1, xp=50),
            "host_fixture_1": _agent(decisions=11, walks=3, attacks=0, xp=80, floor="not_met"),
        },
    )

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    (run,) = store.list_runs()

    assert run.agent_count == 2
    assert run.agents_passed == 2
    assert run.passed is False
    assert run.headline == {
        "decision_calls": 21,
        "walk_sends": 5,
        "attributed_attacks": 1,
        "xp_gain_total": 130,
        "engagement_floor_met": 1,
    }


def test_empty_and_malformed_agents_do_not_crash_listing(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    _write_receipt(receipts_dir, 400, {})
    (receipts_dir / "receipt-401.json").write_text("{not json")

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    runs = store.list_runs()
    assert [r.run_id for r in runs] == ["receipt-400"]
    assert runs[0].headline["decision_calls"] == 0
    assert runs[0].passed is None or runs[0].passed is False


def test_detail_projection_carries_tails_gates_and_move_reasons(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    run_id = _write_receipt(receipts_dir, 500, {"host_fixture_0": _agent()}, run_scope="window-1")

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    detail = store.run_detail(run_id)

    agent = detail.agents["host_fixture_0"]
    assert agent["passed"] is True
    assert agent["decision_calls"] == {"count": 21, "verdict": "observed"}
    assert agent["frame_counters"]["walk_sends"] == 4
    assert agent["engagement_floor"] == "met"
    emission = agent["emission"]
    assert emission["decision_tail"] == [{"event": "Heartbeat"}]
    assert emission["script_tail"] == [{"step": "approach"}]
    assert emission["move_gate_reasons"] == ["no_attackable_in_reach"]
    assert emission["gates"] == {}
    assert emission["killcommit"]["bot_dealt_damage"] == 55
    assert emission["xp_gain_total"] == 130
    assert detail.meta["run_scope"] == "window-1"


def test_detail_of_old_receipt_defaults_missing_fields(receipts_dir: Path) -> None:
    """Pre-emission receipts (no tails/killcommit) must render with defaults."""
    receipts_dir.mkdir(parents=True)
    old_agent = _agent(attacks=None)
    _write_receipt(receipts_dir, 600, {"host_fixture_0": old_agent})

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    detail = store.run_detail("receipt-600")
    emission = detail.agents["host_fixture_0"]["emission"]

    assert emission["decision_tail"] == []
    assert emission["script_tail"] == []
    assert emission["move_gate_reasons"] == []
    assert emission["killcommit"] == {}
    assert emission["xp_gain_total"] is None


def test_detail_drops_bulky_samples(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    _write_receipt(receipts_dir, 700, {"host_fixture_0": _agent()})

    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    detail = store.run_detail("receipt-700")

    assert "diagnostic_samples" not in detail.agents["host_fixture_0"]
    assert "diagnostic_samples" in detail.omitted


def test_unknown_run_id_raises_without_path_traversal(receipts_dir: Path) -> None:
    receipts_dir.mkdir(parents=True)
    _write_receipt(receipts_dir, 800, {"a": _agent()})
    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))

    with pytest.raises(UnknownRunError):
        store.run_detail("receipt-999")
    for evil in ("../evil", "sub/dir", "..", ".hidden"):
        with pytest.raises(UnknownRunError):
            store.run_detail(evil)
    # Nothing outside the glob was touched.
    assert sorted(p.name for p in receipts_dir.iterdir()) == ["receipt-800.json"]


def test_missing_dir_yields_no_runs(receipts_dir: Path) -> None:
    store = ReceiptRunStore(str(receipts_dir / "receipt-*.json"))
    assert store.list_runs() == []
