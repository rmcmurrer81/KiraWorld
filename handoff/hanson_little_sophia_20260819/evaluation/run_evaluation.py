#!/usr/bin/env python3
"""Entry point for the isolated matched behavioral evaluator."""

import sys

# The evaluator's containment rule forbids Python bytecode writes beside source.
sys.dont_write_bytecode = True

from isolated_eval.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
