"""Offline pending-walk attribution over population traces; never opens a world."""

import argparse
import json
from pathlib import Path

from robots.app.pendingwalk_attribution import load_traces, summarize_pendingwalk


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--start", help="Inclusive ISO timestamp with UTC offset")
    parser.add_argument("--end", help="Exclusive ISO timestamp with UTC offset")
    parser.add_argument(
        "--bucket-origin",
        help="Wall clock of receipt-sample second zero (the runner launch); " "defaults to --start",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    samples = json.loads(args.receipt.read_text())["samples"]
    traces = load_traces(args.traces, start=args.start, end=args.end)
    result = summarize_pendingwalk(
        traces,
        samples=samples,
        start=args.start,
        end=args.end,
        bucket_origin=args.bucket_origin,
    )
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
