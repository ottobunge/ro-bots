"""Decision-pipeline benchmark harness: real-shape probes, honest rows.

Per configured backend the runner sends N real decide requests — the exact
``build_decision_request`` payload a mid-combat tick sends — and M chat
requests in the production chat payload shape, recording latency percentiles,
success rate, API-exposed token counts and error classes. A backend that
cannot be reached produces an ``unreachable`` row: never fabricated, never
silently dropped. Offline proof lives in ``tests/test_bench_decision.py``;
the CLI entry point is ``scripts/bench_decision.py`` (``task bench``).
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

import httpx

from robots.adapters.chat._http import chat_payload
from robots.domain.decisions import build_decision_request
from robots.domain.model import ActorRef, BotState, ChatLine, Goal

# The playing runtime's local/private Clef adapters send model "clef-flash";
# the benchmark probes the same production shape.
DECIDE_MODEL = "clef-flash"

_BENCH_MONSTERS: tuple[tuple[str, float], ...] = (
    ("Poring", 2.5),
    ("Lunatic", 4.0),
    ("Condor", 6.5),
    ("Drops", 9.5),
    ("Fabre", 12.0),
)

_CHAT_PROMPTS: tuple[str, ...] = (
    "anyone got spare red pots? my grind run went bad",
    "lf2m prontera south grind, casual pace",
    "wts +8 fire blend, pm me offers",
    "how do i get to byalan island again?",
    "thanks for the buffs party!",
    "brb feeding dog",
)


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile over an ascending-sorted sample."""
    if not sorted_values:
        msg = "percentile of empty sample"
        raise ValueError(msg)
    if not 0.0 <= q <= 1.0:
        msg = f"quantile out of bounds: {q}"
        raise ValueError(msg)
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[low]
    weight = position - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * weight


def mid_combat_state(index: int) -> BotState:
    """A realistic mid-combat grind tick: damaged, engaged, in a party.

    Probes vary deterministically by index so a 30-request run exercises 30
    distinct honest states instead of one payload replayed (synthetic
    fixed-payload benchmarks masked real outages — never go back to that).
    """
    rng = random.Random(4242 + index)
    monsters = tuple(
        ActorRef(
            id=15000 + 7 * index + slot,
            name=name,
            kind="monster",
            distance=round(distance + rng.uniform(-0.5, 2.0), 1),
        )
        for slot, (name, distance) in enumerate(_BENCH_MONSTERS)
    )
    return BotState(
        name=f"BenchBot{index:02d}",
        job="Swordsman",
        base_level=42,
        hp=620 + (index % 3) * 15,
        max_hp=1050,
        sp=38 + (index % 4) * 6,
        max_sp=92,
        map_name="prt_fild08",
        x=118 + index % 7,
        y=71 + (index * 3) % 11,
        goal=Goal.GRIND,
        in_party=True,
        nearby=monsters,
        inventory={
            "Jellopy": 31 + index % 5,
            "Red Potion": 3 + index % 2,
            "Sticky Mucus": 7,
        },
        pending_invites=(),
        recent_chat=(
            ChatLine(channel="party", sender="HealerMira", text="pulling one more", at=91.0),
            ChatLine(channel="public", sender="MerchantTan", text="wts rings pm me", at=93.5),
        ),
    )


def build_decide_probe(index: int) -> dict[str, Any]:
    """The exact production SystemOne payload for probe ``index``."""
    return build_decision_request(mid_combat_state(index))


def build_chat_probe(index: int) -> dict[str, Any]:
    """The exact production chat payload for probe ``index``."""
    return chat_payload(_CHAT_PROMPTS[index % len(_CHAT_PROMPTS)])


# ---- backend configuration -------------------------------------------------

_BACKEND_KINDS = ("systemone", "workers", "chat")
_PROBE_PHASES = ("decide", "chat")
_DECIDE_KINDS = frozenset({"systemone", "workers"})
_CHAT_KINDS = frozenset({"systemone", "chat"})
_SYSTEMONE_PATH = "/v1/systemone"
_CHAT_PATH = "/v1/chat/completions"
_UNREACHABLE_CLASSES = frozenset({"connection_error", "timeout"})


