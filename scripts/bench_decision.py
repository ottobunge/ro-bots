#!/usr/bin/env python3
"""Decision-pipeline benchmark CLI: ``task bench`` and ``task bench-report``.

run:    probe every configured backend (real-shape decide + chat requests),
        append one row per backend to run/benchmarks/decide-<date>.jsonl and
        print the comparison table. Unreachable backends get an honest
        'unreachable' row — never fabricated.
report: render the latest row per backend as run/benchmarks/latest.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from robots.bench import (
    append_rows,
    benchmark_path,
    load_backends,
    latest_rows,
    read_rows,
    render_report,
    run_benchmark,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).resolve().parent / "bench_backends.json"
DEFAULT_OUT_DIR = REPO_ROOT / "run" / "benchmarks"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="benchmark every configured backend and append rows")
    run.add_argument("--config", default=str(DEFAULT_CONFIG))
    run.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    run.add_argument("--decide-n", type=int, default=30)
    run.add_argument("--chat-n", type=int, default=10)
    run.add_argument("--timeout", type=float, default=120.0)
    run.add_argument("--backends", default=None, help="comma-separated subset of backend names")

    report = sub.add_parser("report", help="render the latest rows as a markdown table")
    report.add_argument("--benchmarks-dir", default=str(DEFAULT_OUT_DIR))
    report.add_argument("--out", default=None, help="default <benchmarks-dir>/latest.md")
    return parser


def _select(configs: list[Any], names: str | None) -> list[Any]:
    if not names:
        return configs
    wanted = {name.strip() for name in names.split(",") if name.strip()}
    unknown = wanted - {config.name for config in configs}
    if unknown:
        print(f"unknown backends: {', '.join(sorted(unknown))}", file=sys.stderr)
        raise SystemExit(2)
    return [config for config in configs if config.name in wanted]


def _run(args: argparse.Namespace) -> int:
    configs = _select(load_backends(args.config), args.backends)
    rows = run_benchmark(configs, decide_n=args.decide_n, chat_n=args.chat_n, timeout=args.timeout)
    path = benchmark_path(args.out_dir)
    append_rows(path, rows)
    print(f"appended {len(rows)} rows -> {path}")
    print(render_report(latest_rows(rows)), end="")
    return 0


def _report(args: argparse.Namespace) -> int:
    bench_dir = Path(args.benchmarks_dir)
    files = sorted(bench_dir.glob("decide-*.jsonl"))
    if not files:
        print(f"no decide-*.jsonl rows under {bench_dir}", file=sys.stderr)
        return 1
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(read_rows(path))
    report = render_report(latest_rows(rows))
    out = Path(args.out) if args.out else bench_dir / "latest.md"
    out.write_text(report)
    print(f"wrote {out}")
    print(report, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return _run(args)
    return _report(args)


if __name__ == "__main__":
    raise SystemExit(main())
