#!/usr/bin/env python3
"""Spike 005-gpu-clef: LCP-warm repeated-prefix measurement.

Fires the SAME request twice back-to-back N times; reports first-call (cold-ish)
and second-call (prefix-cache hit) latency. Usage: lcp_warm.py --url URL [--reps 10]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request

sys.path.insert(0, "/home/otto/dev/ro-bots/spikes/001-clef-local")
from bench import make_bot, post  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8091")
    ap.add_argument("--reps", type=int, default=10)
    args = ap.parse_args()
    url = args.url.rstrip("/") + "/v1/systemone"
    rng = __import__("random").Random(777)
    req = make_bot(999, rng)

    first, second = [], []
    for i in range(args.reps):
        _, d1 = post(url, req)
        _, d2 = post(url, req)
        first.append(d1 * 1000)
        second.append(d2 * 1000)
        print(f"rep {i}: first {d1*1000:.0f} ms, second {d2*1000:.0f} ms")
    print(f"\nfirst-call  p50 {statistics.median(first):.0f} ms")
    print(
        f"second-call p50 {statistics.median(second):.0f} ms  "
        f"(LCP/prefix-cache warm), min {min(second):.0f}"
    )


if __name__ == "__main__":
    main()