@dataclass(frozen=True, slots=True)
class BackendConfig:
    """One benchmark target from the backends JSON config.

    ``probes`` selects the phases run against this backend: ``"decide"`` hits
    ``{base_url}/v1/systemone`` (kind ``systemone``) or the full Workers AI
    run URL (kind ``workers``); ``"chat"`` hits
    ``{base_url}/v1/chat/completions``. Defaults: decide for
    systemone/workers, chat for chat.
    """

    name: str
    base_url: str
    kind: str
    probes: tuple[str, ...] | None = None

    def phases(self) -> tuple[str, ...]:
        if self.probes is not None:
            return self.probes
        return ("chat",) if self.kind == "chat" else ("decide",)


def _expand_placeholders(value: str, env: Mapping[str, str]) -> str:
    """Expand ``$VAR`` placeholders; unknown vars survive for a graceful skip."""
    try:
        return Template(value).substitute(env)
    except KeyError:
        return value


def _parse_probes(entry: dict[str, Any]) -> tuple[str, ...] | None:
    probes = entry.get("probes")
    if probes is None:
        return None
    if isinstance(probes, list) and probes and all(p in _PROBE_PHASES for p in probes):
        return tuple(probes)
    msg = f"backend {entry.get('name')!r}: probes must be a non-empty list of {_PROBE_PHASES}"
    raise ValueError(msg)


def load_backends(
    path: str | Path, *, environ: Mapping[str, str] | None = None
) -> list[BackendConfig]:
    """Read the benchmark backends config: name, base_url, kind, optional probes."""
    env = os.environ if environ is None else environ
    raw = json.loads(Path(path).read_text())
    entries = raw.get("backends") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        msg = f"benchmark config {path} needs a 'backends' list"
        raise ValueError(msg)
    return [_parse_backend(entry, env) for entry in entries]


def _parse_backend(entry: Any, env: Mapping[str, str]) -> BackendConfig:
    if not isinstance(entry, dict):
        msg = f"backend entry must be an object: {entry!r}"
        raise ValueError(msg)
    name, base_url, kind = entry.get("name"), entry.get("base_url"), entry.get("kind")
    if not (isinstance(name, str) and isinstance(base_url, str) and isinstance(kind, str)):
        msg = f"backend entry needs string name/base_url/kind: {entry!r}"
        raise ValueError(msg)
    if kind not in _BACKEND_KINDS:
        msg = f"unknown backend kind: {kind}"
        raise ValueError(msg)
    return BackendConfig(
        name=name,
        base_url=_expand_placeholders(base_url, env),
        kind=kind,
        probes=_parse_probes(entry),
    )


# ---- probe execution -------------------------------------------------------


@dataclass(slots=True)
class _PhaseMetrics:
    requested: int
    success: int = 0
    failed: int = 0
    walls: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)
    tokens_in: int | None = None
    tokens_out: int | None = None

    def record_error(self, error_class: str) -> None:
        self.failed += 1
        self.errors[error_class] = self.errors.get(error_class, 0) + 1

    def record_success(self, wall: float, body: dict[str, Any] | None, envelope: str) -> None:
        self.success += 1
        self.walls.append(wall)
        if body is None:
            return
        tokens_in, tokens_out = _extract_usage(body, envelope=envelope)
        if tokens_in is not None:
            self.tokens_in = tokens_in
        if tokens_out is not None:
            self.tokens_out = tokens_out

    def to_row(self) -> dict[str, Any]:
        walls = sorted(self.walls)
        return {
            "n": self.requested,
            "success": self.success,
            "failed": self.failed,
            "p50_s": round(percentile(walls, 0.5), 3) if walls else None,
            "p90_s": round(percentile(walls, 0.9), 3) if walls else None,
            "max_s": round(walls[-1], 3) if walls else None,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "errors": dict(self.errors),
        }


