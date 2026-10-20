"""Offline proof for the decision-pipeline benchmark harness.

No live backend calls: HTTP doubles ride ``httpx.MockTransport``; latency
math, row schema, skip-on-unreachable, probe construction and report
rendering are all proven offline.
"""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from robots.adapters.chat._http import chat_payload
from robots.bench import (
    BackendConfig,
    append_rows,
    bench_backend,
    benchmark_path,
    build_chat_probe,
    build_decide_probe,
    latest_rows,
    load_backends,
    mid_combat_state,
    percentile,
    read_rows,
    render_report,
    run_benchmark,
)
from robots.domain.decisions import build_decision_request

FAKE_NOW = "2026-10-20T12:00:00+00:00"

ROW_KEYS = {"timestamp", "backend", "kind", "status", "decide", "chat", "success_rate"}
UNREACHABLE_ROW_KEYS = ROW_KEYS | {"error_class"}
METRIC_KEYS = {
    "n",
    "success",
    "failed",
    "p50_s",
    "p90_s",
    "max_s",
    "tokens_in",
    "tokens_out",
    "errors",
}


def mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)


def decide_body() -> dict[str, Any]:
    return {
        "answers": {"next_action": "grind"},
        "usage": {"prompt_tokens": 2210, "completion_tokens": 90},
    }


def chat_body() -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": "anyone near prt south?"}}],
        "usage": {"prompt_tokens": 48, "completion_tokens": 17},
    }


class TestLatencyMath:
    def test_percentile_interpolates_linearly(self) -> None:
        assert percentile([10.0, 20.0, 30.0, 40.0], 0.5) == 25.0
        assert percentile([10.0, 20.0, 30.0, 40.0], 0.9) == 37.0

    def test_percentile_single_value_and_bounds(self) -> None:
        assert percentile([5.0], 0.9) == 5.0
        assert percentile([1.0, 2.0], 0.0) == 1.0
        assert percentile([1.0, 2.0], 1.0) == 2.0

    def test_percentile_empty_sample_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            percentile([], 0.5)

    def test_percentile_rejects_out_of_bounds_quantile(self) -> None:
        with pytest.raises(ValueError, match="out of bounds"):
            percentile([1.0, 2.0], 1.5)


class TestRealShapeProbes:
    def test_decide_probe_is_exact_build_decision_request_output(self) -> None:
        index = 3
        payload = build_decide_probe(index)
        assert payload == build_decision_request(mid_combat_state(index))

    def test_decide_probe_carries_systemone_envelope(self) -> None:
        payload = build_decide_probe(0)
        assert set(payload) == {"model", "state", "questions"}
        assert payload["model"] == "clef"
        assert isinstance(payload["questions"], dict)
        assert payload["questions"]

    def test_mid_combat_state_is_mid_combat(self) -> None:
        state = mid_combat_state(1)
        assert state.nearby_monsters, "a mid-combat tick sees monsters"
        assert 0 < state.hp < state.max_hp, "mid-combat HP is damaged, not fresh"
        assert state.in_party, "the benchmark party leg is engaged"
        assert state.goal == state.goal.GRIND

    def test_probes_are_deterministic_and_vary_by_index(self) -> None:
        assert build_decide_probe(2) == build_decide_probe(2)
        assert build_decide_probe(2) != build_decide_probe(9)

    def test_chat_probe_is_the_production_chat_payload_shape(self) -> None:
        payload = build_chat_probe(0)
        assert payload == chat_payload(payload["messages"][1]["content"])
        assert set(payload) == {"messages", "max_tokens", "temperature"}
        assert payload["messages"][0]["role"] == "system"


