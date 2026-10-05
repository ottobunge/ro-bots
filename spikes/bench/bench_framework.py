#!/usr/bin/env python3
"""Decision backend benchmark framework (ADR-012).

Runs the canonical workload (bench.make_bot: realistic RO state + 18 mixed
questions, 2390 tokens) against one or more backends and emits a comparison
row per backend: single cold/p50/p95, batch-8 wall time, warm-prefix latency,
cost per 1k decisions.

Usage:
    python3 bench_framework.py --backends cloudflare-flash,cpu --runs 10

Backends:
    cpu               local llama.cpp /v1/systemone (spike 001 build, port 8091)
    cloudflare-flash  Workers AI @cf/cloudflare/clef-flash
    cloudflare-27b    Workers AI @cf/cloudflare/clef
    heavengraph-*     GPU llama.cpp (requires HEAVENGRAPH_CLEF_URL, spike 005)

Auth: hosted backends read CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN from
~/.hermes/.env, falling back to wrangler's local OAuth config. MAX_BENCH_CALLS
(default 50) caps hosted spend per invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "001-clef-local"))
from bench import make_bot  # noqa: E402

ACCOUNT_ID = "da23eba55895f31702561b4d52e9cac5"
HERMES_ENV = Path.home() / ".hermes/.env"
WRANGLER_CONFIG = Path.home() / ".config/.wrangler/config/default.toml"
PRICE_PER_MTOK = {"cloudflare-flash": 0.09, "cloudflare-27b": 0.24}
DEFAULT_MAX_CALLS = 50


def load_cf_token() -> str:
    """Prefer ~/.hermes/.env vars; fall back to wrangler's local OAuth token."""
    if HERMES_ENV.exists():
        env: dict[str, str] = {}
        for line in HERMES_ENV.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
        if env.get("CLOUDFLARE_API_TOKEN"):
            os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", env.get("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID))
            return env["CLOUDFLARE_API_TOKEN"]
    for line in WRANGLER_CONFIG.read_text().splitlines():
        if line.strip().startswith("oauth_token"):
            return line.split('"')[1]
    msg = "no Cloudflare token found (checked ~/.hermes/.env and wrangler config)"
    raise RuntimeError(msg)


def http_post(url: str, request: dict, token: str | None = None) -> tuple[dict, float]:
    """POST one request; returns (parsed_json, wall_seconds)."""
    body = json.dumps(request).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.load(resp)
    return payload, time.perf_counter() - start


class Backend:
    def __init__(self, name: str, url: str, token: str | None = None, model: str | None = None) -> None:
        self.name = name
        self.url = url
        self.token = token
        self.model = model
        self.calls = 0

    def call(self, request: dict) -> tuple[dict, float]:
        if self.calls >= DEFAULT_MAX_CALLS:
            raise RuntimeError(f"{self.name}: MAX_BENCH_CALLS={DEFAULT_MAX_CALLS} reached")
        self.calls += 1
        payload, wall = http_post(self.url, request, self.token)
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(f"{self.name}: API error {payload.get('errors')}")
        return payload, wall


def cpu_backend() -> Backend:
    return Backend("cpu", "http://127.0.0.1:8091/v1/systemone")


def cloudflare(model_key: str, model_id: str) -> Backend:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model_id}"
    # The request body's `model` field must literally be "clef" or "clef-flash".
    body_model = "clef-flash" if "flash" in model_key else "clef"
    return Backend(model_key, url, token=load_cf_token(), model=body_model)


def heavengraph(model_key: str) -> Backend:
    base = os.environ.get("HEAVENGRAPH_CLEF_URL")
    if not base:
        msg = "HEAVENGRAPH_CLEF_URL not set (spike 005 pending)"
        raise RuntimeError(msg)
    return Backend(model_key, base.rstrip("/") + "/v1/systemone")


def run_single(backend: Backend, requests: list[dict], runs: int) -> dict:
    request = dict(requests[0])
    if backend.model:
        request["model"] = backend.model
    _, cold = backend.call(request)
    walls = []
    answers: dict = {}
    last_payload: dict = {}
    for _ in range(runs):
        payload, wall = backend.call(request)
        walls.append(wall)
        last_payload = payload
        result = payload.get("result", payload)
        answers = result.get("answers", {})
    p50 = statistics.median(walls)
    p95 = sorted(walls)[min(int(len(walls) * 0.95), len(walls) - 1)]
    usage = last_payload.get("result", last_payload).get("usage", {})
    input_tokens = usage.get("input_tokens") or 0
    return {"cold": cold, "p50": p50, "p95": p95, "answers": answers, "input_tokens": input_tokens}


def run_batch(backend: Backend, requests: list[dict]) -> float:
    """Wall time for 8 distinct bot decisions, sequential HTTP."""
    start = time.perf_counter()
    for i, base_request in enumerate(requests[:8]):
        request = dict(base_request)
        if backend.model:
            request["model"] = backend.model
        backend.call(request)
    return time.perf_counter() - start


def run_warm_prefix(backend: Backend, requests: list[dict]) -> float:
    """Second call of an identical request (captures KV/prefix reuse)."""
    request = dict(requests[0])
    if backend.model:
        request["model"] = backend.model
    backend.call(request)
    _, second = backend.call(request)
    return second


def bench(backend: Backend, requests: list[dict], runs: int) -> dict:
    single = run_single(backend, requests, runs)
    batch8 = run_batch(backend, requests)
    warm = run_warm_prefix(backend, requests)
    row: dict = {
        "backend": backend.name,
        "cold_s": round(single["cold"], 3),
        "p50_s": round(single["p50"], 3),
        "p95_s": round(single["p95"], 3),
        "batch8_s": round(batch8, 3),
        "warm_prefix_s": round(warm, 3),
        "input_tokens": single["input_tokens"],
    }
    if backend.name in PRICE_PER_MTOK:
        cost = PRICE_PER_MTOK[backend.name] * single["input_tokens"] / 1_000_000
        row["cost_per_1k_decisions"] = round(cost * 1000, 4)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", default="cpu")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rng = random.Random(4242)
    requests = [make_bot(i, random.Random(4242 + i)) for i in range(8)]

    factories: dict[str, Callable[[], Backend]] = {
        "cpu": cpu_backend,
        "cloudflare-flash": lambda: cloudflare("cloudflare-flash", "@cf/cloudflare/clef-flash"),
        "cloudflare-27b": lambda: cloudflare("cloudflare-27b", "@cf/cloudflare/clef"),
        "heavengraph-flash": lambda: heavengraph("heavengraph-flash"),
        "heavengraph-27b": lambda: heavengraph("heavengraph-27b"),
    }

    rows = []
    for name in args.backends.split(","):
        name = name.strip()
        if name not in factories:
            print(f"unknown backend: {name}", file=sys.stderr)
            continue
        try:
            rows.append(bench(factories[name](), requests, args.runs))
        except (RuntimeError, OSError, urllib.error.URLError) as exc:
            rows.append({"backend": name, "error": str(exc)[:200]})

    header = (
        f"{'backend':20s} {'cold':>8s} {'p50':>8s} {'p95':>8s} "
        f"{'batch8':>8s} {'warm':>8s} {'$/1k':>8s}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        if "error" in row:
            print(f"{row['backend']:20s} ERROR: {row['error']}")
            continue
        print(
            f"{row['backend']:20s} {row['cold_s']:7.2f}s {row['p50_s']:7.2f}s "
            f"{row['p95_s']:7.2f}s {row['batch8_s']:7.2f}s {row['warm_prefix_s']:7.2f}s "
            f"{row.get('cost_per_1k_decisions', '-')!s:>8}"
        )
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