def classify_http_error(exc: httpx.HTTPError) -> str:
    """Map transport failures to the stable row error classes."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection_error"
    return "http_status"


def _run_probe(
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    validate: Callable[[dict[str, Any]], bool],
) -> tuple[float, str | None, dict[str, Any] | None]:
    """One timed probe: (wall_seconds, error_class or None, validated body)."""
    start = time.perf_counter()
    try:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPError as exc:
        return time.perf_counter() - start, classify_http_error(exc), None
    except ValueError:
        return time.perf_counter() - start, "malformed_response", None
    wall = time.perf_counter() - start
    if not isinstance(body, dict) or not validate(body):
        return wall, "malformed_response", None
    return wall, None, body


def _run_phase(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    *,
    payloads: list[dict[str, Any]],
    validate: Callable[[dict[str, Any]], bool],
    envelope: str,
) -> tuple[_PhaseMetrics, str | None]:
    """Run one probe phase; stop early only when first contact proves unreachability.

    Latencies describe successful responses only; failures count into
    ``failed``/``errors`` and the row's success rate instead.
    """
    metrics = _PhaseMetrics(requested=len(payloads))
    for position, payload in enumerate(payloads):
        wall, error, body = _run_probe(client, url, payload, headers, validate)
        if error is None:
            metrics.record_success(wall, body, envelope)
            continue
        metrics.record_error(error)
        if position == 0 and error in _UNREACHABLE_CLASSES:
            metrics.requested = position + 1
            return metrics, error
    return metrics, None


def _validate_plain_decide(body: dict[str, Any]) -> bool:
    return isinstance(body.get("answers"), dict)


def _validate_workers_decide(body: dict[str, Any]) -> bool:
    result = body.get("result")
    return (
        body.get("success") is not False
        and isinstance(result, dict)
        and isinstance(result.get("answers"), dict)
    )


def _validate_chat(body: dict[str, Any]) -> bool:
    try:
        content = body["choices"][0]["message"]["content"]
    except KeyError, IndexError, TypeError:
        return False
    return isinstance(content, str) and bool(content.strip())


_USAGE_IN_KEYS = ("prompt_tokens", "input_tokens")
_USAGE_OUT_KEYS = ("completion_tokens", "output_tokens")


def _extract_usage(body: dict[str, Any], *, envelope: str) -> tuple[int | None, int | None]:
    """Token counts the API actually exposed; (None, None) when it does not."""
    node: Any = body.get("result") if envelope == "workers" else body
    usage = node.get("usage") if isinstance(node, dict) else None
    if not isinstance(usage, dict):
        return None, None
    tokens_in = next(
        (usage[key] for key in _USAGE_IN_KEYS if isinstance(usage.get(key), int)), None
    )
    tokens_out = next(
        (usage[key] for key in _USAGE_OUT_KEYS if isinstance(usage.get(key), int)), None
    )
    return tokens_in, tokens_out


def _resolve_endpoint(
    config: BackendConfig, environ: Mapping[str, str]
) -> tuple[str, dict[str, str], str | None]:
    """(probe URL, auth headers, missing-credential reason)."""
    if config.kind == "workers":
        token = environ.get("CLOUDFLARE_API_TOKEN")
        if not token or "$" in config.base_url:
            return config.base_url, {}, "missing_credentials"
        return config.base_url, {"Authorization": f"Bearer {token}"}, None
    if config.kind == "systemone":
        return config.base_url.rstrip("/") + _SYSTEMONE_PATH, {}, None
    return config.base_url.rstrip("/") + _CHAT_PATH, {}, None


def _response_contract(kind: str) -> tuple[Callable[[dict[str, Any]], bool], str]:
    """(response validator, usage envelope) for a backend kind."""
    if kind == "workers":
        return _validate_workers_decide, "workers"
    return _validate_plain_decide, "plain"


def _decide_payloads(count: int) -> list[dict[str, Any]]:
    payloads = [build_decide_probe(index) for index in range(count)]
    for payload in payloads:
        payload["model"] = DECIDE_MODEL
    return payloads


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _unreachable_row(config: BackendConfig, error_class: str, timestamp: str) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "backend": config.name,
        "kind": config.kind,
        "status": "unreachable",
        "error_class": error_class,
        "decide": None,
        "chat": None,
        "success_rate": None,
    }


def _decide_phase(
    client: httpx.Client,
    config: BackendConfig,
    url: str,
    *,
    headers: dict[str, str],
    validate: Callable[[dict[str, Any]], bool],
    envelope: str,
    decide_n: int,
    phases: tuple[str, ...],
) -> tuple[dict[str, Any] | None, int, int, str | None]:
    """Run the decide phase: (row, successes, attempted, unreachable_class)."""
    if "decide" not in phases or config.kind not in _DECIDE_KINDS:
        return None, 0, 0, None
    metrics, unreachable = _run_phase(
        client,
        url,
        headers,
        payloads=_decide_payloads(decide_n),
        validate=validate,
        envelope=envelope,
    )
    return metrics.to_row(), metrics.success, metrics.requested, unreachable


def _chat_phase(
    client: httpx.Client,
    config: BackendConfig,
    headers: dict[str, str],
    chat_n: int,
    phases: tuple[str, ...],
) -> tuple[dict[str, Any] | None, int, int, str | None]:
    """Run the chat phase: (row, successes, attempted, unreachable_class)."""
    if "chat" not in phases or config.kind not in _CHAT_KINDS:
        return None, 0, 0, None
    metrics, unreachable = _run_phase(
        client,
        config.base_url.rstrip("/") + _CHAT_PATH,
        headers,
        payloads=[build_chat_probe(index) for index in range(chat_n)],
        validate=_validate_chat,
        envelope="plain",
    )
    return metrics.to_row(), metrics.success, metrics.requested, unreachable


def bench_backend(
    config: BackendConfig,
    *,
    decide_n: int = 30,
    chat_n: int = 10,
    client_factory: Callable[[], httpx.Client] | None = None,
    environ: Mapping[str, str] | None = None,
    now: Callable[[], str] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Benchmark one backend; return its row (never raises for a dead backend)."""
    env = os.environ if environ is None else environ
    timestamp = now() if now is not None else _utc_now_iso()
    url, headers, missing = _resolve_endpoint(config, env)
    if missing is not None:
        return _unreachable_row(config, missing, timestamp)
    validate, envelope = _response_contract(config.kind)

    client = client_factory() if client_factory is not None else httpx.Client(timeout=timeout)
    try:
        phases = config.phases()
        decide_row, successes, attempted, unreachable = _decide_phase(
            client,
            config,
            url,
            headers=headers,
            validate=validate,
            envelope=envelope,
            decide_n=decide_n,
            phases=phases,
        )
        if unreachable is not None:
            return _unreachable_row(config, unreachable, timestamp)
        chat_row, chat_success, chat_attempted, chat_unreachable = _chat_phase(
            client, config, headers, chat_n, phases
        )
        if chat_unreachable is not None and decide_row is None:
            return _unreachable_row(config, chat_unreachable, timestamp)
    finally:
        client.close()

    total_success = successes + chat_success
    total_attempted = attempted + chat_attempted
    return {
        "timestamp": timestamp,
        "backend": config.name,
        "kind": config.kind,
        "status": "ok",
        "decide": decide_row,
        "chat": chat_row,
        "success_rate": round(total_success / total_attempted, 4) if total_attempted else None,
    }