class TestRunner:
    def test_ok_row_records_counts_latencies_tokens_and_wire_shape(self) -> None:
        wire: list[tuple[str, dict[str, Any], dict[str, str]]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = chat_body() if request.url.path == "/v1/chat/completions" else decide_body()
            wire.append((request.url.path, json.loads(request.content), dict(request.headers)))
            return httpx.Response(200, json=body)

        config = BackendConfig(
            name="bench-local",
            base_url="http://bench.test",
            kind="systemone",
            probes=("decide", "chat"),
        )
        row = bench_backend(
            config,
            decide_n=3,
            chat_n=2,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )

        assert set(row) == ROW_KEYS
        assert row["timestamp"] == FAKE_NOW
        assert row["backend"] == "bench-local"
        assert row["kind"] == "systemone"
        assert row["status"] == "ok"
        assert row["success_rate"] == 1.0
        assert row["decide"] is not None
        assert set(row["decide"]) == METRIC_KEYS
        assert row["decide"]["n"] == 3
        assert row["decide"]["success"] == 3
        assert row["decide"]["failed"] == 0
        assert row["decide"]["tokens_in"] == 2210
        assert row["decide"]["tokens_out"] == 90
        assert row["decide"]["errors"] == {}
        assert 0 <= row["decide"]["p50_s"] <= row["decide"]["p90_s"] <= row["decide"]["max_s"]
        assert row["chat"] is not None
        assert set(row["chat"]) == METRIC_KEYS
        assert row["chat"]["n"] == 2
        assert row["chat"]["success"] == 2
        assert row["chat"]["tokens_in"] == 48
        # Production wire shape survives the harness: real payload, playing model override.
        decide_wire = [w for w in wire if w[0] == "/v1/systemone"]
        assert len(decide_wire) == 3
        assert set(decide_wire[0][1]) == {"model", "state", "questions"}
        assert decide_wire[0][1]["model"] == "clef-flash"
        chat_wire = [w for w in wire if w[0] == "/v1/chat/completions"]
        assert len(chat_wire) == 2
        assert set(chat_wire[0][1]) == {"messages", "max_tokens", "temperature"}

    def test_decide_only_backend_leaves_chat_phase_absent(self) -> None:
        config = BackendConfig(
            name="bench-decide",
            base_url="http://bench.test",
            kind="systemone",
            probes=("decide",),
        )
        row = bench_backend(
            config,
            decide_n=1,
            chat_n=5,
            client_factory=lambda: mock_client(
                lambda _request: httpx.Response(200, json=decide_body())
            ),
            now=lambda: FAKE_NOW,
        )
        assert row["decide"]["n"] == 1
        assert row["chat"] is None

    @pytest.mark.parametrize(
        ("exc", "error_class"),
        [
            (
                httpx.ConnectError("refused", request=httpx.Request("POST", "http://x")),
                "connection_error",
            ),
            (httpx.ReadTimeout("slow", request=httpx.Request("POST", "http://x")), "timeout"),
        ],
    )
    def test_unreachable_backend_is_skipped_with_honest_row(self, exc, error_class) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            raise exc

        config = BackendConfig(name="down-backend", base_url="http://down.test", kind="systemone")
        row = bench_backend(
            config,
            decide_n=5,
            chat_n=3,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )

        assert set(row) == UNREACHABLE_ROW_KEYS
        assert row["status"] == "unreachable"
        assert row["error_class"] == error_class
        assert row["decide"] is None
        assert row["chat"] is None
        assert row["success_rate"] is None
        assert calls == ["/v1/systemone"], "skip after first contact, no probe storm"

    def test_missing_workers_credentials_skip_the_row_gracefully(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
            msg = "no request may be sent without credentials"
            raise AssertionError(msg)

        config = BackendConfig(
            name="cloudflare-clef-flash",
            base_url="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run/@cf/cloudflare/clef-flash",
            kind="workers",
        )
        row = bench_backend(
            config,
            decide_n=2,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            environ={},
            now=lambda: FAKE_NOW,
        )
        assert row["status"] == "unreachable"
        assert row["error_class"] == "missing_credentials"
        assert row["decide"] is None

    def test_workers_backend_sends_bearer_token_and_reads_envelope(self) -> None:
        headers_seen: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            headers_seen.append(dict(request.headers))
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "answers": {"next_action": "grind"},
                        "usage": {"input_tokens": 2210},
                    },
                },
            )

        config = BackendConfig(
            name="cloudflare-clef-flash",
            base_url="https://api.cloudflare.com/client/v4/accounts/acct/ai/run/@cf/cloudflare/clef-flash",
            kind="workers",
        )
        row = bench_backend(
            config,
            decide_n=2,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            environ={"CLOUDFLARE_API_TOKEN": "test-only-token"},
            now=lambda: FAKE_NOW,
        )
        assert headers_seen[0].get("authorization") == "Bearer test-only-token"
        assert row["status"] == "ok"
        assert row["decide"]["tokens_in"] == 2210
        assert row["decide"]["tokens_out"] is None, "never fabricate unexposed token counts"

    def test_partial_failures_record_error_classes_and_success_rate(self) -> None:
        responses: list[httpx.Response | Exception] = [
            httpx.Response(200, json=decide_body()),
            httpx.Response(500, text="boom"),
            httpx.Response(200, json={"nope": 1}),
            httpx.Response(200, json=decide_body()),
            httpx.Response(200, json=chat_body()),
        ]
        index = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal index
            outcome = responses[index]
            index += 1
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        config = BackendConfig(
            name="flaky",
            base_url="http://flaky.test",
            kind="systemone",
            probes=("decide", "chat"),
        )
        row = bench_backend(
            config,
            decide_n=4,
            chat_n=1,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert row["decide"]["success"] == 2
        assert row["decide"]["failed"] == 2
        assert row["decide"]["errors"] == {"http_status": 1, "malformed_response": 1}
        assert row["chat"]["success"] == 1
        assert row["success_rate"] == 0.6
        assert row["status"] == "ok"

    def test_zero_success_leaves_latencies_null_not_zero(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        config = BackendConfig(name="junk", base_url="http://junk.test", kind="chat")
        row = bench_backend(
            config,
            decide_n=0,
            chat_n=2,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert row["decide"] is None
        assert row["chat"]["success"] == 0
        assert row["chat"]["p50_s"] is None
        assert row["chat"]["max_s"] is None
        assert row["chat"]["errors"] == {"malformed_response": 2}
        assert row["success_rate"] == 0.0

    def test_non_json_body_is_malformed_response_not_a_crash(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>gateway noise</html>")

        config = BackendConfig(name="noise", base_url="http://noise.test", kind="systemone")
        row = bench_backend(
            config,
            decide_n=2,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert row["decide"]["errors"] == {"malformed_response": 2}

    def test_decide_success_without_usage_leaves_tokens_null(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"answers": {"next_action": "grind"}})

        config = BackendConfig(name="nolegs", base_url="http://nolegs.test", kind="systemone")
        row = bench_backend(
            config,
            decide_n=1,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert row["decide"]["tokens_in"] is None
        assert row["decide"]["tokens_out"] is None

    def test_workers_rejection_is_an_error_not_a_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"success": False, "errors": [{"code": 7301}]})

        config = BackendConfig(
            name="cloudflare-clef-flash",
            base_url="https://api.cloudflare.com/client/v4/accounts/acct/ai/run/@cf/cloudflare/clef-flash",
            kind="workers",
        )
        row = bench_backend(
            config,
            decide_n=1,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            environ={"CLOUDFLARE_API_TOKEN": "test-only-token"},
            now=lambda: FAKE_NOW,
        )
        assert row["decide"]["success"] == 0
        assert row["decide"]["errors"] == {"malformed_response": 1}

    def test_chat_phase_unreachable_after_decide_ok_keeps_decide_stats(self) -> None:
        refusal = "refused"

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/chat/completions":
                raise httpx.ConnectError(refusal, request=request)
            return httpx.Response(200, json=decide_body())

        config = BackendConfig(
            name="half-up",
            base_url="http://half.test",
            kind="systemone",
            probes=("decide", "chat"),
        )
        row = bench_backend(
            config,
            decide_n=1,
            chat_n=2,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert row["status"] == "ok", "decide answered; the backend is not unreachable"
        assert row["decide"]["success"] == 1
        assert row["chat"]["failed"] == 1
        assert row["chat"]["errors"] == {"connection_error": 1}
        assert row["success_rate"] == 0.5


class TestConfigLoad:
    def write_config(self, tmp_path, payload: str) -> str:
        config_path = tmp_path / "backends.json"
        config_path.write_text(payload)
        return str(config_path)

    def test_malformed_config_entries_are_rejected(self, tmp_path) -> None:
        probes_entry = '{"name": "x", "base_url": "http://x", "kind": "systemone", "probes": []}'
        malformed = [
            "[]",
            '{"backends": [42]}',
            '{"backends": [{"name": "x", "base_url": 3, "kind": "systemone"}]}',
            f'{{"backends": [{probes_entry}]}}',
        ]
        expected = [
            "needs a 'backends' list",
            "must be an object",
            "needs string name",
            "probes must be",
        ]
        for payload, match in zip(malformed, expected, strict=True):
            path = tmp_path / f"{payload.encode().hex()}.json"
            path.write_text(payload)
            with pytest.raises(ValueError, match=match):
                load_backends(str(path), environ={})

    def test_load_backends_reads_names_urls_kinds_and_expands_env(self, tmp_path) -> None:
        config_path = self.write_config(
            tmp_path,
            json.dumps(
                {
                    "backends": [
                        {
                            "name": "local-rocm",
                            "base_url": "http://127.0.0.1:8093",
                            "kind": "systemone",
                        },
                        {
                            "name": "cloudflare-clef-flash",
                            "base_url": "https://api.cloudflare.com/client/v4/accounts/"
                            "$CLOUDFLARE_ACCOUNT_ID/ai/run/@cf/cloudflare/clef-flash",
                            "kind": "workers",
                            "probes": ["decide"],
                        },
                        {
                            "name": "chat-qwen3-4b",
                            "base_url": "http://127.0.0.1:8300",
                            "kind": "chat",
                        },
                    ]
                }
            ),
        )
        backends = load_backends(config_path, environ={"CLOUDFLARE_ACCOUNT_ID": "cafe1234"})
        assert [b.name for b in backends] == [
            "local-rocm",
            "cloudflare-clef-flash",
            "chat-qwen3-4b",
        ]
        assert backends[0].kind == "systemone"
        assert "$CLOUDFLARE_ACCOUNT_ID" not in backends[1].base_url
        assert "accounts/cafe1234/" in backends[1].base_url
        assert backends[1].probes == ("decide",)
        assert backends[2].probes is None
        assert backends[2].phases() == ("chat",), "chat backends default to chat probes only"

    def test_unexpanded_placeholder_survives_for_graceful_skip(self, tmp_path) -> None:
        config_path = self.write_config(
            tmp_path,
            json.dumps(
                {
                    "backends": [
                        {
                            "name": "cloudflare-clef-flash",
                            "base_url": "https://api.cloudflare.com/client/v4/accounts/"
                            "$CLOUDFLARE_ACCOUNT_ID/ai/run/@cf/cloudflare/clef-flash",
                            "kind": "workers",
                        }
                    ]
                }
            ),
        )
        (backends,) = load_backends(config_path, environ={})
        assert "$CLOUDFLARE_ACCOUNT_ID" in backends.base_url

    def test_unknown_kind_rejected_at_load(self, tmp_path) -> None:
        config_path = self.write_config(
            tmp_path,
            json.dumps(
                {
                    "backends": [
                        {"name": "weird", "base_url": "http://x.test", "kind": "smoke_signals"}
                    ]
                }
            ),
        )
        with pytest.raises(ValueError, match="unknown backend kind"):
            load_backends(config_path, environ={})


def ok_row(backend: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "timestamp": FAKE_NOW,
        "backend": backend,
        "kind": "systemone",
        "status": "ok",
        "decide": {
            "n": 30,
            "success": 30,
            "failed": 0,
            "p50_s": 0.9,
            "p90_s": 1.3,
            "max_s": 1.85,
            "tokens_in": 2210,
            "tokens_out": 90,
            "errors": {},
        },
        "chat": None,
        "success_rate": 1.0,
    }
    row.update(overrides)
    return row


def unreachable_row(backend: str, error_class: str = "connection_error") -> dict[str, Any]:
    return {
        "timestamp": FAKE_NOW,
        "backend": backend,
        "kind": "systemone",
        "status": "unreachable",
        "error_class": error_class,
        "decide": None,
        "chat": None,
        "success_rate": None,
    }


class TestPersistenceAndReport:
    def test_append_rows_creates_and_appends_jsonl(self, tmp_path) -> None:
        path = tmp_path / "run" / "benchmarks" / "decide-2026-10-20.jsonl"
        append_rows(path, [ok_row("heavengraph"), unreachable_row("local-rocm")])
        append_rows(path, [ok_row("heavengraph")])
        lines = path.read_text().splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0])["backend"] == "heavengraph"
        assert json.loads(lines[2])["status"] == "ok"
        assert [row["backend"] for row in read_rows(path)] == [
            "heavengraph",
            "local-rocm",
            "heavengraph",
        ]

    def test_benchmark_path_uses_decide_date_filename(self, tmp_path) -> None:
        assert benchmark_path(tmp_path, "2026-10-20") == tmp_path / "decide-2026-10-20.jsonl"

    def test_latest_rows_keeps_last_row_per_backend_in_order(self) -> None:
        rows = [
            ok_row("heavengraph"),
            unreachable_row("local-rocm"),
            ok_row("heavengraph", success_rate=0.99),
            ok_row("chat-qwen3-4b", kind="chat", decide=None),
        ]
        latest = latest_rows(rows)
        assert [row["backend"] for row in latest] == [
            "heavengraph",
            "local-rocm",
            "chat-qwen3-4b",
        ]
        assert latest[0]["success_rate"] == 0.99, "the newer heavengraph row wins"

    def test_render_report_markdown_table(self) -> None:
        qwen = ok_row(
            "chat-qwen3-4b",
            kind="chat",
            decide=None,
            chat={
                "n": 10,
                "success": 8,
                "failed": 2,
                "p50_s": 0.35,
                "p90_s": 0.52,
                "max_s": 0.9,
                "tokens_in": 48,
                "tokens_out": 22,
                "errors": {"timeout": 2},
            },
            success_rate=0.75,
        )
        rows = [ok_row("heavengraph"), unreachable_row("local-rocm"), qwen]
        report = render_report(rows)

        assert report.startswith("# Decision pipeline benchmark")
        assert "| backend | decide p50 | decide p90 | chat p50 | success |" in report
        assert "|---|---|---|---|---|" in report
        assert "| heavengraph | 0.90s | 1.30s | — | 100% |" in report
        assert "| local-rocm | unreachable (connection_error) | — | — | — |" in report
        assert "| chat-qwen3-4b | — | — | 0.35s | 75% |" in report
        assert report.endswith("\n")

    def test_run_benchmark_covers_every_configured_backend(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "down.test":
                msg = "refused"
                raise httpx.ConnectError(msg, request=request)
            return httpx.Response(200, json=decide_body())

        configs = [
            BackendConfig(name="up", base_url="http://up.test", kind="systemone"),
            BackendConfig(name="down", base_url="http://down.test", kind="systemone"),
        ]
        rows = run_benchmark(
            configs,
            decide_n=1,
            chat_n=0,
            client_factory=lambda: mock_client(handler),
            now=lambda: FAKE_NOW,
        )
        assert [row["backend"] for row in rows] == ["up", "down"]
        assert [row["status"] for row in rows] == ["ok", "unreachable"]
