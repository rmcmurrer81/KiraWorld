"""Static-only hostile fixture: put the protocol worker one generation too deep."""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args()
    command = [
        sys.executable,
        "-u",
        "-m",
        "Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8.worker_entry",
        "--static-fixture",
        "--nonce",
        args.nonce,
    ]
    process = subprocess.Popen(command, shell=False)
    return int(process.wait())


if __name__ == "__main__":
    raise SystemExit(main())
