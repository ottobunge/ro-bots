#!/usr/bin/env python3
"""Benchmark Cloudflare Workers AI hosted Clef against the local CPU numbers.

Uses the same realistic RO decision request as bench.py. Reads the OAuth
token from wrangler's local config (~/.config/.wrangler/config/default.toml)
-- the token never leaves this machine. Models: @cf/cloudflare/clef-flash
(9B) and @cf/cloudflare/clef (27B).
"""

from __future__ import annotations

import json
import random
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ACCOUNT_ID = "da23eba55895f31702561b4d52e9cac5"
WRANGLER_CONFIG = Path.home() / ".config/.wrangler/config/default.toml"
MODELS = {
    "clef-flash": "@cf/cloudflare/clef-flash",
    "clef-27b": "@cf/cloudflare/clef",
}
PRICE_PER_MTOK = {"clef-flash": 0.09, "clef-27b": 0.24}  # USD per 1M input tokens

sys.path.insert(0, str(Path(__file__).parent))
from bench import make_bot  # noqa: E402  (same request generator as the local bench)


def load_token() -> str:
    """Read the OAuth token from wrangler's config (local keyring file)."""
    for line in WRANGLER_CONFIG.read_text().splitlines():
        if line.strip().startswith("oauth_token"):
            return line.split('"')[1]
    msg = f"no oauth_token in {WRANGLER_CONFIG}"
    raise RuntimeError(msg)


def call(model: str, request: dict, token: str) -> tuple[dict, float, int]:
    """POST one SystemOne request; return (answers, wall_seconds, input_tokens)."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{model}"
    body = json.dumps(request).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.load(resp)
    wall = time.perf_counter() - start
    if not payload.get("success"):
        raise RuntimeError(f"API error: {payload.get('errors')}")
    result = payload["result"]
    answers = result["answers"]
    input_tokens = result.get("usage", {}).get("input_tokens", 0)
    return answers, wall, input_tokens


def main() -> None:
    token = load_token()
    rng = random.Random(4242)
    request = make_bot(0, rng)
    request["model"] = "clef-flash"
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    for name, model_id in MODELS.items():
        request["model"] = "clef-flash" if "flash" in name else "clef"
        # cold call (route warmup)
        _, cold, input_tokens = call(model_id, request, token)
        walls = []
        answers = {}
        for _ in range(runs):
            answers, wall, _ = call(model_id, request, token)
            walls.append(wall)
        p50 = statistics.median(walls)
        p95 = sorted(walls)[int(len(walls) * 0.95)]
        choice = answers.get("next_action", {}).get("choice")
        conf = answers.get("next_action", {}).get("confidence")
        cost = PRICE_PER_MTOK[name] * input_tokens / 1_000_000
        print(
            f"{name:10s} cold={cold:6.2f}s  p50={p50:6.2f}s  p95={p95:6.2f}s  "
            f"in_tokens={input_tokens}  next_action={choice}({conf:.2f})  "
            f"cost/decision=${cost:.6f}"
        )
    print("\nCPU (spike 001) reference: p50=64.9s p95=77.1s | LCP-warm=0.94s")


if __name__ == "__main__":
    main()
