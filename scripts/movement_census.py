"""Offline movement census over population traces; never opens a live world."""

import argparse
import json
from pathlib import Path

from robots.app.movement_census import summarize_movement_traces


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--start", help="Inclusive ISO timestamp with UTC offset")
    parser.add_argument("--end", help="Exclusive ISO timestamp with UTC offset")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize_movement_traces(args.traces, start=args.start, end=args.end)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
