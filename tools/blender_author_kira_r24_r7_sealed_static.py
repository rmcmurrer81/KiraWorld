from __future__ import annotations

"""Sealed R24 R7 author command target.

R7 is static-only.  This exact target validates the controller receipt fields
and then deliberately fails before importing ``bpy`` or authoring a Blend.  A
later, separately audited execution package must replace it append-only; the
R7 controller never accepts a caller-selected command.
"""

import argparse
import hashlib
from pathlib import Path
import re
import sys


EXECUTION_AUTHORITY = "NOT_GRANTED_STATIC_R7"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeError(f"{name} is not a canonical SHA-256 digest")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--controller-nonce", required=True)
    parser.add_argument("--job-nonce", required=True)
    parser.add_argument("--source-snapshot-sha256", required=True)
    parser.add_argument("--execute-authoring", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    _require_sha256("controller nonce", args.controller_nonce)
    _require_sha256("job nonce", args.job_nonce)
    _require_sha256("source snapshot digest", args.source_snapshot_sha256)
    source = Path(args.source).resolve()
    if not source.is_file() or _sha256_file(source) != args.source_snapshot_sha256:
        raise RuntimeError("sealed author source snapshot identity changed")
    # Deliberately do not inspect, create, or mutate the requested output.  The
    # parsed fields bind the proposed command receipt, but cannot grant the
    # execution authority that this static package explicitly lacks.
    raise RuntimeError(
        "R24 R7 is a static gate; sealed author execution authority is not granted"
    )


if __name__ == "__main__":
    raise SystemExit(main())
