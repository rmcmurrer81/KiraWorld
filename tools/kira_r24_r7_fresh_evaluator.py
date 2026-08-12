from __future__ import annotations

"""Exact R24 R7 evaluator; its sole result channel is stdout's anonymous pipe."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
while str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7 as r7


SCHEMA = "kira.avatar.r24.r7.fresh_evaluator_envelope.v2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(name: str, value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeError(f"{name} is not a canonical SHA-256 digest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--controller-nonce", required=True)
    parser.add_argument("--author-job-nonce", required=True)
    parser.add_argument("--author-command-sha256", required=True)
    parser.add_argument("--author-pid", required=True)
    parser.add_argument("--author-job-quiescent", required=True, choices=("true",))
    parser.add_argument("--immutable-source-snapshot-sha256", required=True)
    parser.add_argument("--dependency-bundle-sha256", required=True)
    parser.add_argument("--expected-evaluator-path", required=True)
    parser.add_argument("--expected-evaluator-bytes", required=True, type=int)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for name, value in (
        ("candidate digest", args.candidate_sha256),
        ("controller nonce", args.controller_nonce),
        ("author job nonce", args.author_job_nonce),
        ("author command digest", args.author_command_sha256),
        ("immutable source snapshot digest", args.immutable_source_snapshot_sha256),
        ("dependency bundle digest", args.dependency_bundle_sha256),
        ("expected evaluator digest", args.expected_evaluator_sha256),
    ):
        require_sha256(name, value)
    if not re.fullmatch(r"[1-9][0-9]*", args.author_pid):
        raise RuntimeError("author PID is not a canonical positive integer")

    evaluator = Path(__file__).resolve()
    expected_evaluator = Path(args.expected_evaluator_path).resolve()
    evaluator_bytes = int(evaluator.stat().st_size)
    evaluator_sha256 = sha256_file(evaluator)
    if (
        expected_evaluator != evaluator
        or args.expected_evaluator_bytes != evaluator_bytes
        or args.expected_evaluator_sha256 != evaluator_sha256
    ):
        raise RuntimeError("fresh evaluator identity differs from the sealed identity")

    candidate = Path(args.candidate).resolve()
    if not candidate.is_file() or sha256_file(candidate) != args.candidate_sha256:
        raise RuntimeError("candidate identity changed before fresh evaluation")
    candidate_record = {
        "path": str(candidate),
        "bytes": int(candidate.stat().st_size),
        "sha256": args.candidate_sha256,
    }
    result = r7.artifact_evaluation_only(
        candidate, args.candidate_sha256, Path(args.blender)
    )
    failures = r7.validate_artifact_evaluation_result(result)
    if failures:
        raise RuntimeError("fresh artifact result schema failed: " + ",".join(sorted(failures)))
    envelope = {
        "schema": SCHEMA,
        "controller_nonce": args.controller_nonce,
        "author_job_nonce": args.author_job_nonce,
        "candidate": candidate_record,
        "immutable_source_snapshot_sha256": args.immutable_source_snapshot_sha256,
        "author": {
            "command_sha256": args.author_command_sha256,
            "pid": int(args.author_pid),
            "job_quiescent": True,
        },
        "evaluator": {
            "pid": os.getpid(),
            "path": str(evaluator),
            "bytes": evaluator_bytes,
            "sha256": evaluator_sha256,
        },
        "dependency_bundle_sha256": args.dependency_bundle_sha256,
        "artifact_result": result,
        "truth": {
            "fresh_process": True,
            "stdout_anonymous_pipe_only": True,
            "writable_result_path_used": False,
        },
    }
    sys.stdout.buffer.write(r7.canonical_json(envelope) + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