def run_benchmark(
    configs: list[BackendConfig],
    *,
    decide_n: int = 30,
    chat_n: int = 10,
    client_factory: Callable[[], httpx.Client] | None = None,
    environ: Mapping[str, str] | None = None,
    now: Callable[[], str] | None = None,
    timeout: float = 120.0,
) -> list[dict[str, Any]]:
    """Benchmark every configured backend; one honest row each."""
    return [
        bench_backend(
            config,
            decide_n=decide_n,
            chat_n=chat_n,
            client_factory=client_factory,
            environ=environ,
            now=now,
            timeout=timeout,
        )
        for config in configs
    ]


# ---- persistence and reporting ---------------------------------------------


def benchmark_path(directory: str | Path, day: str | None = None) -> Path:
    """The append-only JSONL file for one run day: ``decide-<date>.jsonl``."""
    stamp = day or datetime.now(UTC).date().isoformat()
    return Path(directory) / f"decide-{stamp}.jsonl"


def append_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """Append rows as JSON lines, creating the directory and file as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    """Parse every recorded row from a benchmark JSONL file."""
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def latest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The newest row per backend, in first-seen backend order."""
    newest: dict[str, dict[str, Any]] = {}
    for row in rows:
        newest[row["backend"]] = row
    return list(newest.values())


def _seconds(value: Any) -> str:
    return "—" if value is None else f"{value:.2f}s"


def _percent(value: Any) -> str:
    return "—" if value is None else f"{round(value * 100)}%"


def _report_row(row: dict[str, Any]) -> str:
    if row.get("status") == "unreachable":
        note = f"unreachable ({row.get('error_class')})"
        return f"| {row['backend']} | {note} | — | — | — |"
    decide = row.get("decide") or {}
    chat = row.get("chat") or {}
    cells = (
        row["backend"],
        _seconds(decide.get("p50_s")),
        _seconds(decide.get("p90_s")),
        _seconds(chat.get("p50_s")),
        _percent(row.get("success_rate")),
    )
    return "| " + " | ".join(cells) + " |"


def render_report(rows: list[dict[str, Any]]) -> str:
    """Render rows as the operator's markdown comparison table."""
    lines = [
        "# Decision pipeline benchmark (latest run)",
        "",
        "| backend | decide p50 | decide p90 | chat p50 | success |",
        "|---|---|---|---|---|",
        *(_report_row(row) for row in rows),
    ]
    return "\n".join(lines) + "\n"
