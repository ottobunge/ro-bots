"""Run receipts store: window receipts -> newest-first summaries + detail view.

Receipts are JSON files named ``receipt-<epoch>.json`` produced by the 30-minute
playing windows. Older windows legitimately lack newer emission fields, so
every read is defensive and missing fields render as empty/None ("not supplied").
"""

from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path
from typing import Any

from dashboard_webapp.models import RunDetail, RunSummary
from dashboard_webapp.repository import DataSourceError, UnknownRunError

_RUN_TS = re.compile(r"receipt-(\d+)\.json$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# Bulky per-agent diagnostics excluded from the detail projection.
_HEAVY_AGENT_KEYS = (
    "diagnostic_samples",
    "projection_samples",
    "frame_timeline",
    "script_capture",
    "received_packets",
    "sent_packets",
    "xp_receipts",
    "pacer",
    "replan",
    "runtime_diagnostic",
    "acquired_counts",
    "chat_calls",
    "chat_failures",
    "damage_receipt_count",
    "death_receipt_count",
    "dispatched_actions",
    "transport_state",
)

_AGENT_KEYS = (
    "passed",
    "persona_id",
    "counters_basis",
    "decision_calls",
    "decision_failures",
    "frame_counters",
    "engagement_floor",
    "decisive_branch_hint",
    "final_goal",
)

_EMISSION_DEFAULTS: dict[str, Any] = {
    "phases": {},
    "gates": {},
    "decision_tail": [],
    "script_tail": [],
    "move_gate_reasons": [],
    "killcommit": {},
    "monster_names_seen": [],
    "warning_records": [],
    "xp_gain_total": None,
    "script_steps": None,
    "decision_rows": None,
    "action_rows": None,
    "decision_failures": None,
}

_META_KEYS = (
    "passed",
    "scenario",
    "operator",
    "elapsed_s",
    "mechanical_tick_seconds",
    "pacer_policy",
    "replan_policy",
    "run_scope",
    "spawn_knowledge",
    "operator_goal_override",
    "after",
)


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _headline(agents: dict[str, Any]) -> dict[str, int]:
    decisions = walks = attacks = xp = floor_met = 0
    for agent in agents.values():
        if not isinstance(agent, dict):
            continue
        decisions += _int((agent.get("decision_calls") or {}).get("count"))
        walks += _int((agent.get("frame_counters") or {}).get("walk_sends"))
        emission = agent.get("emission") or {}
        killcommit = emission.get("killcommit")
        if isinstance(killcommit, dict):
            attacks += _int(killcommit.get("attributed_attacks"))
        else:
            attacks += _int(emission.get("attributed_attacks"))
        xp_total = emission.get("xp_gain_total")
        if isinstance(xp_total, int) and not isinstance(xp_total, bool):
            xp += xp_total
        if agent.get("engagement_floor") == "met":
            floor_met += 1
    return {
        "decision_calls": decisions,
        "walk_sends": walks,
        "attributed_attacks": attacks,
        "xp_gain_total": xp,
        "engagement_floor_met": floor_met,
    }


def _started_ts(path: Path) -> float:
    match = _RUN_TS.search(path.name)
    if match:
        return float(match.group(1))
    try:
        return float(path.stat().st_mtime)
    except OSError:
        return 0.0


def _summary(path: Path, receipt: dict[str, Any]) -> RunSummary:
    agents = receipt.get("agents") or {}
    if not isinstance(agents, dict):
        agents = {}
    real_agents = {k: v for k, v in agents.items() if isinstance(v, dict)}
    return RunSummary(
        run_id=path.stem,
        file=path.name,
        started_ts=_started_ts(path),
        passed=receipt.get("passed") if isinstance(receipt.get("passed"), bool) else None,
        scenario=receipt.get("scenario") if isinstance(receipt.get("scenario"), str) else None,
        operator=receipt.get("operator") if isinstance(receipt.get("operator"), str) else None,
        elapsed_s=(
            receipt.get("elapsed_s") if isinstance(receipt.get("elapsed_s"), (int, float)) else None
        ),
        agent_count=len(real_agents),
        agents_passed=sum(1 for a in real_agents.values() if a.get("passed") is True),
        headline=_headline(real_agents),
    )


class ReceiptRunStore:
    """RunSource over a receipts glob (read-only file access)."""

    def __init__(self, receipts_glob: str) -> None:
        self._glob = receipts_glob

    def _paths(self) -> list[Path]:
        return [Path(p) for p in glob.glob(self._glob) if p.endswith(".json")]

    def list_runs(self) -> list[RunSummary]:
        runs: list[tuple[float, Path, RunSummary]] = []
        for path in self._paths():
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(receipt, dict):
                continue
            runs.append((_started_ts(path), path, _summary(path, receipt)))
        runs.sort(key=lambda item: item[0], reverse=True)
        return [summary for _, _, summary in runs]

    def run_detail(self, run_id: str) -> RunDetail:
        receipt = self._load(run_id)
        return self._project(run_id, receipt)

    def _resolve(self, run_id: str) -> Path:
        if (
            not run_id
            or "/" in run_id
            or "\\" in run_id
            or not _RUN_ID.match(run_id)
            or run_id.startswith(".")
        ):
            raise UnknownRunError(f"unknown run: {run_id}")
        directory = os.path.dirname(self._glob) or "."
        candidate = Path(directory) / f"{run_id}.json"
        if not candidate.is_file():
            raise UnknownRunError(f"unknown run: {run_id}")
        return candidate

    def _load(self, run_id: str) -> dict[str, Any]:
        path = self._resolve(run_id)
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            raise DataSourceError(f"unreadable receipt: {path.name}") from None
        if not isinstance(receipt, dict):
            raise DataSourceError(f"unreadable receipt: {path.name}")
        return receipt

    def _project(self, run_id: str, receipt: dict[str, Any]) -> RunDetail:
        raw_agents = receipt.get("agents") or {}
        if not isinstance(raw_agents, dict):
            raw_agents = {}
        agents: dict[str, dict[str, Any]] = {}
        omitted: set[str] = set()
        for name, agent in raw_agents.items():
            if not isinstance(agent, dict):
                continue
            projected: dict[str, Any] = {key: agent.get(key) for key in _AGENT_KEYS}
            raw_emission = agent.get("emission")
            emission = raw_emission if isinstance(raw_emission, dict) else {}
            projected["emission"] = {
                key: emission.get(key, default) for key, default in _EMISSION_DEFAULTS.items()
            }
            for key in _HEAVY_AGENT_KEYS:
                if key in agent:
                    omitted.add(key)
            agents[name] = projected

        meta: dict[str, Any] = {}
        for key in _META_KEYS:
            if key in receipt:
                meta[key] = receipt[key]
        interventions = receipt.get("operator_interventions")
        if isinstance(interventions, list):
            meta["operator_interventions"] = (
                interventions if len(interventions) <= 20 else {"count": len(interventions)}
            )

        return RunDetail(
            summary=_summary(Path(f"{run_id}.json"), receipt),
            agents=agents,
            meta=meta,
            omitted=sorted(omitted),
        )
