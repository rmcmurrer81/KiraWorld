from __future__ import annotations

"""Sealed R24 R6 author command target.

R6 is static-only, so this exact command target deliberately fails before
opening a Blend. A later separately audited execution package must replace it
append-only; the R6 controller never accepts a caller-selected command.
"""

import argparse
import sys


EXECUTION_AUTHORITY = "NOT_GRANTED_STATIC_R6"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--controller-nonce", required=True)
    parser.add_argument("--execute-authoring", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    parse_args()
    raise RuntimeError(
        "R24 R6 is a static gate; sealed author execution authority is not granted"
    )


if __name__ == "__main__":
    raise SystemExit(main())

