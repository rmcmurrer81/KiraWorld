from __future__ import annotations

"""Exact fresh-process evaluator entry for the append-only R24 R6 gate."""

import argparse
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
while str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r6 as r6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", args.candidate_sha256):
        raise RuntimeError("candidate digest is malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", args.nonce):
        raise RuntimeError("controller nonce is malformed")
    output = Path(args.output).resolve()
    if output.exists():
        raise RuntimeError("fresh evaluator output already exists")
    result = r6.artifact_evaluation_only(
        Path(args.candidate), args.candidate_sha256, Path(args.blender)
    )
    envelope = {
        "schema": "kira.avatar.r24.r6.fresh_evaluator_envelope.v1",
        "nonce": args.nonce,
        "candidate_sha256": args.candidate_sha256,
        "artifact_result": result,
    }
    encoded = r6.canonical_json(envelope)
    descriptor = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
