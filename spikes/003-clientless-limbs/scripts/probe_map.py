#!/usr/bin/env python3
"""Retired unsafe historical probe; importing this file has no side effects."""

import sys


def main(argv=None):
    print("RETIRED: use test_limbs.py with an explicit private isolated fixture", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
