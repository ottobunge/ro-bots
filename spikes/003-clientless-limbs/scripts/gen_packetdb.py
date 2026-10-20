#!/usr/bin/env python3
"""Retired historical generator; no alternate guard evaluator is supported."""

import sys


def main(argv=None):
    print("RETIRED: use packetdb.py's strict MAIN 20180704 offline derivation", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
